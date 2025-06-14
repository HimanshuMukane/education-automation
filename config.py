from dotenv import load_dotenv
from os import getenv
import os
load_dotenv()

SECRET_KEY = getenv('SECRET_KEY', "159357258456")
ENV = getenv('ENV', 'development')
DEBUG = getenv('DEBUG') == 'true'

DB_TYPE = getenv('DB_TYPE','mysql')
DB_DRIVER = getenv('DB_DRIVER','pymysql')
DB_USERNAME = getenv('DB_USERNAME','root')
DB_PASSWORD = getenv('DB_PASSWORD','')
DB_HOST = getenv('DB_HOST','localhost')
DB_NAME = getenv('DB_NAME','')

MAIL_SERVER = getenv('MAIL_SERVER', '')
MAIL_PORT = getenv('MAIL_PORT', '')
MAIL_USE_TLS = getenv('MAIL_USE_TLS', '')
MAIL_DEBUG = getenv('MAIL_DEBUG', '')
MAIL_USERNAME = getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = getenv('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = getenv('MAIL_DEFAULT_SENDER', '')

class Config:
    SECRET_KEY = SECRET_KEY
    ENV = ENV
    DEBUG = DEBUG
    SQLALCHEMY_DATABASE_URI = f"{DB_TYPE}+{DB_DRIVER}://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}