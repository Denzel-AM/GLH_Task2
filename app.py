from flask import Flask, render_template, request, redirect, url_for, flash , session
from datetime import datetime, date
import os
import re
import shutil
import json
from datetime import date, datetime
from models import db, User , Category, Loyalty, Product
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
import stripe





# ─────────────────────────────────────────────────────────────────────────────
# SEED ROUTE — visit /seed in the browser to populate demo data
# ─────────────────────────────────────────────────────────────────────────────

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
def _get_or_create_user(email, **kwargs):
    """Return existing user by email, or create and return a new one."""
    user = User.query.filter_by(email=email).first()
    if user:
        return user, False
    password = kwargs.pop("password")
    user = User(email=email, **kwargs)
    user.set_password(password)
    db.session.add(user)
    return user, True
# sedding producers and products 
def seed_data():
    """Populate the database with demo categories, products and users.
    Safe to call multiple times — skips existing records."""

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

    cat_map = {c.category_name: c.id for c in Category.query.all()}

    # --- Users (skip any that already exist) ---
    admin_user, _ = _get_or_create_user(
        "admin@glh.co.uk", password="Admin@1234!",
        name="Admin GLH", phone="01234000001",
        address="132 Dartmouth Street, Bletchley", role="admin",
    )
    db.session.flush()

    producer1, _ = _get_or_create_user(
        "tom@greenacre.farm", password="Farmer@1234!",
        name="Tom Hargreaves", phone="01234000002",
        address="Green Acre Farm, Buckinghamshire", role="producer",
    )
    db.session.flush()

    producer2, _ = _get_or_create_user(
        "sarah@bloomfield.co.uk", password="Farmer@1234!",
        name="Sarah Bloom", phone="01234000003",
        address="Bloomfield Dairy, Northamptonshire", role="producer",
    )
    db.session.flush()

    demo_customer, created = _get_or_create_user(
        "customer@glh.co.uk", password="Customer@1234!",
        name="Alex Johnson", phone="07700900001",
        address="10 Mill Lane, Milton Keynes, MK1 1AA",
        role="customer", loyalty_points=250,
    )
    db.session.flush()

    if created and not demo_customer.loyalty_account:
        db.session.add(Loyalty(user_id=demo_customer.id, points=250))

    # --- Products (skip if already present) ---
    if not Product.query.first():
        products = [
            # Vegetables
            Product(product_name="Heritage Tomatoes",
                    description="Sweet, vine-ripened heirloom tomatoes picked at peak season.",
                    price=2.50, stock_quantity=80, category_id=cat_map["Vegetables"],
                    image_url="/static/images/hayley-ryczek-pNcFMdEe09Q-unsplash.jpg",
                    producer_id=producer1.id),
            Product(product_name="Mixed Salad Leaves",
                    description="A fresh blend of seasonal salad leaves, ready to eat.",
                    price=1.80, stock_quantity=60, category_id=cat_map["Vegetables"],
                    image_url="/static/images/cindie-hansen-ak2UGvCPDk8-unsplash.jpg",
                    producer_id=producer1.id),
            Product(product_name="Tenderstem Broccoli",
                    description="Crisp tenderstem broccoli, harvested daily.",
                    price=1.99, stock_quantity=45, category_id=cat_map["Vegetables"],
                    image_url="/static/images/fernando-andrade-nAOZCYcLND8-unsplash.jpg",
                    producer_id=producer1.id),
            # Fruit
            Product(product_name="Seasonal Apple Box (5kg)",
                    description="A selection of locally grown apples — crisp and naturally sweet.",
                    price=6.50, stock_quantity=40, category_id=cat_map["Fruit"],
                    image_url="/static/images/gemma-c-stpjHJGqZyw-unsplash.jpg",
                    producer_id=producer1.id),
            Product(product_name="Mixed Berry Punnet",
                    description="Strawberries, raspberries and blueberries from local polytunnels.",
                    price=3.20, stock_quantity=30, category_id=cat_map["Fruit"],
                    image_url="/static/images/allec-gomes-xnRg3xDcNnE-unsplash.jpg",
                    producer_id=producer1.id),
            # Dairy
            Product(product_name="Whole Milk (2L)",
                    description="Unhomogenised whole milk from grass-fed cows.",
                    price=1.60, stock_quantity=100, category_id=cat_map["Dairy"],
                    image_url="/static/images/andrew-molyneaux-o_qvA6R7hgs-unsplash.jpg",
                    producer_id=producer2.id),
            Product(product_name="Mature Cheddar (250g)",
                    description="Aged for 12 months — sharp, crumbly and full of flavour.",
                    price=3.50, stock_quantity=55, category_id=cat_map["Dairy"],
                    image_url="/static/images/andrey-haimin-qtwlKiu6VHg-unsplash.jpg",
                    producer_id=producer2.id),
            # Bakery
            Product(product_name="Sourdough Loaf",
                    description="Long-fermented sourdough with a crisp crust and open crumb.",
                    price=4.00, stock_quantity=20, category_id=cat_map["Bakery"],
                    image_url="/static/images/karyna-panchenko-T4QUfXJNwZc-unsplash.jpg",
                    producer_id=producer2.id),
            # Honey & Preserves
            Product(product_name="Wildflower Honey (340g)",
                    description="Raw, unfiltered honey from local hives — full of natural goodness.",
                    price=5.50, stock_quantity=35, category_id=cat_map["Honey & Preserves"],
                    image_url="/static/images/kg-baek-aeE-Y7SVVR4-unsplash.jpg",
                    producer_id=producer1.id),
            Product(product_name="Damson Jam (200g)",
                    description="Traditional recipe using hand-picked damsons. No artificial additives.",
                    price=2.80, stock_quantity=50, category_id=cat_map["Honey & Preserves"],
                    image_url="/static/images/giorgio-trovato-fczCr7MdE7U-unsplash.jpg",
                    producer_id=producer1.id),
            # Meat & Eggs
            Product(product_name="Free-Range Eggs (12)",
                    description="A dozen large eggs from hens raised on pasture.",
                    price=3.20, stock_quantity=70, category_id=cat_map["Meat & Eggs"],
                    image_url="/static/images/kyle-mackie-MEnlQv-EQvY-unsplash.jpg",
                    producer_id=producer2.id),
            Product(product_name="Pork Sausages (6 pack)",
                    description="Traditional pork sausages, 85% pork with natural casings.",
                    price=4.50, stock_quantity=25, category_id=cat_map["Meat & Eggs"],
                    image_url="/static/images/sergey-kotenev-j-17JLHMIpk-unsplash.jpg",
                    producer_id=producer2.id),
        ]
        for p in products:
            p.update_availability()
            db.session.add(p)

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
    seed_data()
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