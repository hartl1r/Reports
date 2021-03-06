# config.py # AzureMonitorScheduling

import os
#import pyodbc
import urllib.parse

from dotenv import load_dotenv

# LOAD dotenv IN THE BASE DIRECTORY
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

params = urllib.parse.quote_plus('DRIVER=' +  os.getenv('Driver') + ';'
                                    'SERVER=' + os.getenv('Server') + ';'
                                    'DATABASE=' + os.getenv('Database') + ';'
                                    'UID=' + os.getenv('Username') + ';'
                                    'PWD=' + os.getenv('Password') + ';'
)
conn_str = 'mssql+pyodbc:///?odbc_connect={}'.format(params)

class Config(object):
    SECRET_KEY = os.environ.get('Secret_key') or 'juniorbr549wells'
    SQLALCHEMY_DATABASE_URI = conn_str 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMPLATES_AUTO_RELOAD=True 
        
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_ASCII_ATTACHMENTS = False
    PDF_API = os.getenv('pdf_api')