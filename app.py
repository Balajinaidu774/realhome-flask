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
    crim = db.Column(db.Float, nullable=True)
    zn = db.Column(db.Float, nullable=True)
    indus = db.Column(db.Float, nullable=True)
    chas = db.Column(db.Integer, nullable=True)
    nox = db.Column(db.Float, nullable=True)
    rm = db.Column(db.Float, nullable=True)      # Avg. rooms (our "BHK")
    age = db.Column(db.Float, nullable=True)
    dis = db.Column(db.Float, nullable=True)
    rad = db.Column(db.Integer, nullable=True)
    tax = db.Column(db.Float, nullable=True)
    ptratio = db.Column(db.Float, nullable=True)
    b = db.Column(db.Float, nullable=True)
    lstat = db.Column(db.Float, nullable=True)
    medv = db.Column(db.Float, nullable=True)    # Price in $1000s (our "Price")
    image_url = db.Column(db.String(500), nullable=True) 
    lat = db.Column(db.Float, nullable=True)     # Latitude
    lon = db.Column(db.Float, nullable=True)     # Longitude
    
    # --- NEW REALISTIC COLUMNS ---
    property_type = db.Column(db.String(100), nullable=True)
    street_name = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    # -----------------------------
    
    def __repr__(self):
        return f"Property('{self.street_name}', 'Price (MEDV): {self.medv}')"

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
    properties = Property.query.order_by(db.func.random()).limit(3).all()
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
@login_required
def profile():
    return render_template('profile.html')

@app.route('/contact/<int:property_id>', methods=['GET', 'POST'])
@login_required
def contact(property_id):
    prop = Property.query.get_or_404(property_id)
    
    if request.method == 'POST':
        message = request.form.get('message')
        print(f"Inquiry from {current_user.email} about Property ID {prop.id}: {message}")
        flash('Your message has been sent!', 'success')
        return redirect(url_for('contact', property_id=prop.id))

    return render_template('contact.html', prop=prop)

# --- Run the Application ---

if __name__ == '__main__':
    app.run(debug=True)