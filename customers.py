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
    
    # the total orders
    total_orders = Order.query.filter_by(user_id=current_user.id).count()

    total_spent = db.session.query(
        db.func.sum(Order.total_amount)
    ).filter_by(user_id=current_user.id).scalar() or 0.0

    # Count unique producers supported (via order items)
    from models import Product
    all_order_ids = [o.id for o in Order.query.filter_by(user_id=current_user.id).all()]
    producers_supported = 0
    if all_order_ids:
        producers_supported = db.session.query(
            db.func.count(db.func.distinct(Product.producer_id))
        ).join(OrderItem, OrderItem.product_id == Product.id
        ).filter(OrderItem.order_id.in_(all_order_ids)).scalar() or 0

    # Most recent in-flight order for tracker
    active_order = (
        Order.query
        .filter_by(user_id=current_user.id)
        .filter(Order.order_status.notin_(["Delivered", "Cancelled"]))
        .order_by(Order.order_date.desc())
        .first()
    )

    # Loyalty credit value (100 points = £1)
    loyalty_credit = round(current_user.loyalty_points / 100, 2)

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
    

    return render_template(
        "customer/dashboard.html",
        user = current_user,
        day = day_of_week,
        month = month_name,
        year = year,
        date = day_of_month,
        first_name = first_name,
        initials = initials,
        credit = loyalty_points,
        recent_orders=recent_orders,
        total_orders=total_orders,
        total_spent=round(total_spent, 2),
        producers_supported=producers_supported,
        active_order=active_order,
        loyalty_credit=loyalty_credit,
        current_date=datetime.now(),
        nav_links=nav_for(current_user)
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


