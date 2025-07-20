# -*- coding: utf-8 -*-
from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_migrate import Migrate
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
import string
import random
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
from urllib.parse import quote_plus

app = Flask(__name__)

# Configuration
# Secure password encoding
db_password = quote_plus(os.getenv('DB_PASSWORD', 'sample_password'))

# Flask app secret key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')

# Choose database based on environment
#if os.getenv('FLASK_ENV') == 'production':
db_user = os.getenv('DB_USER', 'cpaneluser_damascus_developer')
db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'cpaneluser_damascus_app')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
#else:
#    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'mail.damascusprojects.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'noreply@damascusprojects.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'sample_password')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True  # Important for port 465
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'noreply@damascusprojects.com')

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
    order_number = db.Column(db.String(100), unique=True, nullable=True)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



















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
        
        # HTML email content
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
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        user = User(username=username, first_name=first_name, last_name=last_name, email=email)
        user.set_password(password)
        user.user_code = get_unique_user_code()
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use a different email.', 'danger')
            return redirect(url_for('signup'))

        # Else proceed to create new user
        db.session.add(user)
        db.session.commit()
        send_welcome_email(user, password)
        login_user(user)

        flash('Account created! Now login.', 'success')
        return redirect(url_for('choose_program'))
    return render_template('signup.html')



@app.route('/login/', methods=['GET', 'POST'])
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
