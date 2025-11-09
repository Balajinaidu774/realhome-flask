from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from flask_bcrypt import Bcrypt

# --- APP INITIALIZATION ---
app = Flask(__name__)

# CONFIG: Secret key is required for sessions and flash messages
app.config['SECRET_KEY'] = 'your_super_secret_key_change_this'
# CONFIG: This is the path to our database file
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

# --- EXTENSIONS INITIALIZATION ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# CONFIG: Tell LoginManager where to redirect if user is not logged in
login_manager.login_view = 'login'
# CONFIG: Set the "category" for the "Please log in" message
login_manager.login_message_category = 'info'


# --- DATABASE MODELS ---

# This is our User model (a "table" in the database)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    # We use username for display, like "Welcome, Bhaskar"
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # 60 chars is the length of a bcrypt hash
    password_hash = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f'<User {self.email}>'

# This function is required by Flask-Login.
# It tells Flask-Login how to find a user given their ID.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- AUTHENTICATION ROUTES ---

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # If user is already logged in, send them to the homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
       
    if request.method == 'POST':
        # Get data from the HTML form
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user or email already exists
        existing_user_email = User.query.filter_by(email=email).first()
        existing_user_name = User.query.filter_by(username=username).first()

        if existing_user_email:
            flash('That email is already in use.', 'danger')
            return redirect(url_for('signup'))
        if existing_user_name:
            flash('That username is already taken.', 'danger')
            return redirect(url_for('signup'))

        # If all checks pass, hash the password and create the user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
       
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password
        )
       
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    # If it's a GET request, just show the signup page
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, send them to the homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Find the user by their email
        user = User.query.filter_by(email=email).first()

        # Check if user exists AND the password is correct
        if user and bcrypt.check_password_hash(user.password_hash, password):
            # If yes, log them in with Flask-Login
            login_user(user)
            # Send them to the homepage (or wherever they were trying to go)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            # If no, show an error
            flash('Login failed. Check your email and password.', 'danger')
            return redirect(url_for('login'))

    # If it's a GET request, just show the login page
    return render_template('login.html')


@app.route('/logout')
@login_required # Only logged-in users can log out
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# --- STANDARD PAGE ROUTES ---

@app.route('/')
def index():
    """Serves the main home page."""
    # current_user is available in all templates!
    return render_template('index.html')

@app.route('/buy')
def buy():
    """Serves the 'buy' properties page."""
    return render_template('buy.html')

@app.route('/rent')
def rent():
    """Serves the 'rent' properties page."""
    return render_template('rent.html')

@app.route('/about')
def about():
    """Serves the 'about us' page."""
    return render_template('about.html')

@app.route('/support')
@login_required # This decorator SECURES the page!
def support():
    """Serves the customer support page."""
    # No more JS needed to check for login!
    # If not logged in, Flask-Login will redirect them to the 'login' page.
    return render_template('support.html')


# --- RUN THE APP ---

if __name__ == '__main__':
    with app.app_context():
        # This will create the database file and tables
        # if they don't exist
        db.create_all()
    app.run(debug=True)
