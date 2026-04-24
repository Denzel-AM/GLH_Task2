from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Product, Category, Order, OrderItem, StockMovement
from datetime import datetime
from auth import NAV, nav_for
from utils import save_product_image

producer_bp = Blueprint("producer", __name__, url_prefix="/producer")


def producer_required(f):
    """Decorator: restrict route to users with role == 'producer'."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "producer":
            flash("Access restricted to producers.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


# PRODUCER DASHBOARD

@producer_bp.route("/dashboard")
@producer_required
def dashboard():
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

    return render_template(
        "producers/dashboard.html",
        user=current_user,
        products=products,
        recent_orders=recent_orders,
        total_revenue=round(total_revenue, 2),
        low_stock=low_stock,
        nav_links=nav_for(current_user),
        current_date=datetime.now(),
    )


# MANAGE STOCK

@producer_bp.route("/manage-stock", methods=["GET", "POST"])
@producer_required
def manage_stock():
    products = Product.query.filter_by(producer_id=current_user.id).all()
    categories = Category.query.all()

    if request.method == "POST":
        action = request.form.get("action")

        # ── Update stock quantity ──────────────────────────────────────────
        if action == "update_stock":
            product_id = request.form.get("product_id", type=int)
            new_qty    = request.form.get("quantity", type=int)
            note       = request.form.get("note", "").strip()

            product = Product.query.filter_by(id=product_id, producer_id=current_user.id).first()
            if not product:
                flash("Product not found.", "danger")
            elif new_qty is None or new_qty < 0:
                flash("Please enter a valid stock quantity.", "danger")
            else:
                change = new_qty - product.stock_quantity
                product.stock_quantity = new_qty
                product.update_availability()

                movement = StockMovement(
                    product_id    = product.id,
                    change_amount = change,
                    movement_type = "manual_adjustment",
                    note          = note or "Manual stock update",
                )
                db.session.add(movement)
                db.session.commit()
                flash(f"Stock updated for {product.product_name}.", "success")

        # ── Add new product ────────────────────────────────────────────────
        elif action == "add_product":
            name        = request.form.get("product_name", "").strip()
            description = request.form.get("description", "").strip()
            price_str   = request.form.get("price", "")
            stock_str   = request.form.get("stock_quantity", "")
            category_id = request.form.get("category_id", type=int)

            try:
                price = float(price_str)
                stock = int(stock_str)
            except ValueError:
                flash("Please enter valid price and stock values.", "danger")
                return redirect(url_for("producer.manage_stock"))

            if not name or price <= 0 or stock < 0 or not category_id:
                flash("Please fill in all product fields correctly.", "danger")
            else:
                image_url = save_product_image(request.files.get("product_image"))
                if request.files.get("product_image") and request.files["product_image"].filename and not image_url:
                    flash("Invalid image type. Allowed: jpg, jpeg, png, gif, webp.", "danger")
                    return redirect(url_for("producer.manage_stock"))

                new_product = Product(
                    product_name  = name,
                    description   = description,
                    price         = round(price, 2),
                    stock_quantity= stock,
                    category_id   = category_id,
                    producer_id   = current_user.id,
                    image_url     = image_url,
                )
                new_product.update_availability()
                db.session.add(new_product)

                if stock > 0:
                    db.session.flush()
                    movement = StockMovement(
                        product_id    = new_product.id,
                        change_amount = stock,
                        movement_type = "restock",
                        note          = "Initial stock on product creation",
                    )
                    db.session.add(movement)

                db.session.commit()
                flash(f"Product '{name}' added successfully.", "success")

        # ── Update product details ─────────────────────────────────────────
        elif action == "update_product":
            product_id  = request.form.get("product_id", type=int)
            name        = request.form.get("product_name", "").strip()
            description = request.form.get("description", "").strip()
            price_str   = request.form.get("price", "")
            category_id = request.form.get("category_id", type=int)

            product = Product.query.filter_by(id=product_id, producer_id=current_user.id).first()
            if not product:
                flash("Product not found.", "danger")
            else:
                try:
                    price = float(price_str)
                except ValueError:
                    flash("Invalid price value.", "danger")
                    return redirect(url_for("producer.manage_stock"))

                new_image = save_product_image(request.files.get("product_image"))
                if request.files.get("product_image") and request.files["product_image"].filename and not new_image:
                    flash("Invalid image type. Allowed: jpg, jpeg, png, gif, webp.", "danger")
                    return redirect(url_for("producer.manage_stock"))

                product.product_name = name or product.product_name
                product.description  = description
                product.price        = round(price, 2)
                if category_id:
                    product.category_id = category_id
                if new_image:
                    product.image_url = new_image
                db.session.commit()
                flash(f"Product '{product.product_name}' updated.", "success")

        # ── Delete product ─────────────────────────────────────────────────
        elif action == "delete_product":
            product_id = request.form.get("product_id", type=int)
            product = Product.query.filter_by(id=product_id, producer_id=current_user.id).first()
            if product:
                db.session.delete(product)
                db.session.commit()
                flash("Product removed.", "success")
            else:
                flash("Product not found.", "danger")

        return redirect(url_for("producer.manage_stock"))

    return render_template(
        "producers/manage_stock.html",
        products=products,
        categories=categories,
        user=current_user,
        nav_links=nav_for(current_user),
    )


# PRODUCER ACCOUNT SETTINGS

@producer_bp.route("/settings", methods=["GET", "POST"])
@producer_required
def settings():
    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        phone   = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if name and len(name) >= 2:
            current_user.name = name
        if address and len(address) >= 5:
            current_user.address = address
        current_user.phone = phone or current_user.phone
        db.session.commit()
        flash("Profile updated successfully.", "success")

    return render_template(
        "producers/acc_settings.html",
        user=current_user,
        nav_links=nav_for(current_user),
    )