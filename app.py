from flask import Flask, render_template, request, redirect, url_for, flash , session
from datetime import datetime, date
import os
import re
import shutil
import json
from datetime import date, datetime
from models import db, User , Category
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from config import get_config
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user,
)
from customers import customer_bp
from auth import auth_bp
from admin import admin_bp
from producers import producer_bp
from flask_migrate import Migrate
from shop import shop_bp






# import your auth blueprint
from auth import auth_bp, login_manager

app = Flask(__name__)
get_config(app)

def seed_admin_user():
        """Create a default admin user if none exists."""
        existing_admin = User.query.filter_by(role='admin').first()
        if not existing_admin:
            admin_user = User(
                name='Admin',
                email='admin@glh.co.uk',
                password_hash=generate_password_hash('admin@glh123', method='scrypt'),
                role='admin',
                address='123 Admin St, City, Country',
                #dob=date(1990, 1, 1),
                phone='0000000000',
                created_at=datetime.utcnow()
            )
            db.session.add(admin_user)
            db.session.commit()
            
#seeding the cartegories into the database
def seed_cartegories():
    # --- Categories (skip if already present) ---
    if not Category.query.first():
        categories = [
            Category(category_name="Vegetables"),
            Category(category_name="Fruit"),
            Category(category_name="Dairy"),
            Category(category_name="Bakery"),
            Category(category_name="Honey & Preserves"),
            Category(category_name="Meat & Eggs"),
        ]
        for cat in categories:
            db.session.add(cat)
        db.session.flush()
        db.session.commit()

# --- register blueprint ---
app.register_blueprint(auth_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(producer_bp)
app.register_blueprint(shop_bp)
# --- setup login manager ---
login_manager.init_app(app)
login_manager.login_view = "auth.login"

with app.app_context():
    db.create_all()
    seed_admin_user()
    seed_cartegories()
    migrate = Migrate(app, db)
#--- nav links setup ---
nav_links = [
    {"name": "Home", "url": "/"},
    {"name": "About Us", "url": "/about"},
    {"name": "Privacy", "url": "/privacy"},
    {"name": "Dashboard", "url": "/dashboard"},
    {"name": "Login", "url": "/login"},
    {"name": "Producers", "url": "/producers"},
    {"name": "Shop", "url": "/shop"},
    {"name": "Contact", "url": "contact-us"},
    {"name": "Register", "url": "/register"},
    {"name": "Logout", "url": "/logout"},
    ]

home_links = [nav_links[i] for i in ( 0,1, 2,3,4)]  # Home, About Us, Privacy
login_nav_links = [nav_links[i] for i in (0, 1, 5, 2,5)]
register_links = [nav_links[i] for i in (0, 1, 2, 5,6 , 7)]  # Home, About Us, Privacy, Login
admin_nav_links = nav_links  # All links for admin
dashboard_nav_links = [nav_links[i] for i in (0, 6)]

with app.app_context():
    db.create_all()
    
    
    

#----- home route----
@app.route('/')
def home():
    return render_template('index.html', nav_links=register_links)

@app.route('/about')
def about():
    return render_template('about.html', nav_links=register_links)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', nav_links=register_links)

@app.route('/contact-us', methods=["GET", "POST"])
def contact_us():
    from auth import NAV, nav_for
    from models import Enquiry
    nav = nav_for(current_user) if current_user.is_authenticated else NAV["public"]

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name  = request.form.get("last_name", "").strip()
        email      = request.form.get("email", "").strip()
        subject    = request.form.get("subject", "General Inquiry")
        message    = request.form.get("message", "").strip()

        if not first_name or not email or not message:
            flash("Please fill in all required fields.", "danger")
            return render_template("contact_us.html", nav_links=nav)

        enquiry = Enquiry(
            name    = f"{first_name} {last_name}".strip(),
            email   = email,
            subject = subject,
            message = message,
            user_id = current_user.id if current_user.is_authenticated else None,
        )
        db.session.add(enquiry)
        db.session.commit()
        flash("Thank you for your message! We'll be in touch soon.", "success")
        return redirect(url_for("contact_us"))

    return render_template('contact_us.html', nav_links=nav)


# ─────────────────────────────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 50

@app.route('/login')
def login():
    return render_template('auth/login.html', nav_links=register_links)

@app.route('/register')
def register():
    return render_template('auth/register.html', nav_links=register_links)

@app.route('/shop')
def shop():
    return render_template('shop.html', nav_links=shop_links)

         

@app.route('/failure')

def failure():
    #get the failure reason from query parameter
    flash('sorry bro you aint got it like that', 'danger')
    return render_template('500.html')

@app.route('/producers')
def producers():
    return render_template('producers.html', nav_links=register_links)


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))




if __name__ == "__main__":
    app.run(debug=True)