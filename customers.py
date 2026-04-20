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

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


# ─────────────────────────────────────────────────────────────────────────────
# ACCESS GUARD
# ─────────────────────────────────────────────────────────────────────────────

def customer_required(fn):
    """
    Decorator — allows only logged-in users whose role is 'customer'.
    Admins and producers are sent to 403; anonymous users to the login page.
    Apply AFTER @login_required so Flask-Login handles the anonymous case first.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.role == "customer":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper



@customer_bp.route("/dashboard")
@login_required
@customer_required
def dashboard():
    """
    Customer home page.
    Pulls the 5 most recent orders, the active in-progress order for the
    tracker, lifetime stats, and the loyalty account summary.
    """
    # Recent orders for the table
    recent_orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.order_date.desc())
        .limit(5)
        .all()
    )

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
        "customer/dashboard.html",
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



# ─────────────────────────────────────────────────────────────────────────────
# ORDER HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@customer_bp.route("/orders")
@login_required
def orders():
    all_orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.order_date.desc())
        .all()
    )
    return render_template(
        "customer/orders.html",
        orders=all_orders,
        user=current_user,
        nav_links=nav_for(current_user),
    )


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

@customer_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        phone   = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if name and len(name) >= 2:
            current_user.name = name
        if address and len(address) >= 5:
            current_user.address = address
        if phone:
            current_user.phone = phone
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("customer.profile"))

    return render_template(
        "customer/profile.html",
        user=current_user,
        nav_links=nav_for(current_user),
    )


