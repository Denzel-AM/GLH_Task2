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
    Loyalty, User, Enquiry, StockMovement
)
from auth import nav_for
from auth import is_valid_password
from io import BytesIO
import imghdr
from utils import save_product_image



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

def dashboard():
    if current_user.role != "admin":
        flash("You do not have access to this page")
        return redirect(url_for('auth.login'))
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
@login_required

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

@login_required
def create_producer():
    """Create a new producer account from the admin panel."""
    if current_user.role != "admin":
        flash("You do not have access to this page")
        return redirect(url_for('auth.login'))
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
@login_required
def toggle_active(user_id):
    if current_user.role != "admin":
        flash("You do not have access to this page")
        return redirect(url_for('auth.login'))
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
@login_required
def change_role(user_id):
    if current_user.role != "admin":
        flash("You do not have access to this page")
        return redirect(url_for('auth.login'))

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



# ─────────────────────────────────────────────────────────────────────────────
# MANAGE PRODUCTS  (add / edit / stock / delete — across all producers)
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/manage-products", methods=["GET", "POST"])
@admin_required
def manage_products():
    categories = Category.query.all()
    producers  = User.query.filter_by(role="producer").order_by(User.name).all()

    if request.method == "POST":
        action = request.form.get("action")

        # ── Add new product ────────────────────────────────────────────────
        if action == "add_product":
            name        = request.form.get("product_name", "").strip()
            description = request.form.get("description", "").strip()
            category_id = request.form.get("category_id", type=int)
            producer_id = request.form.get("producer_id", type=int) or None
            price_str   = request.form.get("price", "")
            stock_str   = request.form.get("stock_quantity", "")

            try:
                price = float(price_str)
                stock = int(stock_str)
            except ValueError:
                flash("Please enter valid price and stock values.", "danger")
                return redirect(url_for("admin.manage_products"))

            if not name or price <= 0 or stock < 0 or not category_id:
                flash("Please fill in all required product fields.", "danger")
            else:
                image_url = save_product_image(request.files.get("product_image"))
                if request.files.get("product_image") and request.files["product_image"].filename and not image_url:
                    flash("Invalid image type. Allowed: jpg, jpeg, png, gif, webp.", "danger")
                    return redirect(url_for("admin.manage_products"))

                product = Product(
                    product_name  = name,
                    description   = description,
                    price         = round(price, 2),
                    stock_quantity= stock,
                    category_id   = category_id,
                    producer_id   = producer_id,
                    image_url     = image_url,
                )
                product.update_availability()
                db.session.add(product)
                if stock > 0:
                    db.session.flush()
                    db.session.add(StockMovement(
                        product_id    = product.id,
                        change_amount = stock,
                        movement_type = "restock",
                        note          = "Initial stock — added by admin",
                    ))
                db.session.commit()
                flash(f"Product '{name}' added.", "success")

        # ── Update stock ───────────────────────────────────────────────────
        elif action == "update_stock":
            product_id = request.form.get("product_id", type=int)
            new_qty    = request.form.get("quantity", type=int)
            note       = request.form.get("note", "").strip()

            product = db.session.get(Product, product_id)
            if not product:
                flash("Product not found.", "danger")
            elif new_qty is None or new_qty < 0:
                flash("Invalid stock quantity.", "danger")
            else:
                change = new_qty - product.stock_quantity
                product.stock_quantity = new_qty
                product.update_availability()
                db.session.add(StockMovement(
                    product_id    = product.id,
                    change_amount = change,
                    movement_type = "manual_adjustment",
                    note          = note or "Admin stock update",
                ))
                db.session.commit()
                flash(f"Stock updated for '{product.product_name}'.", "success")

        # ── Update product details ─────────────────────────────────────────
        elif action == "update_product":
            product_id  = request.form.get("product_id", type=int)
            name        = request.form.get("product_name", "").strip()
            description = request.form.get("description", "").strip()
            price_str   = request.form.get("price", "")
            category_id = request.form.get("category_id", type=int)
            producer_id = request.form.get("producer_id", type=int) or None

            product = db.session.get(Product, product_id)
            if not product:
                flash("Product not found.", "danger")
            else:
                try:
                    price = float(price_str)
                except ValueError:
                    flash("Invalid price value.", "danger")
                    return redirect(url_for("admin.manage_products"))
                new_image = save_product_image(request.files.get("product_image"))
                if request.files.get("product_image") and request.files["product_image"].filename and not new_image:
                    flash("Invalid image type. Allowed: jpg, jpeg, png, gif, webp.", "danger")
                    return redirect(url_for("admin.manage_products"))

                product.product_name = name or product.product_name
                product.description  = description
                product.price        = round(price, 2)
                if category_id:
                    product.category_id = category_id
                product.producer_id = producer_id
                if new_image:
                    product.image_url = new_image
                db.session.commit()
                flash(f"Product '{product.product_name}' updated.", "success")

        # ── Delete product ─────────────────────────────────────────────────
        elif action == "delete_product":
            product_id = request.form.get("product_id", type=int)
            product = db.session.get(Product, product_id)
            if product:
                db.session.delete(product)
                db.session.commit()
                flash("Product deleted.", "success")
            else:
                flash("Product not found.", "danger")

        return redirect(url_for("admin.manage_products"))

    products = Product.query.order_by(Product.product_name).all()
    return render_template(
        "admin/manage_products.html",
        products=products,
        categories=categories,
        producers=producers,
        user=current_user,
        nav_links=nav_for(current_user),
    )



# MANAGE ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@admin_bp.route("/orders")
@admin_required
def orders():
    status_filter = request.args.get("status", "")
    query = Order.query
    if status_filter:
        query = query.filter_by(order_status=status_filter)
    all_orders = query.order_by(Order.order_date.desc()).all()

    return render_template(
        "admin/orders.html",
        orders=all_orders,
        status_filter=status_filter,
        user=current_user,
        nav_links=nav_for(current_user),
    )


@admin_bp.route("/orders/<int:order_id>/update-status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order      = db.session.get(Order, order_id)
    new_status = request.form.get("status", "")
    valid_statuses = ("Pending", "Confirmed", "Processing", "Out for Delivery", "Delivered", "Cancelled")

    if not order:
        flash("Order not found.", "danger")
    elif new_status not in valid_statuses:
        flash("Invalid status.", "danger")
    else:
        order.order_status = new_status
        db.session.commit()
        flash(f"Order #GLH-{order.id:04d} updated to '{new_status}'.", "success")

    return redirect(url_for("admin.orders"))