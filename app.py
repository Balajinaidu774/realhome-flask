from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import os
from sqlalchemy import func
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np

# --- Model Training ---
model = LinearRegression()
# Use lowercase column names to match the normalized CSV headers below
feature_cols = ['rm', 'lstat', 'ptratio', 'crim']
target_col = 'medv'
data_averages = {}
try:
    df = pd.read_csv('real_estate.csv')
    df.columns = [col.lower().strip() for col in df.columns]
    df = df[feature_cols + [target_col]].dropna()
    X = df[feature_cols]
    y = df[target_col]
    model.fit(X, y)
    data_averages = {
        'rm': round(df['rm'].mean(), 1),
        'lstat': round(df['lstat'].mean(), 1),
        'ptratio': round(df['ptratio'].mean(), 1),
        'crim': round(df['crim'].mean(), 2)
    }
    print("Machine learning model trained successfully.")
except FileNotFoundError:
    print("ERROR: 'real_estate.csv' not found. The value estimator will not work.")
except Exception as e:
    print(f"Error training model: {e}")
# --- End Model Training ---

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
    property_type = db.Column(db.String(100), nullable=True)
    street_name = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # --- NEW: VERIFIABLE QUALITY COLUMNS ---
    architect = db.Column(db.String(100), nullable=True)
    builder = db.Column(db.String(100), nullable=True)
    quality_verified = db.Column(db.Boolean, default=False)
    last_verified_on = db.Column(db.String(50), nullable=True)
    # -------------------------------------
    
    def __repr__(self):
        return f"Property('{self.street_name}', Verified: {self.quality_verified})"

# --- User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Authentication Routes ---
# ... (signup, login, logout routes remain unchanged) ...
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
    query = Property.query
    search_location = request.args.get('search_location')
    search_type = request.args.get('search_type')
    search_price_sale = request.args.get('search_price_sale')
    if search_location:
        query = query.filter(Property.street_name.ilike(f'%{search_location}%'))
    if search_type:
        query = query.filter(Property.property_type == search_type)
    if search_price_sale:
        if search_price_sale == '1':
            query = query.filter(Property.medv < 500)
        elif search_price_sale == '2':
            query = query.filter(Property.medv.between(500, 1000))
        elif search_price_sale == '3':
            query = query.filter(Property.medv > 1000)
    properties = query.all()
    types_result = db.session.query(Property.property_type).distinct().all()
    property_types = [t[0] for t in types_result if t[0]]
    return render_template('buy.html', 
                           properties=properties, 
                           property_types=property_types,
                           search_params=request.args)

@app.route('/rent')
def rent():
    query = Property.query
    search_location = request.args.get('search_location')
    search_type = request.args.get('search_type')
    search_price_rent = request.args.get('search_price_rent')
    if search_location:
        query = query.filter(Property.street_name.ilike(f'%{search_location}%'))
    if search_type:
        query = query.filter(Property.property_type == search_type)
    if search_price_rent:
        if search_price_rent == '1':
            query = query.filter(Property.medv < 300)
        elif search_price_rent == '2':
            query = query.filter(Property.medv.between(300, 600))
        elif search_price_rent == '3':
            query = query.filter(Property.medv > 600)
    properties = query.all()
    types_result = db.session.query(Property.property_type).distinct().all()
    property_types = [t[0] for t in types_result if t[0]]
    return render_template('rent.html', 
                           properties=properties, 
                           property_types=property_types,
                           search_params=request.args)

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
        print(f"Inquiry from {current_user.email} about {prop.street_name}: {message}")
        flash('Your message has been sent!', 'success')
        return redirect(url_for('contact', property_id=prop.id))
    return render_template('contact.html', prop=prop)

@app.route('/value')
def value():
    return render_template('value.html', averages=data_averages, prediction=None)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        form_data = request.form
        rm = float(form_data.get('rm'))
        lstat = float(form_data.get('lstat'))
        ptratio = float(form_data.get('ptratio'))
        crim = float(form_data.get('crim'))
        input_data = pd.DataFrame([[rm, lstat, ptratio, crim]], columns=feature_cols)
        prediction_raw = model.predict(input_data)
        predicted_price = prediction_raw[0] * 1000
        return render_template('value.html', 
                               averages=data_averages, 
                               prediction=f"${predicted_price:,.0f}",
                               form_values=form_data)
    except Exception as e:
        print(f"Prediction Error: {e}")
        flash('There was an error making a prediction. Please check your inputs.', 'danger')
        return render_template('value.html', averages=data_averages, prediction=None)

# --- NEW: API ROUTE FOR PROPERTY DETAILS ---
@app.route('/api/property/<int:property_id>')
def get_property_details(property_id):
    prop = Property.query.get_or_404(property_id)
    
    # Convert model to dictionary
    prop_data = {
        "id": prop.id,
        "property_type": prop.property_type,
        "price_sale": f"${(prop.medv or 0) * 1000:,.0f}",
        "price_rent": f"${(prop.medv or 0) * 10:,.0f} / month",
        "details_line": f"{prop.rm:.1f} Rooms | {prop.ptratio:.1f} P/T Ratio | {prop.crim:.2f} Crime Rate",
        "address": f"{prop.street_name}, Boston, MA",
        "image_url": prop.image_url,
        "lat": prop.lat,
        "lon": prop.lon,
        "description": prop.description,
        
        # --- Add new verifiable data ---
        "architect": prop.architect,
        "builder": prop.builder,
        "quality_verified": prop.quality_verified,
        "last_verified_on": prop.last_verified_on
    }
    return jsonify(prop_data)
# -------------------------------------------

# --- Run the Application ---
if __name__ == '__main__':
    app.run(debug=True)