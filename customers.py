import re
from datetime import datetime, date

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, abort,
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user,
)
from flask_login import UserMixin

from models import db, User, Loyalty


# BLUEPRINT & LOGIN MANAGER

customer_bp    = Blueprint("auth", __name__)
login_manager = LoginManager()

@customer_bp.route('dashboard')
@login_required
def dashboard():
    if current_user.role != "customer"
        flash('Access denied, Account not authorised', danger)
        redirect url_for('auth.login')
    return render_template('customer/dashboard.hmtl')