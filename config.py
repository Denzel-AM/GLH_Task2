from flask import Flask
from models import db, User
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

def seed_admin_user():
        """Create a default admin user if none exists."""
        existing_admin = User.query.filter_by(role='admin').first()
        if not existing_admin:
            admin_user = User(
                name='Admin',
                email='admin@glh.co.uk',
                password=generate_password_hash('admin@glh123', method='scrypt'),
                role='admin',
                address='123 Admin St, City, Country',
                dob=date(1990, 1, 1),
                phone='0000000000',
                created_at=datetime.utcnow()
            )
            db.session.add(admin_user)
            db.session.commit()
