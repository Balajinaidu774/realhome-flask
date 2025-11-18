from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import os
from sqlalchemy import func
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
import hashlib
import datetime
import json
from utils.proof import compute_sha256, make_merkle_root, anchor_to_ledger
from utils.chatbot import get_chatbot_response

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

# Currency conversion (USD -> INR) and formatting
app.config['USD_TO_INR'] = float(os.environ.get('USD_TO_INR', '83'))  # default conversion rate


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
    provenance_score = db.Column(db.Float, nullable=True, default=0.0)
    provenance_summary = db.Column(db.Text, nullable=True)
    # -------------------------------------

    # Ownership fields
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_sold = db.Column(db.Boolean, default=False)
    bought_on = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"Property('{self.street_name}', Verified: {self.quality_verified})"


# --- Verification Model ---
class Verification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    contributor_name = db.Column(db.String(200), nullable=True)
    contributor_pubkey = db.Column(db.String(500), nullable=True)
    doc_url = db.Column(db.String(1000), nullable=True)
    doc_hash = db.Column(db.String(128), nullable=False)
    attestation_level = db.Column(db.String(50), nullable=False, default='self')
    verifier = db.Column(db.String(200), nullable=True)
    verification_tx = db.Column(db.String(500), nullable=True)
    score = db.Column(db.Float, nullable=True, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    property = db.relationship('Property', backref=db.backref('verifications', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'role': self.role,
            'contributor_name': self.contributor_name,
            'doc_url': self.doc_url,
            'doc_hash': self.doc_hash,
            'attestation_level': self.attestation_level,
            'verifier': self.verifier,
            'verification_tx': self.verification_tx,
            'score': self.score,
            'notes': self.notes,
            'created_on': self.created_on.isoformat()
        }


# --- Transaction model to track purchases and rentals ---
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'buy' or 'rent'
    created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    property = db.relationship('Property', backref=db.backref('transactions', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'property_id': self.property_id,
            'type': self.type,
            'created_on': self.created_on.isoformat()
        }


# --- Support Ticket Model ---
class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, closed
    created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_on = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = db.relationship('User', backref=db.backref('support_tickets', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subject': self.subject,
            'message': self.message,
            'status': self.status,
            'created_on': self.created_on.isoformat(),
            'updated_on': self.updated_on.isoformat()
        }


# --- Visitor tracking model ---
class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    visits = db.Column(db.Integer, default=1)
    first_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = db.relationship('User', backref=db.backref('visitors', lazy=True))

    def touch(self):
        self.visits = (self.visits or 0) + 1
        self.last_seen = datetime.datetime.utcnow()
        db.session.add(self)
        db.session.commit()


# --- Simple provenance scoring helpers ---
ATTESTATION_WEIGHT = {
    'self': 0.3,
    'third_party': 0.8,
    'on_chain': 1.0
}

def compute_doc_hash(value: str) -> str:
    # Compute SHA-256 of the provided value (doc_url or raw content)
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def recompute_provenance(property_obj):
    verifs = Verification.query.filter_by(property_id=property_obj.id).all()
    if not verifs:
        property_obj.provenance_score = 0.0
        property_obj.provenance_summary = None
        return
    total = 0.0
    details = []
    for v in verifs:
        w = ATTESTATION_WEIGHT.get(v.attestation_level, 0.3)
        s = (v.score if v.score is not None else 0.5) * w
        total += s
        details.append({'role': v.role, 'contributor': v.contributor_name, 'score': v.score, 'attestation': v.attestation_level})
    avg = total / len(verifs)
    # normalize to 0..1
    prop_score = max(0.0, min(1.0, avg))
    property_obj.provenance_score = prop_score
    property_obj.provenance_summary = json.dumps(details)
    db.session.add(property_obj)
    db.session.commit()


# --- Visitor tracking helper ---
def record_visit(req):
    try:
        ip = req.remote_addr or req.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    except Exception:
        ip = None
    ua = req.headers.get('User-Agent', '')[:480]
    visitor = None
    try:
        # Try to find by ip + user_agent
        if ip:
            visitor = Visitor.query.filter_by(ip=ip, user_agent=ua).first()
        if not visitor and current_user.is_authenticated:
            # try to find by user association
            visitor = Visitor.query.filter_by(user_id=current_user.id).first()
        if visitor:
            visitor.touch()
        else:
            new_v = Visitor(ip=ip, user_id=(current_user.id if current_user.is_authenticated else None), user_agent=ua, visits=1)
            db.session.add(new_v)
            db.session.commit()
    except Exception:
        db.session.rollback()
        return


# --- Ensure DB has provenance columns (simple runtime migration for SQLite) ---
def ensure_provenance_columns():
    try:
        with app.app_context():
            # Try to add columns if they don't exist (SQLite supports ADD COLUMN)
            from sqlalchemy import text
            conn = db.engine.connect()
            try:
                conn.execute(text('ALTER TABLE property ADD COLUMN provenance_score REAL DEFAULT 0.0'))
            except Exception:
                pass
            try:
                conn.execute(text('ALTER TABLE property ADD COLUMN provenance_summary TEXT'))
            except Exception:
                pass
            # add ownership columns if missing
            try:
                conn.execute(text('ALTER TABLE property ADD COLUMN owner_id INTEGER'))
            except Exception:
                pass
            try:
                conn.execute(text('ALTER TABLE property ADD COLUMN is_sold BOOLEAN DEFAULT 0'))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE property ADD COLUMN bought_on TEXT"))
            except Exception:
                pass
            conn.close()
    except Exception:
        # If this fails, ignore; app will still run but new columns won't be present until migrated
        pass

# Run quick runtime migration
ensure_provenance_columns()

# Ensure all tables exist (safe for development)
with app.app_context():
    try:
        db.create_all()
    except Exception:
        pass

# --- Template filters / helpers for currency formatting ---
def _format_indian_number(amount: int) -> str:
    """Format integer amount using Indian grouping: 12,34,567"""
    s = str(int(round(amount)))
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ','.join(parts) + ',' + last3

def format_inr(amount, per_month=False):
    """Return a formatted string with the rupee symbol and Indian grouping.
    `amount` is expected in INR (numeric).
    """
    try:
        amt = float(amount)
    except Exception:
        return amount
    formatted = _format_indian_number(amt)
    if per_month:
        return f"₹{formatted} / month"
    return f"₹{formatted}"

# Register filter and make rate available in templates
app.jinja_env.filters['inr'] = format_inr
app.jinja_env.globals['USD_TO_INR'] = app.config['USD_TO_INR']

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
    # record the visit
    try:
        record_visit(request)
    except Exception:
        pass

    properties = Property.query.order_by(db.func.random()).limit(3).all()
    # compute unique buyers and unique renters
    try:
        unique_buyers = db.session.query(func.count(func.distinct(Transaction.user_id))).filter(Transaction.type == 'buy').scalar() or 0
        unique_renters = db.session.query(func.count(func.distinct(Transaction.user_id))).filter(Transaction.type == 'rent').scalar() or 0
        # visitor stats
        unique_visitors = Visitor.query.count()
        total_visits = db.session.query(func.sum(Visitor.visits)).scalar() or 0
        # properties sold and rented
        properties_sold = Property.query.filter_by(is_sold=True).count()
        properties_rented = db.session.query(func.count(func.distinct(Transaction.property_id))).filter(Transaction.type == 'rent').scalar() or 0
    except Exception:
        unique_buyers = unique_renters = unique_visitors = total_visits = properties_sold = properties_rented = 0
    return render_template('index.html', properties=properties, unique_buyers=unique_buyers, unique_renters=unique_renters, unique_visitors=unique_visitors, total_visits=total_visits, properties_sold=properties_sold, properties_rented=properties_rented)

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
            query = query.filter(Property.medv < 17)
        elif search_price_sale == '2':
            query = query.filter(Property.medv.between(17, 22))
        elif search_price_sale == '3':
            query = query.filter(Property.medv.between(22, 26))
        elif search_price_sale == '4':
            query = query.filter(Property.medv > 26)
    # record visit and compute stats
    try:
        record_visit(request)
    except Exception:
        pass
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
            query = query.filter(Property.medv < 1.5)
        elif search_price_rent == '2':
            query = query.filter(Property.medv.between(1.5, 2.2))
        elif search_price_rent == '3':
            query = query.filter(Property.medv.between(2.2, 2.6))
        elif search_price_rent == '4':
            query = query.filter(Property.medv > 2.6)
    try:
        record_visit(request)
    except Exception:
        pass
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

@app.route('/support', methods=['GET', 'POST'])
@login_required
def support():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        if not subject or not message:
            flash('Subject and message are required.', 'danger')
            return render_template('support.html')
        
        # Create new support ticket
        ticket = SupportTicket(user_id=current_user.id, subject=subject, message=message)
        db.session.add(ticket)
        db.session.commit()
        
        flash('Your support ticket has been submitted successfully. We will review it shortly.', 'success')
        return render_template('support.html')
    
    return render_template('support.html')

@app.route('/profile')
@login_required
def profile():
    # Count number of properties the current user has purchased and list them
    try:
        purchased_count = Transaction.query.filter_by(user_id=current_user.id, type='buy').count()
        rented_count = Transaction.query.filter_by(user_id=current_user.id, type='rent').count()
        purchased_tx = Transaction.query.filter_by(user_id=current_user.id, type='buy').order_by(Transaction.created_on.desc()).all()
        purchased_props = [Property.query.get(tx.property_id) for tx in purchased_tx]
        # Get user's support tickets
        support_tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_on.desc()).all()
    except Exception:
        purchased_count = 0
        rented_count = 0
        purchased_props = []
        support_tickets = []
    return render_template('profile.html', purchased_count=purchased_count, rented_count=rented_count, purchased_props=purchased_props, support_tickets=support_tickets)

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
        # convert USD -> INR for display
        predicted_inr = predicted_price * app.config['USD_TO_INR']
        return render_template('value.html', 
                       averages=data_averages, 
                       prediction=format_inr(predicted_inr),
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
        # Provide prices converted to INR
        "price_sale": format_inr((prop.medv or 0) * 1000 * app.config['USD_TO_INR']),
        "price_rent": format_inr((prop.medv or 0) * 10 * app.config['USD_TO_INR'], per_month=True),
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


# --- Verification endpoints ---
@app.route('/api/property/<int:property_id>/verifications', methods=['GET'])
def list_verifications(property_id):
    prop = Property.query.get_or_404(property_id)
    verifs = [v.to_dict() for v in prop.verifications]
    return jsonify({'property_id': property_id, 'verifications': verifs, 'provenance_score': prop.provenance_score})


@app.route('/transaction/create', methods=['POST'])
@login_required
def create_transaction():
    data = request.get_json() or {}
    prop_id = data.get('property_id')
    tx_type = data.get('type')
    if not prop_id or tx_type not in ('buy', 'rent'):
        return jsonify({'status': 'error', 'message': 'property_id and valid type (buy|rent) required'}), 400
    prop = Property.query.get(prop_id)
    if not prop:
        return jsonify({'status': 'error', 'message': 'property not found'}), 404
    # create transaction
    tx = Transaction(user_id=current_user.id, property_id=prop.id, type=tx_type)
    db.session.add(tx)

    # If this is a purchase, mark property as sold and set owner
    if tx_type == 'buy':
        try:
            prop.owner_id = current_user.id
            prop.is_sold = True
            prop.bought_on = datetime.datetime.utcnow().isoformat()
            db.session.add(prop)
        except Exception:
            # ignore property update errors but keep transaction
            pass

    db.session.commit()
    return jsonify({'status': 'ok', 'transaction': tx.to_dict(), 'property': {'id': prop.id, 'is_sold': bool(prop.is_sold), 'owner_id': prop.owner_id}})


@app.route('/api/property/<int:property_id>/verify', methods=['POST'])
def create_verification(property_id):
    prop = Property.query.get_or_404(property_id)
    data = request.get_json() or {}
    role = data.get('role') or data.get('role', 'artisan')
    contributor = data.get('contributor_name')
    doc_url = data.get('doc_url')
    doc_hash = data.get('doc_hash') or (compute_sha256(doc_url) if doc_url else compute_sha256(str(datetime.datetime.utcnow())))
    attestation = data.get('attestation_level', 'self')
    score = float(data.get('score', 0.5))

    v = Verification(
        property_id=prop.id,
        role=role,
        contributor_name=contributor,
        doc_url=doc_url,
        doc_hash=doc_hash,
        attestation_level=attestation,
        score=score,
        verifier=data.get('verifier'),
        verification_tx=data.get('verification_tx'),
        notes=data.get('notes')
    )
    db.session.add(v)
    db.session.commit()

    # recompute property provenance
    recompute_provenance(prop)

    return jsonify({'status': 'ok', 'verification': v.to_dict(), 'provenance_score': prop.provenance_score})


@app.route('/api/anchor', methods=['POST'])
def anchor_verifications():
    # Anchor all verification doc_hashes into a simple ledger (Merkle root)
    all_hashes = [v.doc_hash for v in Verification.query.all()]
    root = make_merkle_root(all_hashes)
    anchor = anchor_to_ledger(root)
    return jsonify({'status': 'anchored', 'anchor': anchor})


# --- Chatbot endpoint ---
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    response = get_chatbot_response(user_message)
    return jsonify(response)

# --- Run the Application ---
if __name__ == '__main__':
    app.run(debug=True)