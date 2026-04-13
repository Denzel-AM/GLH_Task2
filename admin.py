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
    Loyalty, User, Enquiry
)
from auth import nav_for
from auth import is_valid_password



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
    total_users     = User.query.count()
    total_orders    = Order.query.count()
    total_products  = Product.query.count()
    total_enquiries = Enquiry.query.count()

    pending_orders   = Order.query.filter_by(order_status="Pending").count()
    confirmed_orders = Order.query.filter_by(order_status="Confirmed").count()

    recent_orders      = Order.query.order_by(Order.order_date.desc()).limit(10).all()
    low_stock_products = Product.query.filter(Product.stock_quantity <= 5).all()
    recent_enquiries   = Enquiry.query.order_by(Enquiry.submitted_date.desc()).limit(5).all()

    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0.0

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
    '''
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
    )'''
    return render_template(
        "admin/dashboard.html",
        user=current_user,
        day = day_of_week,
        month = month_name,
        year = year,
        first_name = first_name,
        initials = initials,
        date = day_of_month,
        total_users=total_users,
        total_orders=total_orders,
        total_products=total_products,
        total_enquiries=total_enquiries,
        pending_orders=pending_orders,
        confirmed_orders=confirmed_orders,
        recent_orders=recent_orders,
        low_stock_products=low_stock_products,
        recent_enquiries=recent_enquiries,
        total_revenue=round(total_revenue, 2),
        nav_links=nav_for(current_user),
        current_date=datetime.now(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MANAGE ACCOUNTS  (view + create producer)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/manage-accounts")
@admin_required
def manage_accounts():
    role_filter = request.args.get("role", "")
    query = User.query
    if role_filter in ("customer", "producer", "admin"):
        query = query.filter_by(role=role_filter)
    users = query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin/manage_accounts.html",
        users=users,
        role_filter=role_filter,
        user=current_user,
        nav_links=nav_for(current_user),
    )


#__________________________________________________________________________
#creating a producer account
#__________________________________________________________________________

@admin_bp.route("/create-producer", methods=["POST"])
@admin_required
def create_producer():
    """Create a new producer account from the admin panel."""
    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip().lower()
    phone    = request.form.get("phone", "").strip()
    address  = request.form.get("address", "").strip()
    password = request.form.get("password", "")

    #validating inputs
    if not name or not email or not address or not password:
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for("admin.manage_accounts"))

    if User.query.filter_by(email=email).first():
        flash(f"An account with email {email} already exists.", "danger")
        return redirect(url_for("admin.manage_accounts"))

    if not is_valid_password(password):
        flash(
            "Password must be at least 8 characters with uppercase, lowercase, "
            "a number, and a special character.",
            "danger",
        )
        return redirect(url_for("admin.manage_accounts"))

    producer = User(
        name    = name,
        email   = email,
        phone   = phone ,
        address = address,
        role    = "producer",
    )
    producer.set_password(password)
    db.session.add(producer)
    db.session.commit()
    flash(f"Producer account created for {name} ({email}).", "success")
    return redirect(url_for("admin.manage_accounts", role="producer"))


@admin_bp.route("/manage-accounts/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_active(user_id):
    target = db.session.get(User, user_id)
    if not target:
        flash("User not found.", "danger")
    elif target.id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
    else:
        target.is_active = not target.is_active
        db.session.commit()
        status = "activated" if target.is_active else "deactivated"
        flash(f"Account for {target.name} has been {status}.", "success")
    return redirect(url_for("admin.manage_accounts"))


@admin_bp.route("/manage-accounts/<int:user_id>/change-role", methods=["POST"])
@admin_required
def change_role(user_id):
    target   = db.session.get(User, user_id)
    new_role = request.form.get("role", "")

    if not target:
        flash("User not found.", "danger")
    elif target.id == current_user.id:
        flash("You cannot change your own role.", "warning")
    elif new_role not in ("customer", "producer", "admin"):
        flash("Invalid role.", "danger")
    else:
        target.role = new_role
        db.session.commit()
        flash(f"{target.name} is now a {new_role}.", "success")
    return redirect(url_for("admin.manage_accounts"))
