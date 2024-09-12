from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
import os

app = Flask(__name__)
#load_dotenv('.env.development.local')
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
# Local PostgreSQL connection (hardcoded for testing)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://default:Boiyph53JmOC@ep-winter-bonus-a45f5ljj-pooler.us-east-1.aws.neon.tech:5432/verceldb?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # to suppress warnings

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from examzen import routes