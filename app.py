from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
import string
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

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
    town = db.Column(db.String(150), nullable=True)
    country = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    profile_picture = db.Column(db.String(200), nullable=True)

    def get_profile_picture_url(self):
        if self.profile_picture:
            return url_for('static', filename=f'uploads/{self.profile_picture}')
        return url_for('static', filename='images/profile.png')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    status = db.Column(db.String(100), default='pending', nullable=False)

# --------------------------------------------------
# INIT DATA
# --------------------------------------------------
def create_tables_and_initial_data():
    db.create_all()
    create_initial_programs()

def create_initial_programs():
    programs = [
        {'name': 'Project Management', 'slug': 'project_management', 'price': 50000, 'icon': 'fas fa-tasks'},
        {'name': 'Investor', 'slug': 'investor', 'price': 499999, 'icon': 'fas fa-chart-line'},
        {'name': 'Innovator or Idea Owner', 'slug': 'innovator', 'price': 21500, 'icon': 'fas fa-lightbulb'},
        {'name': 'Visa Sponsorship', 'slug': 'visa', 'price': 37500, 'icon': 'fas fa-passport'},
        {'name': 'Priority Housing', 'slug': 'housing', 'price': 50000, 'icon': 'fas fa-home'},
        {'name': 'Hire Purchase (Buyer)', 'slug': 'hireb', 'price': 21000, 'icon': 'fas fa-truck-pickup'},
        {'name': 'Hire Purchase (Seller)', 'slug': 'hires', 'price': 21000, 'icon': 'fas fa-truck-pickup'}
    ]
    for prog in programs:
        if not Program.query.filter_by(slug=prog['slug']).first():
            db.session.add(Program(**prog))
    db.session.commit()

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
# ROUTES
# --------------------------------------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route("/applications/<slug>")
def apply_program(slug):
    # Mapping slug to template
    templates = {
        "project_management": "applications/pm.html",
        "visa": "applications/visa.html",
        "investor": "applications/investor.html",
        "innovator": "applications/innovator.html",
        "housing": "applications/housing.html",
        "hireb": "applications/hire-buyer.html",
        "hires": "applications/hire-seller.html"
    }

    if slug in templates:
        return render_template(templates[slug])
    else:
        flash("Invalid program selected.", "warning")
        return redirect(url_for("dashboard"))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        user = User(username=username, first_name=first_name, last_name=last_name, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        login_user(user)

        flash('Account created! Now login.', 'success')
        return redirect(url_for('choose_program'))
    return render_template('signup.html')

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
    db.session.commit()
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
    if request.method == 'POST':
        file = request.files['receipt']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            subscription.payment_receipt = filename
            db.session.commit()
            flash('Receipt uploaded successfully.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('upload_receipt.html', subscription=subscription)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('choose_program'))
        flash('Invalid credentials', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')

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


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/health')
def health():
    return "OK", 200

with app.app_context():
    # Create tables and initial data
    create_tables_and_initial_data()
# --------------------------------------------------
# MAIN
# --------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        create_tables_and_initial_data()
    app.run(debug=True, host='0.0.0.0', port=5001)
