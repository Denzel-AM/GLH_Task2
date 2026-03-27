from functools import wraps
from datetime import datetime
from datetime import date
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, abort, jsonify,
)
from flask_login import login_required, current_user
from models import (
    db,
    Order, OrderItem,
    Product, Category,
    Loyalty, 
)
from auth import nav_for




# ─────────────────────────────────────────────────────────────────────────────
# BLUEPRINT
# ─────────────────────────────────────────────────────────────────────────────

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ─────────────────────────────────────────────────────────────────────────────
# ACCESS GUARD
# ─────────────────────────────────────────────────────────────────────────────

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.role == "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper



@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    
    

    #all order
    total_orders = Order.query.filter_by(user_id=current_user.id).count()

    # Get today's date
    today = datetime.today()

    # Format date as dd/mm/yyyy
    formatted_date = today.strftime("%d/%m/%Y")

    # Extract parts
    day_of_week = today.strftime("%A")   # Full weekday name (e.g., Monday)
    day_of_month = today.day             # Numeric day of the month
    month_name = today.strftime("%B")    # Full month name (e.g., March)
    year = today.year
    
    #get user name
    name = current_user.name
    first_name = name.split(" ", 1)[0]
    words = name.strip().split()

    initials = ''.join(word[0] for word in words if word)
    loyalty_points = current_user.loyalty_points
    credit = loyalty_points/100
    return render_template(
        "admin/dashboard.html",
        nav_links        = nav_for(current_user),
        user = current_user,
        day = day_of_week,
        month = month_name,
        year = year,
        date = day_of_month,
        first_name = first_name,
        initials = initials,
        credit = loyalty_points,
        total_orders = total_orders
    )