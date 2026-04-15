from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Order, OrderItem
from datetime import datetime
from auth import nav_for

customer_bp = Blueprint("customer", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@customer_bp.route("/dashboard")
@login_required
def dashboard():
    # Recent orders
    recent_orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.order_date.desc())
        .limit(5)
        .all()
    )

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

    return render_template(
        "customer/dashboard.html",
        user=current_user,
        recent_orders=recent_orders,
        total_orders=total_orders,
        total_spent=round(total_spent, 2),
        producers_supported=producers_supported,
        active_order=active_order,
        loyalty_credit=loyalty_credit,
        current_date=datetime.now(),
        nav_links=nav_for(current_user),
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