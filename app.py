from flask import Flask, render_template, request, redirect, url_for, flash , session
from datetime import datetime, date
import os
import re
import shutil
import json
from datetime import date, datetime
from models import db
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from config import get_config


app = Flask(__name__)
get_config(app)

with app.app_context():
    db.create_all()
    
#--- nav links setup ---
nav_links = [
    {"name": "Home", "url": "/"},
    {"name": "About Us", "url": "/about"},
    {"name": "Privacy", "url": "/privacy"},
    {"name": "Dashboard", "url": "/dashboard"},
    {"name": "Login", "url": "/login"},
    {"name": "Register", "url": "/register"},
    {"name": "Logout", "url": "/logout"},
    ]

home_links = [nav_links[i] for i in ( 1, 2)]  # Home, About Us, Privacy
login_nav_links = [nav_links[i] for i in (0, 1, 5, 2)]
register_links = [nav_links[i] for i in (0, 1, 2, 4)]  # Home, About Us, Privacy, Login
admin_nav_links = nav_links  # All links for admin
dashboard_nav_links = [nav_links[i] for i in (0, 6)]

with app.app_context():
    db.create_all()
    
    
    

#----- home route----
@app.route('/')
def home():
    return render_template('index.html', nav_links=home_links)

@app.route('/about')
def about():
    return render_template('about.html', nav_links=home_links)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', nav_links=home_links)

@app.route('/contact-us')
def contact_us():
    return render_template('contact_us.html', nav_links=home_links)


@app.route('/login')
def login():
    return render_template('auth/login.html', nav_links=home_links)

@app.route('/register')
def register():
    return render_template('auth/register.html', nav_links=home_links)



@app.route('/dashboard')

def dashboard():
    return render_template(
        "dashboard.html",
        nav_links=dashboard_nav_links,
        user = user
    )           

@app.route('/failure')

def failure():
    #get the failure reason from query parameter
    flash('sorry bro you aint got it like that', 'danger')
    return render_template('500.html')



@app.route('/logout')

def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)