from flask import Flask
from models import db
import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    SECRET_KEY = 'GLH_Task_2_Secret_Key'
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///glh.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

def get_config(app: Flask):
    app.secret_key = 'GLH_Task_2_Secret_Key'
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///glh.db"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
