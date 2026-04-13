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

producer_bp = Blueprint("producer", __name__, url_prefix="/producer")


# ─────────────────────────────────────────────────────────────────────────────
# ACCESS GUARD
# ─────────────────────────────────────────────────────────────────────────────

def producer_required(fn):
    """
    Decorator — allows only logged-in users whose role is 'customer'.
    Admins and producers are sent to 403; anonymous users to the login page.
    Apply AFTER @login_required so Flask-Login handles the anonymous case first.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.role == "producer":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper



@producer_bp.route("/dashboard")
@login_required
@producer_required
def dashboard():
    """
    Customer home page.
    Pulls the 5 most recent orders, the active in-progress order for the
    tracker, lifetime stats, and the loyalty account summary.
    """
    products = Product.query.filter_by(producer_id=current_user.id).all()

    # Orders that include at least one of this producer's products
    product_ids = [p.id for p in products]
    recent_order_items = (
        OrderItem.query
        .filter(OrderItem.product_id.in_(product_ids))
        .order_by(OrderItem.id.desc())
        .limit(20)
        .all()
    )

    # Collect unique orders
    seen_order_ids = set()
    recent_orders = []
    for item in recent_order_items:
        if item.order_id not in seen_order_ids:
            seen_order_ids.add(item.order_id)
            recent_orders.append(item.order)

    total_revenue = sum(
        oi.item_price * oi.quantity
        for oi in OrderItem.query.filter(OrderItem.product_id.in_(product_ids)).all()
    )
    low_stock = [p for p in products if p.stock_quantity <= 5]

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
    date = day_of_week
    name = current_user.name
    first_name = name.split(" ", 1)[0]
    words = name.strip().split()

    initials = ''.join(word[0] for word in words if word)
    loyalty_points = current_user.loyalty_points
    credit = loyalty_points/100
    return render_template(
        "producers/dashboard.html",
        nav_links = nav_for(current_user),
        user = current_user,
        day = day_of_week,
        month = month_name,
        year = year,
        date = day_of_month,
        first_name = first_name,
        initials = initials,
        credit = loyalty_points,
        total_orders = total_orders,
        products=products,
        recent_orders=recent_orders,
        total_revenue=round(total_revenue, 2),
        low_stock=low_stock,
        current_date= date,
    )