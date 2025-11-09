from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import os

# Initialize the Flask application
app = Flask(__name__)

# --- Configurations ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_that_you_should_change') 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Initialize Extensions ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- Database Models ---

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False) 
    
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    zipcode = db.Column(db.String(20), nullable=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    bathrooms = db.Column(db.Integer, nullable=True)
    square_feet = db.Column(db.Integer, nullable=True)
    property_type = db.Column(db.String(50), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    
    def __repr__(self):
        return f"Property('{self.address}', '{self.price}')"

# --- User Loader ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Authentication Routes ---

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Username already exists.', 'danger')
        elif existing_email:
            flash('Email already registered.', 'danger')
        elif not (username and email and password):
             flash('Please fill out all fields.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, email=email, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- Main Page Routes ---

@app.route('/')
def index():
    properties = Property.query.limit(3).all()
    return render_template('index.html', properties=properties)

@app.route('/buy')
def buy():
    properties = Property.query.all()
    return render_template('buy.html', properties=properties)

@app.route('/rent')
def rent():
    properties = Property.query.all()
    return render_template('rent.html', properties=properties)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/support')
@login_required
def support():
    return render_template('support.html')

@app.route('/profile')
@login_required  # Ensures only logged-in users can see this
def profile():
    return render_template('profile.html')

# --- NEW ROUTE FOR CONTACT PAGE ---
@app.route('/contact/<int:property_id>', methods=['GET', 'POST'])
@login_required
def contact(property_id):
    # Find the specific property by its ID, or show a 404 error if not found
    prop = Property.query.get_or_404(property_id)
    
    if request.method == 'POST':
        # Get the message from the form
        message = request.form.get('message')
        
        # Here you would normally email the agent or save the inquiry.
        # For this example, we'll just flash a success message.
        print(f"Inquiry from {current_user.email} about {prop.address}: {message}")
        
        flash('Your message has been sent to the agent!', 'success')
        return redirect(url_for('contact', property_id=prop.id))

    # For a GET request, just show the page with the property info
    return render_template('contact.html', prop=prop)
# ----------------------------------

# --- Run the Application ---

if __name__ == '__main__':
    app.run(debug=True)