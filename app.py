# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, url_for, flash, request, session, current_app, abort, send_file, make_response, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_migrate import Migrate
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
import secrets
import string
import random
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
import io
import csv

app = Flask(__name__)

# Configuration
# Secure password encoding
db_password = quote_plus(os.getenv('DB_PASSWORD', 'damascus_user1'))

# Flask app secret key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
app.config['SECURITY_PASSWORD_SALT'] = os.environ.get('SECURITY_PASSWORD_SALT') or 'my-salt-key'

# Generate verification token
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

#if os.getenv('FLASK_ENV') == 'production':
db_user = os.getenv('DB_USER', 'damascus_user1')
db_host = os.getenv('DB_HOST', '127.0.0.1')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'damascus_db')

#app.config['SQLALCHEMY_DATABASE_URI'] = (f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
#    )

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
#else:
#    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Centralized Upload Configuration
UPLOAD_CONFIG = {
    'visa': {
        'folder': 'uploads/visa_applications',
        'allowed_extensions': {'pdf', 'doc', 'docx'},
        'max_size': 10 * 1024 * 1024  # 10MB
    },
    'project_management': {
        'folder': 'uploads/project_management',
        'allowed_extensions': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'mp4', 'mov', 'avi'},
        'max_size': 500 * 1024 * 1024  # 500MB
    },
    'investor': {
        'folder': 'uploads/investor_applications',
        'allowed_extensions': {'pdf', 'jpg', 'jpeg', 'png'},
        'max_size': 20 * 1024 * 1024  # 20MB
    },
    'joint_venture': {
        'folder': 'uploads/joint_ventures',
        'allowed_extensions': {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'},
        'max_size': 200 * 1024 * 1024  # 200MB
    },
    'housing': {
        'folder': 'uploads/housing_applications',
        'allowed_extensions': {'pdf', 'jpg', 'jpeg', 'png'},
        'max_size': 50 * 1024 * 1024  # 50MB
    },
    'hire_seller': {
        'folder': 'uploads/hire_seller',
        'allowed_extensions': {'pdf', 'doc', 'jpg', 'jpeg', 'png'},
        'max_size': 100 * 1024 * 1024  # 100MB
    },
    'hire_buyer': {
        'folder': 'uploads/hire_buyer',
        'allowed_extensions': {'pdf', 'doc', 'jpg', 'jpeg', 'png'},
        'max_size': 50 * 1024 * 1024  # 50MB
    }
}

# Create upload folders if they don't exist
for config in UPLOAD_CONFIG.values():
    os.makedirs(config['folder'], exist_ok=True)

# Helper Functions
def allowed_file(filename, app_type):
    """Check if file extension is allowed"""
    config = UPLOAD_CONFIG.get(app_type)
    if not config:
        return False
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config['allowed_extensions']

def save_uploaded_file(file, app_type, application_id, field_name):
    """Save uploaded file with proper naming"""
    if not file or file.filename == '':
        return None
    
    config = UPLOAD_CONFIG.get(app_type)
    if not config:
        raise ValueError(f"Invalid application type: {app_type}")
    
    if not allowed_file(file.filename, app_type):
        raise ValueError("File type not allowed")
    
    # Secure the filename and create unique name
    ext = os.path.splitext(file.filename)[1]
    filename = f"{app_type}_{application_id}_{field_name}{ext}"
    filename = secure_filename(filename)
    
    # Save file
    upload_path = os.path.join(config['folder'], filename)
    file.save(upload_path)
    
    return filename
    
    
    
# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'mail.damascusprojects.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'admin@damascusprojects.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'KOo1pfobfZmjfuCi')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True  # Important for port 465
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'admin@damascusprojects.com')

mail = Mail(app)

# Ensure upload dir exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'




















# --------------------------------------------------
# MODELS
# --------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    user_code = db.Column(db.String(150), nullable=False)
    town = db.Column(db.String(150), nullable=True)
    country = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_picture = db.Column(db.String(200), nullable=True)
    verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    verification_code_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    # Relationships to all application types
    project_applications = db.relationship('ProjectApplication', back_populates='user', cascade='all, delete-orphan')
    investor_applications = db.relationship('InvestorApplication', back_populates='user', cascade='all, delete-orphan')
    visa_applications = db.relationship('VisaApplication', back_populates='user', cascade='all, delete-orphan')
    venture_applications = db.relationship('VentureApplication', back_populates='user', cascade='all, delete-orphan')
    housing_applications = db.relationship('HousingApplication', back_populates='user', cascade='all, delete-orphan')
    #hire_applications = db.relationship('HireApplication', back_populates='user', cascade='all, delete-orphan')
    hire_seller_applications = db.relationship('HireSellerApplication', back_populates='user', cascade='all, delete-orphan')
    hire_buyer_applications = db.relationship('HireBuyerApplication', back_populates='user', cascade='all, delete-orphan')

    
    def get_profile_picture_url(self):
        if self.profile_picture:
            return url_for('static', filename=f'uploads/{self.profile_picture}')
        return url_for('static', filename='images/profile.png')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='reset-password(damascus)')

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, salt='reset-password(damascus)', max_age=expires_sec)['user_id']
        except Exception:
            return None
        return User.query.get(user_id)

class Program(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    icon = db.Column(db.String(50))
    subscriptions = db.relationship('Subscription', backref='program', lazy=True)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('program.id'), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    payment_receipt = db.Column(db.String(200), nullable=True)  # uploaded filename
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(100), default='pending', nullable=False)
    order_number = db.Column(db.String(100), unique=True, nullable=True)

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    program_slug = db.Column(db.String(50), nullable=False)  # Which program this admin manages
    is_super_admin = db.Column(db.Boolean, default=False)  # For future super admin functionality

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))
    action = db.Column(db.String(255))
    record_type = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))



class DeletedAccounts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80))
    deletion_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reason = db.Column(db.Text)
      


class VisaApplication(db.Model):
    __tablename__ = 'visa_applications'
    
    user = db.relationship('User', back_populates='visa_applications')
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key Relationship to User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Step 1 - Personal Info
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    birth_month = db.Column(db.String(2), nullable=False)
    birth_day = db.Column(db.String(2), nullable=False)
    birth_year = db.Column(db.String(4), nullable=False)
    nationality = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    marital_status = db.Column(db.String(10), nullable=False)
    
    # Step 2 - Education & Travel
    education_level = db.Column(db.String(50), nullable=False)
    country_of_interest = db.Column(db.String(100), nullable=False)
    travel_purpose = db.Column(db.String(20), nullable=False)
    language_proficiency = db.Column(db.String(20), nullable=False)
    passport_number = db.Column(db.String(50), nullable=False, unique=True)
    
    # Step 3 - Documents & Contact
    resume_filename = db.Column(db.String(200), nullable=True)  # path or filename
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    
    # Metadata
    submitted_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<VisaApplication {self.first_name} {self.last_name} - {self.passport_number}>'
    
class ProjectApplication(db.Model):
    __tablename__ = 'project_applications'
    
    user = db.relationship('User', back_populates='project_applications')
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Step 1: Personal Info
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)

    # Step 2: More Info
    street_address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    birth_day = db.Column(db.Integer, nullable=False)
    birth_month = db.Column(db.Integer, nullable=False)
    birth_year = db.Column(db.Integer, nullable=False)

    # Step 3: Project Details
    project_title = db.Column(db.String(255), nullable=False)
    project_description = db.Column(db.Text, nullable=False)
    project_uniqueness = db.Column(db.Text, nullable=False)
    target_market = db.Column(db.Text, nullable=False)

    # Step 4: Final Step
    business_location = db.Column(db.String(255), nullable=False)
    has_capital = db.Column(db.String(10), nullable=False)
    team_preference = db.Column(db.String(10), nullable=False)
    involvement = db.Column(db.String(10), nullable=False)
    file_name = db.Column(db.String(255))  # uploaded file path/name

    submitted_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class InvestorApplication(db.Model):
    __tablename__ = 'investor_applications'
    
    user = db.relationship('User', back_populates='investor_applications')
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Basic Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # Investment Details
    amount_range = db.Column(db.String(50), nullable=False)
    preferred_area = db.Column(db.String(100), nullable=False)
    preferred_state = db.Column(db.String(100), nullable=False)
    excluded_state = db.Column(db.String(100))
    
    # Contact Information
    street_address = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    
    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<InvestorApplication {self.first_name} {self.last_name}>'
    
class VentureApplication(db.Model):
    __tablename__ = 'venture_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    
    # Innovation Details
    innovation_title = db.Column(db.String(200), nullable=False)
    innovation_description = db.Column(db.Text, nullable=False)
    innovation_stage = db.Column(db.String(50), nullable=False)  # concept/prototype/patented/market
    industry = db.Column(db.String(50), nullable=False)
    
    # Documents
    proposal_filename = db.Column(db.String(255))
    supporting_filenames = db.Column(db.Text)  # JSON string of filenames
    website = db.Column(db.String(255))
    
    # Status and timestamps
    status = db.Column(db.String(20), default='pending')  # pending/review/approved/rejected
    terms_accepted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', back_populates='venture_applications')
    
    def get_supporting_files(self):
        import json
        return json.loads(self.supporting_filenames) if self.supporting_filenames else []
    
    def save_files(self, proposal_file, supporting_files):
        # Ensure upload directory exists
        os.makedirs('uploads/joint_ventures', exist_ok=True)
        
        # Save proposal
        if proposal_file:
            ext = os.path.splitext(proposal_file.filename)[1]
            self.proposal_filename = f"proposal_{self.id}{ext}"
            proposal_file.save(os.path.join('uploads/joint_ventures', self.proposal_filename))
        
        # Save supporting files
        if supporting_files:
            supporting_list = []
            for i, file in enumerate(supporting_files):
                if file.filename == '':  # Skip empty files
                    continue
                ext = os.path.splitext(file.filename)[1]
                filename = f"supporting_{self.id}_{i}{ext}"
                file.save(os.path.join('uploads/joint_ventures', filename))
                supporting_list.append(filename)
            
            import json
            self.supporting_filenames = json.dumps(supporting_list)  
    
class HousingApplication(db.Model):
    __tablename__ = 'housing_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    street_address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    
    # Location Details
    state = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    origin_lga = db.Column(db.String(100), nullable=False)
    preferred_location = db.Column(db.String(100), nullable=False)
    housing_type = db.Column(db.String(100), nullable=False)
    marital_status = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    
    # Income Details
    occupation = db.Column(db.String(100), nullable=False)
    income_range = db.Column(db.String(50), nullable=False)
    repayment_amount = db.Column(db.Float, nullable=False)
    
    # Final Details
    next_of_kin_name = db.Column(db.String(100), nullable=False)
    next_of_kin_relationship = db.Column(db.String(100), nullable=False)
    religion_place = db.Column(db.String(100))
    religious_leader = db.Column(db.String(100))
    traditional_ruler = db.Column(db.String(100))
    property_owned = db.Column(db.Boolean, nullable=False)
    
    # Status and timestamps
    status = db.Column(db.String(20), default='pending')  # pending/review/approved/rejected
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', back_populates='housing_applications')

class HireSellerApplication(db.Model):
    __tablename__ = 'hire_seller_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Seller Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    street_address = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    
    # Contact Details
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    
    # Vehicle Information
    vehicle_model = db.Column(db.String(100), nullable=False)
    year_of_entry = db.Column(db.Integer, nullable=False)
    purchase_cost = db.Column(db.Float, nullable=False)
    
    # Hire Details
    expected_hire_cost = db.Column(db.Float, nullable=False)
    is_first_hire = db.Column(db.Boolean, nullable=False)
    previous_hire_experience = db.Column(db.Text)
    number_of_vehicles = db.Column(db.Integer, nullable=False)
    
    # Status and timestamps
    status = db.Column(db.String(20), default='pending')  # pending/review/approved/rejected
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', back_populates='hire_seller_applications')
    
class HireBuyerApplication(db.Model):
    __tablename__ = 'hire_buyer_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    street_address = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    
    # Contact Details
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    
    # Hire Details
    driving_experience = db.Column(db.Integer, nullable=False)
    choice_of_hire = db.Column(db.String(100), nullable=False)
    alternative_choice = db.Column(db.String(100))
    
    # Additional Information
    next_of_kin = db.Column(db.String(200), nullable=False)
    religion_address1 = db.Column(db.String(200), nullable=False)
    religion_address2 = db.Column(db.String(200), nullable=False)
    religious_leader = db.Column(db.String(100), nullable=False)
    traditional_ruler = db.Column(db.String(200), nullable=False)
    
    # Status and timestamps
    status = db.Column(db.String(20), default='pending')  # pending/review/approved/rejected
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationship
    user = db.relationship('User', back_populates='hire_buyer_applications')


    

@login_manager.user_loader
def load_user(user_id):
    # Try to load as User first
    user = db.session.get(User, int(user_id))
    if user:
        return user
    
    # If not found as User, try as Admin
    admin = db.session.get(Admin, int(user_id))
    if admin:
        return admin
    
    return None


















# --------------------------------------------------
# INIT DATA
# --------------------------------------------------
def create_tables_and_initial_data():
    db.create_all()
    create_initial_programs()
    create_initial_admins()

def create_initial_programs():
    programs = [
        {'name': 'Project Management', 'slug': 'project_management', 'price': 50000, 'icon': 'fas fa-tasks'},
        {'name': 'Investor', 'slug': 'investor', 'price': 499999, 'icon': 'fas fa-chart-line'},
        {'name': 'Joint Venture', 'slug': 'joint_venture', 'price': 21500, 'icon': 'fas fa-lightbulb'},
        {'name': 'Visa Sponsorship', 'slug': 'visa', 'price': 37500, 'icon': 'fas fa-passport'},
        {'name': 'Priority Housing', 'slug': 'housing', 'price': 50000, 'icon': 'fas fa-home'},
        {'name': 'Hire Purchase (Buyer)', 'slug': 'hireb', 'price': 21000, 'icon': 'fas fa-truck-pickup'},
        {'name': 'Hire Purchase (Seller)', 'slug': 'hires', 'price': 21000, 'icon': 'fas fa-truck-pickup'}
    ]
    for prog in programs:
        if not Program.query.filter_by(slug=prog['slug']).first():
            db.session.add(Program(**prog))
    db.session.commit()

def create_initial_admins():
    admin_credentials = {
        'visaadmin@damascusprojects.com': 'visa',
        'ventureadmin@damascusprojects.com': 'joint_venture',
        'housingadmin@damascusprojects.com': 'housing',
        'investoradmin@damascusprojects.com': 'investor',
        'projectadmin@damascusprojects.com': 'project_management',
        'hirebadmin@damascusprojects.com': 'hireb',
        'hiresadmin@damascusprojects.com': 'hires'
    }
    
    default_password = "damascusprojectsadmin"
    
    for email, program_slug in admin_credentials.items():
        if not Admin.query.filter_by(email=email).first():
            admin = Admin(
                email=email,
                program_slug=program_slug
            )
            admin.set_password(default_password)
            db.session.add(admin)
    
    db.session.commit()

def generate_user_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def get_unique_user_code():
    while True:
        code = f"DP-{generate_user_code()}"
        if not User.query.filter_by(user_code=code).first():
            return code

def generate_order_number():
    """Generate timestamp-based order number with random suffix"""
    timestamp = datetime.now().strftime('%y%m')  # YYMM format
    random_suffix = random.randint(100, 999)     # 3 random digits
    order_number = f"#{timestamp}{random_suffix}" # Example: #240612345

    # Check if this order number already exists
    if not db.session.query(Subscription.query.filter(Subscription.order_number == order_number).exists()).scalar():
        return order_number

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def is_verification_code_valid(user, code):
    """Check if the verification code is valid and not expired"""
    if not user.verification_code or not user.verification_code_expires:
        return False
    return (user.verification_code == code and 
            datetime.now(timezone.utc) < user.verification_code_expires)

@app.route('/upload-profile-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    file = request.files.get('profile_picture')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            flash('Invalid file format. Please upload an image.', 'danger')
            return redirect(url_for('dashboard'))

        # rename to user id to avoid conflicts
        new_filename = f"user_{current_user.id}{file_ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
        
        current_user.profile_picture = new_filename
        db.session.commit()
        flash('Profile picture updated successfully.', 'success')
    else:
        flash('No file selected.', 'warning')

    return redirect(url_for('dashboard'))

















# --------------------------------------------------
# EMAILS
# --------------------------------------------------

def send_welcome_email(user, password):
    """Send welcome email with username, password, and user code"""
    try:
        subject = "Welcome to Damascus Projects & Services"
        recipient = user.email
        account_url = url_for('login', _external=True)

        # Intent URI to launch the app if installed
        intent_link = f"intent://app.damascusprojects.com/login#Intent;scheme=https;package=com.Damascus_Projects.app;end"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4361ee;">Welcome to Damascus Projects!</h2>
                
                <p>Hi {user.username},</p>
                
                <p>Thanks for creating an account on Damascus Projects & Services.</p>
                
                <p>Your username is <strong>{user.username}</strong>.</p>
                <p>Your password is: <strong>{password}</strong></p>
                
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #4361ee; margin: 20px 0;">
                    <p style="margin: 0;">Your user code is: <strong style="font-size: 1.1em;">{user.user_code}</strong></p>
                    <p style="margin: 10px 0 0 0;">Please keep this code safe, as it will be used to verify your identity whenever you need support. You can also find it in the bottom-left corner of your account dashboard.</p>
                </div>
                
                <p>You can access your account area to see your subscriptions, change your password, and more.</p>
                
                <div style="margin: 25px 0; text-align: center;">
                    <a href="{account_url}" 
                       style="background-color: #4361ee; color: white; 
                              padding: 12px 24px; text-decoration: none; 
                              border-radius: 5px; display: inline-block;
                              font-weight: bold;">
                        Go to your account
                    </a>
                </div>

                <div style="margin: 15px 0; text-align: center;">
                    <a href="{intent_link}" 
                       style="color: #4361ee; font-weight: bold; text-decoration: underline;">
                        Open in App (for mobile users)
                    </a>
                </div>

                <p>We look forward to seeing you soon.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                
                <p style="color: #666; font-size: 0.9em;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{account_url}" style="color: #4361ee;">{account_url}</a>
                </p>
            </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
Welcome to Damascus Projects & Services!

Hi {user.username},

Thanks for creating an account with us.

Your account details:
Username: {user.username}
Password: {password}
User Code: {user.user_code}

IMPORTANT: Please keep your user code safe, as it will be used to verify 
your identity whenever you need support. You can also find it in the 
bottom-left corner of your account dashboard.

Access your account here:
{account_url}

Open in app:
{intent_link}

You can use your account to:
- View your subscriptions
- Change your password
- Manage your services

We look forward to seeing you soon.

---
Damascus Projects & Services
        """
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_content,
            body=text_content
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Registration successful but failed to send welcome email to {recipient}: {str(e)}")
        return False    

def send_subscription_confirmation(user, subscription, order_number):
    """Send subscription confirmation email with payment instructions"""
    try:
        subject = f"Order #{order_number} - Payment Confirmation Required"
        recipient = user.email
        
        # HTML email content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto; color: #333;">
                <h2 style="color: #4361ee;">Order #{order_number}</h2>
                
                <p>Hi {user.first_name}, thank you for your subscription.</p>
                
                <div style="background: #fff8e6; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <p style="margin: 0; font-weight: bold;">Kindly note that your subscription will only be activated after we confirm receipt of your payment.</p>
                </div>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{url_for('upload_receipt', sub_id=subscription.id, _external=True)}" 
                       style="background-color: #4361ee; color: white; 
                              padding: 12px 24px; text-decoration: none; 
                              border-radius: 5px; display: inline-block;
                              font-weight: bold;">
                        UPLOAD PAYMENT RECEIPT
                    </a>
                </div>
                
                <div style="border: 1px solid #eee; padding: 20px; margin-bottom: 20px;">
                    <h3 style="margin-top: 0; color: #4361ee;">{subscription.program.name}</h3>
                    <p>Quantity: 1</p>
                    <p style="font-size: 1.2em; font-weight: bold;">₦{subscription.program.price:,.2f}</p>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                    <div style="width: 48%;">
                        <h4 style="color: #4361ee;">Payment Method</h4>
                        <p>Direct bank transfer</p>
                    </div>
                    <div style="width: 48%;">
                        <h4 style="color: #4361ee;">Total</h4>
                        <p style="font-weight: bold;">₦{subscription.program.price:,.2f}</p>
                    </div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <h4 style="color: #4361ee;">Billing Address</h4>
                    <p>{user.first_name} {user.last_name}<br>
                    {user.town}<br>
                    {user.country}<br>
                    {user.phone}<br>
                    {user.email}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <h4 style="color: #4361ee;">Get in Touch</h4>
                    <p>
                        <a href="https://facebook.com/yourpage" style="margin: 0 10px; color: #4361ee; text-decoration: none;">facebook</a>
                        <a href="https://twitter.com/yourhandle" style="margin: 0 10px; color: #4361ee; text-decoration: none;">twitter</a>
                        <a href="https://instagram.com/yourprofile" style="margin: 0 10px; color: #4361ee; text-decoration: none;">instagram</a>
                    </p>
                </div>
                
                <div style="border-top: 1px solid #eee; padding-top: 15px; color: #666; font-size: 0.8em;">
                    <p>This email was sent by: admin@damascusprojects.com</p>
                    <p>For any questions please send an email to <a href="mailto:info@damascusprojects.com" style="color: #4361ee;">info@damascusprojects.com</a></p>
                </div>
            </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
Order #{order_number}

Hi {user.first_name}, thank you for your subscription.

IMPORTANT: Your subscription will only be activated after we confirm receipt of your payment.

Upload your payment receipt here:
{url_for('upload_receipt', sub_id=subscription.id, _external=True)}

Subscription Details:
{subscription.program.name}
Quantity: 1
Amount: ₦{subscription.program.price:,.2f}

Payment Method: Direct bank transfer
Total Amount: ₦{subscription.program.price:,.2f}

Billing Address:
{user.first_name} {user.last_name}
{user.town}
{user.country}
Phone: {user.phone}
Email: {user.email}

Contact Us:
Facebook: https://facebook.com/yourpage
Twitter: https://twitter.com/yourhandle
Instagram: https://instagram.com/yourprofile

This email was sent by: admin@damascusprojects.com
For any questions please email: info@damascusprojects.com
        """
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_content,
            body=text_content,
            sender=("Damascus Projects", "admin@damascusprojects.com")
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send subscription confirmation to {recipient}: {str(e)}")
        return False
    
def send_application_email(user):
    """Send send successful application email with username, email and order number"""
    try:
        subject = "Congratulations from Damascus Projects & Services"
        recipient = user.email
        account_url = url_for('login', _external=True)
        
        # HTML email content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4361ee;">Welcome to Damascus Projects!</h2>
                
                <p>Hi {user.username},</p>
                
                <p>Thanks for applying for {user.program} on Damascus Projects & Services.</p>
                
                <p>Your username is <strong>{user.username}</strong>.</p>
                
                <p>Your order is: <strong>{user.subscription.order_number}</strong></p>
                
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #4361ee; margin: 20px 0;">
                    <p style="margin: 0;">Your user code is: <strong style="font-size: 1.1em;">{user.user_code}</strong></p>
                    <p style="margin: 10px 0 0 0;">Please keep this code safe, as it will be used to verify your identity whenever you need support. You can also find it in the bottom-left corner of your account dashboard.</p>
                </div>
                
                <p>You can access your account area to see your subscriptions, change your password, and more.</p>
                
                <div style="margin: 25px 0; text-align: center;">
                    <a href="{account_url}" 
                       style="background-color: #4361ee; color: white; 
                              padding: 12px 24px; text-decoration: none; 
                              border-radius: 5px; display: inline-block;
                              font-weight: bold;">
                        Go to your account
                    </a>
                </div>
                
                <p>We look forward to seeing you soon.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                
                <p style="color: #666; font-size: 0.9em;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{account_url}" style="color: #4361ee;">{account_url}</a>
                </p>
            </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
Welcome to Damascus Projects & Services!

Hi {user.username},

Thanks for creating an account with us.

Your account details:
Username: {user.username}
OrderNumber: {user.subscription.order_number}
User Code: {user.user_code}

IMPORTANT: Please keep your user code safe, as it will be used to verify 
your identity whenever you need support. You can also find it in the 
bottom-left corner of your account dashboard.

Access your account here:
{account_url}

You can use your account to:
- View your subscriptions
- Change your password
- Manage your services

We look forward to seeing you soon.

---
Damascus Projects & Services
        """
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_content,
            body=text_content,
            sender=("Damascus Projects", "admin@damascusprojects.com")
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Application successful but failed to send welcome email to {recipient}: {str(e)}")
        return False

def send_verification_email(user):
    """Send email verification code to user"""
    try:
        # Generate and save verification code
        verification_code = generate_verification_code()
        user.verification_code = verification_code
        user.verification_code_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        db.session.commit()

        subject = "Damascus Projects & Services - Verify Your Email"
        recipient = user.email
        
        # HTML email content
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4361ee;">Email Verification Required</h2>
                
                <p>Hi {user.username},</p>
                
                <p>Thank you for registering with Damascus Projects & Services. 
                Please use the following verification code to complete your account setup.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #4361ee; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; font-size: 24px; font-weight: bold; letter-spacing: 2px;">
                        {verification_code}
                    </p>
                    <p style="margin: 10px 0 0 0;">This code will expire in 24 hours.</p>
                </div>
                
                <p>Enter this code in the verification page of our application to verify your email address.</p>
                
                <p>If you didn't create an account with us, please ignore this email.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                
                <p style="color: #666; font-size: 0.9em;">
                    For security reasons, do not share this code with anyone.
                </p>
            </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
Email Verification - Damascus Projects & Services

Hi {user.username},

Thank you for registering with us. Please use the following verification code to complete your account setup.

Your verification code is: {verification_code}

This code will expire in 24 hours.

Enter this code in the verification page of our application to verify your email address.

If you didn't create an account with us, please ignore this email.

---
Damascus Projects & Services
        """
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_content,
            body=text_content,
            sender=("Damascus Projects", "noreply@damascusprojects.com")
        )
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Failed to send verification email: {str(e)}")
        return False
        
def send_reset_email(user, reset_link):
    subject = "Password Reset Request - Damascus Projects"
    recipient = user.email

    html_content = f"""
    <html>
        <body>
            <h2>Password Reset</h2>
            <p>Hi {user.username},</p>
            <p>To reset your password, click the button below:</p>
            <p><a href="{reset_link}" style="padding:10px 20px; background-color:#4361ee; color:white; text-decoration:none;">Reset Password</a></p>
            <p>If you didn’t request this, just ignore this email.</p>
        </body>
    </html>
    """

    msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_content,
            sender=("Damascus Projects", "admin@damascusprojects.com")
        )
    mail.send(msg)
    return True









# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/project-management')
def project_management():
    return render_template('project_management.html')

@app.route('/investor')
def investor():
    return render_template('investor.html')

@app.route('/venture')
def venture():
    return render_template('venture.html')

@app.route('/visa')
def visa():
    return render_template('visa.html')

@app.route('/housing')
def housing():
    return render_template('housing.html')

@app.route('/hire')
def hire():
    return render_template('hire.html')

@app.route("/applications/<slug>")
def apply_program(slug):
    # Mapping slug to template
    templates = {
        "project_management": "applications/pm.html",
        "visa": "applications/visa.html",
        "investor": "applications/investor.html",
        "venture": "applications/venture.html",
        "housing": "applications/housing.html",
        "hireb": "applications/hire-buyer.html",
        "hires": "applications/hire-seller.html"
    }

    if slug in templates:
        return render_template(templates[slug])
    else:
        flash("Invalid program selected.", "warning")
        return redirect(url_for("dashboard"))

@app.route('/choose-program')
@login_required
def choose_program():
    programs = Program.query.all()
    return render_template('choose_program.html', programs=programs)

@app.route('/programs/<slug>')
@login_required
def program_detail(slug):
    program = Program.query.filter_by(slug=slug).first_or_404()
    return render_template('program_detail.html', program=program)

@app.route('/hire-purchase')
@login_required
def hire_purchase():
    return render_template('hire_purchase.html')

@app.route('/subscribe/<slug>')
@login_required
def subscribe(slug):
    program = Program.query.filter_by(slug=slug).first_or_404()
    subscription = Subscription(user_id=current_user.id, program_id=program.id)
    db.session.add(subscription)
    db.session.commit()
    return redirect(url_for('payment_details', sub_id=subscription.id))

@app.route('/subscription', methods=['GET', 'POST'])
@login_required
def subscription():
    return "This route is not implemented yet. Please check back later.", 501

@app.route('/payment-details/<program_slug>', methods=['GET', 'POST'])
@login_required
def payment_details(program_slug):
    program = Program.query.filter_by(slug=program_slug).first_or_404()
    subscription = Subscription(
        user_id=current_user.id,
        program_id=program.id,
    )
    db.session.add(subscription)
    subscription.order_number = generate_order_number()
    db.session.commit()
    send_subscription_confirmation(
        user=current_user,
        subscription=subscription,
        order_number=subscription.order_number
    )
    return render_template('payment_details.html', subscription=subscription, program=program)


@app.route('/confirm-payment/<int:sub_id>' , methods=['GET', 'POST'])
@login_required
def confirm_payment(sub_id):
    if request.method == 'POST':
        town = request.form.get('town')
        country = request.form.get('country')
        phone = request.form.get('phone')
        subscription = Subscription.query.get_or_404(sub_id)
        if subscription.is_paid:
            flash('Payment already confirmed.', 'info')
            return redirect(url_for('dashboard'))
        subscription.paid_at = datetime.now(timezone.utc)
        current_user.town = town
        current_user.country = country
        current_user.phone = phone
        db.session.commit()
        flash('Your payment is being processed! Thank you for subscribing.', 'success')
        return redirect(url_for('upload_receipt', sub_id=sub_id))
    
    return "Request method not allowed.", 405

@app.route('/upload-receipt/<int:sub_id>', methods=['GET', 'POST'])
@login_required
def upload_receipt(sub_id):
    subscription = Subscription.query.get_or_404(sub_id)
    
    # Ensure the subscription has an order number
    if not subscription.order_number:
        flash('No order number associated with this subscription.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        file = request.files['receipt']
        if file:
            # Get file extension from the original filename
            file_ext = os.path.splitext(file.filename)[1]
            
            # Create new filename using order number
            new_filename = f"receipt_{subscription.order_number}{file_ext}"
            new_filename = secure_filename(new_filename)
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(filepath)
            
            subscription.payment_receipt = new_filename
            db.session.commit()
            
            flash('Receipt uploaded successfully.', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('upload_receipt.html', subscription=subscription)


@app.route('/dashboard')
@login_required
def dashboard():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    programs = Program.query.all()
    return render_template('dashboard.html', subscriptions=subscriptions, programs=programs)






@app.route('/mark_payment_done', methods=['POST'])
@login_required
def mark_payment_done():
    this_user = Subscription.query.filter_by(user_id=current_user.id).first()
    this_user.status = 'pending'
    db.session.commit()
    flash('Thank you! Your payment is being processed.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/cancel-subscription/<int:program_id>', methods=['GET', 'POST'])
@login_required
def cancel_subscription(program_id):
    subscription = Subscription.query.filter_by(user_id=current_user.id, id=program_id).first()
    if subscription:
        db.session.delete(subscription)
        db.session.commit()
        flash('Subscription cancelled successfully.', 'success')
    else:
        flash('Subscription not found.', 'danger')
    return redirect(url_for('dashboard'))







@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Input validation
        if not all([username, first_name, last_name, email, password, confirm_password]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        # Set default phone if not provided
        if not phone:
            phone = 'N/A'

        # Check for existing user by email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if existing_user.verified:
                flash('Email already registered. Please login instead.', 'warning')
                return redirect(url_for('login'))
            else:
                # Resend verification to existing unverified user
                if send_verification_email(existing_user):
                    flash('Email already registered but not verified. A new verification code has been sent.', 'warning')
                else:
                    flash('Email already registered but we failed to resend verification. Please try again.', 'danger')
                return redirect(url_for('verify_email') + f"?email={email}")

        # Create new user
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            verified=False  # Explicitly set to False
        )
        user.set_password(password)
        user.user_code = get_unique_user_code()

        # Generate and store verification code
        verification_code = generate_verification_code()
        user.verification_code = verification_code
        user.verification_code_expires = datetime.now(timezone.utc) + timedelta(hours=24)

        db.session.add(user)
        
        try:
            db.session.commit()
            
            # Send verification email
            if send_verification_email(user):
                flash('Registration successful! Please check your email for the verification code.', 'success')
                return redirect(url_for('verify_email') + f"?email={email}")
            else:
                # If email fails, delete the user and show error
                db.session.delete(user)
                db.session.commit()
                flash('Failed to send verification email. Please try again.', 'danger')
                return redirect(url_for('signup'))
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error during signup: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')

   
@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    email = request.args.get('email') or request.form.get('email')
    
    if request.method == 'POST':
        code = request.form.get('code')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('signup'))
        
        if is_verification_code_valid(user, code):
            user.verified = True
            user.verification_code = None
            user.verification_code_expires = None
            db.session.commit()
            
            login_user(user)
            flash('Email verified successfully!', 'success')
            return redirect(url_for('dashboard'))  # Change to your dashboard route
        else:
            flash('Invalid or expired verification code.', 'danger')
            return render_template('verify_email.html', email=email)

    return render_template('verify_email.html', email=email)

@app.route('/resend-verification', methods=['POST', 'GET'])
def resend_verification():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found. Please check your email or sign up.', 'danger')
        return redirect(url_for('signup'))

    if user.email_verified:
        flash('Email already verified. You can log in now.', 'info')
        return redirect(url_for('login'))
    
    if send_verification_email(user):
        flash('Verification code resent. Please check your inbox.', 'success')
        return redirect(url_for('login'))
    else:
        flash('Failed to resend verification code', 'error')
        return redirect(url_for('resend_verification'))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier').strip()
        password = request.form.get('password')

        user = None
        if '@' in identifier and '.' in identifier:
            # It's likely an email
            user = User.query.filter_by(email=identifier.lower()).first()
        else:
            # It's likely a phone number
            user = User.query.filter_by(phone=identifier).first()
        if user:
            if not user.verified:
                # If user is not verified, redirect to verification page
                send_verification_email(user)
                flash('Please verify your email.', 'info')
                return redirect(url_for('verify_email') + f"?email={user.email}")
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('choose_program'))
        flash('Invalid credentials', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')
    














@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(email=email).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Get the logged-in admin's details
    admin = Admin.query.get(current_user.id)
    if not admin:
        abort(404)
    
    # Find the program this admin manages
    program = Program.query.filter_by(slug=admin.program_slug).first()
    if not program:
        abort(404)
    
    # Fetch users with their subscriptions to this admin's program
    # Include subscription status and payment receipt information
    subscribed_users = User.query.join(Subscription).join(Program).filter(
        Program.slug == program.slug
    ).options(
        db.joinedload(User.subscriptions).joinedload(Subscription.program)
    ).all()
    
    return render_template('admin_dashboard.html', 
                         users=subscribed_users,
                         program_name=program.name.title(),
                         program_slug=program.slug)

@app.route('/export-subscribers/<program_slug>')
@login_required
def export_subscribers(program_slug):
    program = Program.query.filter_by(slug=program_slug).first_or_404()
    
    # Fetch all subscriptions for this program
    subscriptions = Subscription.query.filter_by(program_id=program.id).all()
    
    if not subscriptions:
        flash('No subscribers found for this program.', 'info')
        return redirect(url_for('admin_dashboard'))
    
    # Create a CSV response
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Username', 'Email', 'Phone', 'Subscription Status', 'Payment Receipt'])
    
    # Write subscriber data
    for sub in subscriptions:
        user = sub.user
        writer.writerow([
            user.username,
            user.email,
            user.phone,
            sub.status,
            sub.payment_receipt or 'N/A'
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={program_slug}_subscribers.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response

@app.route('/approve-subscription/<int:sub_id>')
@login_required
def approve_subscription(sub_id):
    subscription = Subscription.query.get_or_404(sub_id)
    subscription.status = 'approved'
    subscription.is_paid = True  # Mark as paid
    db.session.commit()
    flash('Subscription approved', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/decline-subscription/<int:sub_id>')
@login_required
def decline_subscription(sub_id):
    subscription = Subscription.query.get_or_404(sub_id)
    subscription.status = 'declined'
    subscription.is_paid = False  # Mark as not paid
    db.session.commit()
    flash('Subscription declined', 'warning')
    return redirect(url_for('admin_dashboard'))











@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.get_reset_token()
            reset_link = url_for('reset_password', token=token, _external=True)
            send_reset_email(user, reset_link)
            flash("A reset link has been sent to your email.", "success")
        else:
            flash("Email not found in our records.", "danger")
        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash("The reset link is invalid or has expired.", "warning")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        user.set_password(new_password)
        db.session.commit()
        flash("Password updated successfully. You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)




@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))










@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    firstname = request.form.get('firstname', '').strip()
    lastname = request.form.get('lastname', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()

    user = current_user
    updated = False

    if firstname and firstname != user.first_name:
        user.firstname = firstname
        updated = True

    if lastname and lastname != user.last_name:
        user.lastname = lastname
        updated = True

    if username and username != user.username:
        user.username = username
        updated = True

    if email and email != user.email:
        user.email = email
        user.verified = False
        updated = True

    if phone and phone != user.phone:
        user.phone = phone
        updated = True

    if updated:
        try:
            db.session.commit()
            flash("Profile updated successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating your profile.", "danger")
    else:
        flash("No changes detected.", "info")

    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not check_password_hash(current_user.password_hash, current_password):
        flash("Incorrect current password.", "danger")
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for('profile'))

    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash("Password changed successfully.", "success")
    return redirect(url_for('profile'))














@app.route('/delete_account', methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        # Verify password
        password = request.form.get('password')
        if not check_password_hash(current_user.password_hash, password):
            flash('Incorrect password', 'danger')
            return redirect(url_for('delete_account'))

        # Create record in DeletedAccounts
        deleted_user = DeletedAccounts(
            email=current_user.email,
            username=current_user.username,
            reason=request.form.get('reason', 'No reason provided')
        )

        try:
            db.session.add(deleted_user)
            
            # Define a helper function for safe file deletion
            def safe_delete_file(filepath):
                try:
                    if filepath and os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    app.logger.error(f"Error deleting file {filepath}: {str(e)}")

            # Delete all user-related data from all models with file cleanup
            
            # Subscription model
            if Subscription.query.filter_by(user_id=current_user.id).first():
                Subscription.query.filter_by(user_id=current_user.id).delete()
            
            # Visa applications (check for resume file)
            visa_apps = VisaApplication.query.filter_by(user_id=current_user.id).all()
            if visa_apps:
                for vapp in visa_apps:
                    if vapp.resume_filename:
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'visa_resumes', vapp.resume_filename)
                        safe_delete_file(filepath)
                VisaApplication.query.filter_by(user_id=current_user.id).delete()
            
            # Project applications (check for uploaded file)
            project_apps = ProjectApplication.query.filter_by(user_id=current_user.id).all()
            if project_apps:
                for papp in project_apps:
                    if papp.file_name:
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'project_files', papp.file_name)
                        safe_delete_file(filepath)
                ProjectApplication.query.filter_by(user_id=current_user.id).delete()
            
            # Investor applications (no files to delete)
            if InvestorApplication.query.filter_by(user_id=current_user.id).first():
                InvestorApplication.query.filter_by(user_id=current_user.id).delete()
            
            # Venture applications (proposal and supporting files)
            venture_apps = VentureApplication.query.filter_by(user_id=current_user.id).all()
            if venture_apps:
                for venture in venture_apps:
                    if venture.proposal_filename:
                        filepath = os.path.join('uploads/joint_ventures', venture.proposal_filename)
                        safe_delete_file(filepath)
                    if venture.supporting_filenames:
                        try:
                            for filename in venture.get_supporting_files():
                                filepath = os.path.join('uploads/joint_ventures', filename)
                                safe_delete_file(filepath)
                        except Exception as e:
                            app.logger.error(f"Error deleting supporting files: {str(e)}")
                VentureApplication.query.filter_by(user_id=current_user.id).delete()
            
            # Housing applications (no files to delete)
            if HousingApplication.query.filter_by(user_id=current_user.id).first():
                HousingApplication.query.filter_by(user_id=current_user.id).delete()
            
            # Hire seller applications (no files to delete)
            if HireSellerApplication.query.filter_by(user_id=current_user.id).first():
                HireSellerApplication.query.filter_by(user_id=current_user.id).delete()
            
            # Hire buyer applications (no files to delete)
            if HireBuyerApplication.query.filter_by(user_id=current_user.id).first():
                HireBuyerApplication.query.filter_by(user_id=current_user.id).delete()

            # Finally delete the user
            db.session.delete(current_user)
            db.session.commit()
            
            logout_user()
            flash('Your account and all associated data have been permanently deleted', 'info')
            return redirect(url_for('home'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Account deletion failed for user {current_user.id}: {str(e)}")
            flash('Error deleting account. Please try again.', 'danger')
            return redirect(url_for('delete_account'))
    
    return render_template('delete_account.html')  
    
    
@app.route('/health')
def health():
    return "OK", 200

with app.app_context():
    # Create tables and initial data
    create_tables_and_initial_data()









# --------------------------------------------------
# APPLICATIONS SUBMISSION
# --------------------------------------------------

@app.route('/submit_visa', methods=['GET', 'POST'])
@login_required
def submit_visa():
    if request.method == 'POST':
        try:
            # Step 1: Personal Info
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            birth_day = request.form.get('birth_day')
            birth_month = request.form.get('birth_month')
            birth_year = request.form.get('birth_year')
            nationality = request.form.get('nationality')
            gender = request.form.get('gender')
            marital_status = request.form.get('marital_status')

            # Step 2: Education & Travel
            education_level = request.form.get('education_level')
            country_of_interest = request.form.get('country_of_interest')
            travel_purpose = request.form.get('travel_purpose')
            language_proficiency = request.form.get('language_proficiency')
            passport_number = request.form.get('passport_number')

            # Step 3: Documents & Contact
            phone = request.form.get('phone')
            email = request.form.get('email')
            
            # Handle Resume Upload
            resume_file = request.files.get('resume')
            resume_filename = None
            if resume_file and resume_file.filename != '':
                if not allowed_file(resume_file.filename, 'visa'):
                    flash('Invalid file type for resume', 'error')
                    return redirect(request.url)
                
                resume_filename = save_uploaded_file(resume_file, 'visa', current_user.id, 'resume')

            # Save to Database
            application = VisaApplication(
                user_id=current_user.id,
                first_name=first_name,
                last_name=last_name,
                birth_day=birth_day,
                birth_month=birth_month,
                birth_year=birth_year,
                nationality=nationality,
                gender=gender,
                marital_status=marital_status,
                education_level=education_level,
                country_of_interest=country_of_interest,
                travel_purpose=travel_purpose,
                language_proficiency=language_proficiency,
                passport_number=passport_number,
                phone=phone,
                email=email,
                resume_filename=resume_filename
            )
            db.session.add(application)
            db.session.commit()
            send_application_email(current_user)
            flash('Visa application submitted successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(request.url)
    
    return render_template('login.html')

@app.route('/submit_pm', methods=['POST'])
@login_required
def submit_pm():
    try:
        data = request.form
        file = request.files.get('fileUpload')
        file_name = None

        if file and file.filename != '':
            if not allowed_file(file.filename, 'project_management'):
                flash('Invalid file type for project document', 'error')
                return redirect(url_for('dashboard'))
            
            file_name = save_uploaded_file(file, 'project_management', current_user.id, 'project_file')

        application = ProjectApplication(
            user_id=current_user.id,
            first_name=data.get('firstName'),
            last_name=data.get('lastName'),
            phone=data.get('phone'),
            email=data.get('email'),
            street_address=data.get('streetAddress'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zipCode'),
            country=data.get('country'),
            gender=data.get('gender'),
            birth_day=int(data.get('birthDay')),
            birth_month=int(data.get('birthMonth')),
            birth_year=int(data.get('birthYear')),
            project_title=data.get('projectTitle'),
            project_description=data.get('projectDescription'),
            project_uniqueness=data.get('projectUniqueness'),
            target_market=data.get('targetMarket'),
            business_location=data.get('businessLocation'),
            has_capital=data.get('hasCapital'),
            team_preference=data.get('teamPreference'),
            involvement=data.get('involvement'),
            file_name=file_name
        )

        db.session.add(application)
        db.session.commit()
        send_application_email(current_user)

        flash("Application submitted successfully.", "success")
        return redirect(url_for('dashboard'))

    except Exception as e:
        db.session.rollback()
        flash(f"Error submitting application: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

 
@app.route('/submit_venture', methods=['POST'])
@login_required
def submit_venture():
    if request.method == 'POST':
        try:
            # Get form data
            form_data = {
                'first_name': request.form.get('firstName'),
                'last_name': request.form.get('lastName'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'innovation_title': request.form.get('innovationTitle'),
                'innovation_description': request.form.get('innovationDescription'),
                'innovation_stage': request.form.get('innovationStage'),
                'industry': request.form.get('industry'),
                'website': request.form.get('website'),
                'terms_accepted': request.form.get('terms') == 'on'
            }
            
            # Validate required fields
            required_fields = ['first_name', 'last_name', 'email', 'phone', 
                              'innovation_title', 'innovation_description',
                              'innovation_stage', 'industry']
            for field in required_fields:
                if not form_data[field]:
                    flash(f'Missing required field: {field}', 'error')
                    return redirect(url_for('dashboard'))
            
            if not form_data['terms_accepted']:
                flash('You must accept the terms and conditions', 'error')
                return redirect(url_for('dashboard'))
            
            # Get files
            proposal_file = request.files.get('proposal')
            supporting_files = request.files.getlist('supportingDocs')
            
            if not proposal_file or proposal_file.filename == '':
                flash('Innovation proposal is required', 'error')
                return redirect(url_for('dashboard'))
            
            if not allowed_file(proposal_file.filename, 'joint_venture'):
                flash('Invalid file type for proposal', 'error')
                return redirect(url_for('dashboard'))
            
            # Create application
            new_application = VentureApplication(
                user_id=current_user.id,
                **{k: v for k, v in form_data.items() if k != 'terms_accepted'}
            )
            new_application.terms_accepted = form_data['terms_accepted']
            
            db.session.add(new_application)
            db.session.commit()  # Need ID for filenames
            send_application_email(current_user)
            
            # Save files
            try:
                # Save proposal
                proposal_filename = save_uploaded_file(proposal_file, 'joint_venture', new_application.id, 'proposal')
                new_application.proposal_filename = proposal_filename
                
                # Save supporting documents
                supporting_filenames = []
                for i, file in enumerate(supporting_files):
                    if file and file.filename != '':
                        if allowed_file(file.filename, 'joint_venture'):
                            filename = save_uploaded_file(file, 'joint_venture', new_application.id, f'supporting_{i}')
                            supporting_filenames.append(filename)
                
                new_application.supporting_filenames = ','.join(supporting_filenames)
                db.session.commit()
                
                flash('Your joint venture application has been submitted successfully!', 'success')
                return redirect(url_for('dashboard'))
                
            except Exception as file_error:
                db.session.rollback()
                app.logger.error(f'File save error: {str(file_error)}')
                flash('Error saving files. Please try again.', 'error')
                return redirect(url_for('dashboard'))
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Application error: {str(e)}')
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('dashboard'))

@app.route('/submit_housing', methods=['POST'])
@login_required
def submit_housing():
    if request.method == 'POST':
        try:
            # Get form data
            form_data = {
                # Personal Information
                'first_name': request.form.get('firstName'),
                'last_name': request.form.get('lastName'),
                'phone': request.form.get('phone'),
                'email': request.form.get('email'),
                'street_address': request.form.get('streetAddress'),
                'city': request.form.get('city'),
                
                # Location Details
                'state': request.form.get('state'),
                'country': request.form.get('country'),
                'origin_lga': request.form.get('originLGA'),
                'preferred_location': request.form.get('preferredLocation'),
                'housing_type': request.form.get('housingType'),
                'marital_status': request.form.get('maritalStatus'),
                'date_of_birth': datetime.strptime(request.form.get('dob'), '%Y-%m-%d').date(),
                
                # Income Details
                'occupation': request.form.get('occupation'),
                'income_range': request.form.get('incomeRange'),
                'repayment_amount': float(request.form.get('repaymentAmount')),
                
                # Final Details
                'next_of_kin_name': request.form.get('nextOfKinName'),
                'next_of_kin_relationship': request.form.get('nextOfKinRelationship'),
                'religion_place': request.form.get('religionPlace'),
                'religious_leader': request.form.get('religiousLeader'),
                'traditional_ruler': request.form.get('traditionalRuler'),
                'property_owned': request.form.get('propertyOwned') == 'yes'
            }
            
            # Validate required fields
            required_fields = [
                'first_name', 'last_name', 'phone', 'street_address', 'city',
                'state', 'country', 'origin_lga', 'preferred_location', 'housing_type',
                'marital_status', 'date_of_birth', 'occupation', 'income_range',
                'repayment_amount', 'next_of_kin_name', 'next_of_kin_relationship'
            ]
            
            for field in required_fields:
                if not form_data.get(field):
                    flash(f'Missing required field: {field}', 'error')
                    return redirect(url_for('dashboard'))
            
            # Handle document uploads if any
            proof_of_income = request.files.get('proof_of_income')
            proof_filename = None
            if proof_of_income and proof_of_income.filename != '':
                if not allowed_file(proof_of_income.filename, 'housing'):
                    flash('Invalid file type for proof of income', 'error')
                    return redirect(url_for('dashboard'))
                
                proof_filename = save_uploaded_file(proof_of_income, 'housing', current_user.id, 'proof_of_income')
            
            # Create application
            new_application = HousingApplication(
                user_id=current_user.id,
                proof_of_income_filename=proof_filename,
                **form_data
            )
            
            db.session.add(new_application)
            db.session.commit()
            send_application_email(current_user)
            
            flash('Your housing application has been submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            db.session.rollback()
            flash('Invalid data format. Please check your inputs.', 'error')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Housing application error: {str(e)}')
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('dashboard'))

@app.route('/submit_hire_seller', methods=['POST'])
@login_required
def submit_hire_seller():
    if request.method == 'POST':
        try:
            # Get form data
            form_data = {
                # Seller Information
                'first_name': request.form.get('firstName'),
                'last_name': request.form.get('lastName'),
                'street_address': request.form.get('streetAddress'),
                'address_line2': request.form.get('addressLine2'),
                'city': request.form.get('city'),
                
                # Contact Details
                'state': request.form.get('state'),
                'zip_code': request.form.get('zipCode'),
                'country': request.form.get('country'),
                'phone': request.form.get('phone'),
                'email': request.form.get('email'),
                
                # Vehicle Information
                'vehicle_model': request.form.get('vehicleModel'),
                'year_of_entry': int(request.form.get('yearOfEntry')),
                'purchase_cost': float(request.form.get('purchaseCost')),
                
                # Hire Details
                'expected_hire_cost': float(request.form.get('expectedHireCost')),
                'is_first_hire': request.form.get('firstHire') == 'yes',
                'previous_hire_experience': request.form.get('previousHireExperience'),
                'number_of_vehicles': int(request.form.get('numberOfVehicles'))
            }
            
            # Validate required fields
            required_fields = [
                'first_name', 'last_name', 'street_address', 'city',
                'state', 'country', 'phone', 'email',
                'vehicle_model', 'year_of_entry', 'purchase_cost',
                'expected_hire_cost', 'number_of_vehicles'
            ]
            
            for field in required_fields:
                if not form_data.get(field):
                    flash(f'Missing required field: {field}', 'error')
                    return redirect(url_for('hire_seller_form'))
            
            # Validate previous hire experience if not first hire
            if not form_data['is_first_hire'] and not form_data['previous_hire_experience']:
                flash('Please describe your previous hire experience', 'error')
                return redirect(url_for('hire_seller_form'))
            
            # Handle vehicle documents upload
            vehicle_docs = request.files.get('vehicle_docs')
            vehicle_docs_filename = None
            if vehicle_docs and vehicle_docs.filename != '':
                if not allowed_file(vehicle_docs.filename, 'hire_seller'):
                    flash('Invalid file type for vehicle documents', 'error')
                    return redirect(url_for('hire_seller_form'))
                
                vehicle_docs_filename = save_uploaded_file(vehicle_docs, 'hire_seller', current_user.id, 'vehicle_docs')
            
            # Create application
            new_application = HireSellerApplication(
                user_id=current_user.id,
                vehicle_docs_filename=vehicle_docs_filename,
                **form_data
            )
            
            db.session.add(new_application)
            db.session.commit()
            send_application_email(current_user)
            
            flash('Your hire seller application has been submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            db.session.rollback()
            flash('Invalid data format. Please check your inputs.', 'error')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Hire seller application error: {str(e)}')
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('dashboard'))

@app.route('/submit_hire_buyer', methods=['POST'])
@login_required
def submit_hire_buyer():
    if request.method == 'POST':
        try:
            # Get form data
            form_data = {
                # Personal Information
                'first_name': request.form.get('firstName'),
                'last_name': request.form.get('lastName'),
                'street_address': request.form.get('streetAddress'),
                'address_line2': request.form.get('addressLine2'),
                'city': request.form.get('city'),
                
                # Contact Details
                'state': request.form.get('state'),
                'zip_code': request.form.get('zipCode'),
                'country': request.form.get('country'),
                'phone': request.form.get('phone'),
                'email': request.form.get('email'),
                
                # Hire Details
                'driving_experience': int(request.form.get('drivingExperience')),
                'choice_of_hire': request.form.get('choiceOfHire'),
                'alternative_choice': request.form.get('alternativeChoice'),
                
                # Additional Information
                'next_of_kin': request.form.get('nextOfKin'),
                'religion_address1': request.form.get('religionAddress1'),
                'religion_address2': request.form.get('religionAddress2'),
                'religious_leader': request.form.get('religiousLeader'),
                'traditional_ruler': request.form.get('traditionalRuler')
            }
            
            # Validate required fields
            required_fields = [
                'first_name', 'last_name', 'street_address', 'city',
                'state', 'country', 'phone', 'email',
                'driving_experience', 'choice_of_hire',
                'next_of_kin', 'religion_address1', 'religion_address2',
                'religious_leader', 'traditional_ruler'
            ]
            
            for field in required_fields:
                if not form_data.get(field):
                    flash(f'Missing required field: {field}', 'error')
                    return redirect(url_for('dashboard'))
            
            # Handle driver's license upload
            license_file = request.files.get('license_file')
            license_filename = None
            if license_file and license_file.filename != '':
                if not allowed_file(license_file.filename, 'hire_buyer'):
                    flash('Invalid file type for driver license', 'error')
                    return redirect(url_for('dashboard'))
                
                license_filename = save_uploaded_file(license_file, 'hire_buyer', current_user.id, 'driver_license')
            
            # Create application
            new_application = HireBuyerApplication(
                user_id=current_user.id,
                license_filename=license_filename,
                **form_data
            )
            
            db.session.add(new_application)
            db.session.commit()
            send_application_email(current_user)
            
            flash('Your hire buyer application has been submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError as e:
            db.session.rollback()
            flash('Invalid data format. Please check your inputs.', 'error')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Hire buyer application error: {str(e)}')
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('dashboard'))


























# --------------------------------------------------
# MAIN
# --------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        create_tables_and_initial_data()
    app.run(debug=True, host='0.0.0.0', port=5001)
