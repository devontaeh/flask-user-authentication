import os
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, url_for, jsonify
from flask_login import UserMixin, login_user,LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Email
from flask_bcrypt import Bcrypt
from pymongo.mongo_client import MongoClient
import certifi
from bson import ObjectId

# Load environment variales for secret keys and database URI
load_dotenv()
secret_key = os.getenv('SECRET_KEY')
mongo_uri = os.getenv('MONGO_URI')


# basedir = os.path.abspath(os.path.dirname(__file__))

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key # set secret key for CSRF protection

# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)

# set up MongoDB connection
client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client['loginApp']
users = db.users

# Attempt to ping MongoDB to check for successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfuclly connected to MongoDB!")
except Exception as e:
    print(e)

# Initialize Flask-Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader callback for Flask-Login to load user from session
@login_manager.user_loader
def load_user(user_id):
    user_data = users.find_one({'_id':ObjectId(user_id)})
    if user_data:
        return User(
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            email=user_data['email'],
            username=user_data['username'],
            password=user_data['password'],
            _id=user_data['_id']
        )
    return None

# User model for Flask-Login 
class User:
    def __init__(self,  first_name, last_name, email,username, password, _id=None):
        self._id = _id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.username = username
        self.password = password
  
    # Save user to MongoDB
    def save(self):
        user_data = {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'username': self.username,
            'password': self.password
            
        }
        users.insert_one(user_data)
     
    # Required methods for Flask-Login user model
    @staticmethod
    def validate_login(password_hash, password):
        return bcrypt.check_password_hash(password_hash, password)
    @property
    def is_authenticated(self):
        # return True if the user is authenticated, i.e., they have provided valid credentials
        return True

    @property
    def is_active(self):
        # return True if this is an active user 
        # can add logi ie acc confirmation/suspension/subscription
        return True

    @property
    def is_anonymous(self):
        # return True if this is an anonymous user
        return False

    def get_id(self):
        # convert ObjectID to a string
        return str(self._id)

# Registration form with WTForms validators
class RegisterForm(FlaskForm):
    first_name = StringField(validators=[InputRequired()], render_kw={"placeholder": "First Name"})
    last_name = StringField(validators=[InputRequired()], render_kw={"placeholder": "Last Name"})
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    
    # Custom validators to ensure unqiue usernames and emails
    def validate_username(self, username):
        existing_user_username = users.find_one(
            {'username':username.data})
        if existing_user_username:
            raise ValidationError(
                'This username already exists. Please choose a different one.')
            
    def validate_email(self, email):
        existing_user_email = users.find_one(
            {'email':email.data})
        if existing_user_email:
            raise ValidationError(
                'This email is already in use. Please choose a different one.')

# LoginForm with validators for user login
class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')
    
   


# Routes for Flask application
# Home
@app.route('/')
def home():
    return render_template('home.html')

# Login page
@app.route('/login', methods = ['GET', 'POST'])
def login():
    
    form = LoginForm()
    if form.validate_on_submit():
        
        user_data =   users.find_one({'username':form.username.data})
        if user_data and bcrypt.check_password_hash(user_data['password'], form.password.data):
            
            user_obj = User(
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                email=user_data['email'],
                username=user_data['username'],
                password=user_data['password'],
                _id=user_data['_id']
            )
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
        
            flash('Invalid username or password', 'error')
    return render_template('login.html', form = form)

# User dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required 
def dashboard():
    
    return render_template('dashboard.html')

# Logout -> redirects to login page
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
    

# Registration page
@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm()
    
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            username=form.username.data,
            password=hashed_password
            )
        new_user.save()
        return redirect(url_for('login'))
    else:
        if form.errors:
            print("Form errors:")
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"Error in the {field} field - {error}")
    return render_template('register.html', form = form)
    

if __name__ == '__main__':
    # for deployment
    # to make it work for both production and development
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)