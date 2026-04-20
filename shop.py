from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from flask_login import current_user, login_required
from models import db, Product, Category, Order, OrderItem, StockMovement
from datetime import datetime
from auth import NAV, nav_for

shop_bp = Blueprint("shop", __name__)


def _get_nav():
    return nav_for(current_user) if current_user.is_authenticated else NAV["public"]


def _cart_count():
    cart = session.get("cart", {})
    return sum(cart.values())


# ─────────────────────────────────────────────────────────────────────────────
# SHOP LISTING
# ─────────────────────────────────────────────────────────────────────────────

@shop_bp.route("/shop")
def shop():
    categories = Category.query.all()
    category_id = request.args.get("category", type=int)
    search = request.args.get("search", "").strip()

    query = Product.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Product.product_name.ilike(f"%{search}%"))

    products = query.order_by(Product.product_name).all()

    return render_template(
        "shop.html",
        products=products,
        categories=categories,
        selected_category=category_id,
        search=search,
        cart_count=_cart_count(),
        nav_links=_get_nav(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────────────────────────

@shop_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    product_id = str(request.form.get("product_id", ""))
    try:
        quantity = int(request.form.get("quantity", 1))
    except ValueError:
        quantity = 1

    if not product_id:
        flash("Invalid product.", "danger")
        return redirect(url_for("shop.shop"))

    product = db.session.get(Product, int(product_id))
    if not product or product.stock_quantity <= 0:
        flash("This product is currently out of stock.", "warning")
        return redirect(url_for("shop.shop"))

    cart = session.get("cart", {})
    current_qty = cart.get(product_id, 0)
    new_qty = current_qty + quantity

    if new_qty > product.stock_quantity:
        flash(f"Only {product.stock_quantity} units of {product.product_name} available.", "warning")
        new_qty = product.stock_quantity

    cart[product_id] = new_qty
    session["cart"] = cart
    flash(f"Added {product.product_name} to your cart.", "success")

    next_page = request.form.get("next", url_for("shop.shop"))
    return redirect(next_page)


@shop_bp.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    cart_items = []
    total = 0.0

    for product_id_str, qty in list(cart.items()):
        product = db.session.get(Product, int(product_id_str))
        if product:
            subtotal = round(product.price * qty, 2)
            total += subtotal
            cart_items.append({
                "product": product,
                "quantity": qty,
                "subtotal": subtotal,
            })

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=round(total, 2),
        nav_links=_get_nav(),
    )


@shop_bp.route("/cart/update", methods=["POST"])
def update_cart():
    product_id = str(request.form.get("product_id", ""))
    try:
        quantity = int(request.form.get("quantity", 0))
    except ValueError:
        quantity = 0

    cart = session.get("cart", {})

    if quantity <= 0:
        cart.pop(product_id, None)
    else:
        product = db.session.get(Product, int(product_id))
        if product:
            cart[product_id] = min(quantity, product.stock_quantity)

    session["cart"] = cart
    return redirect(url_for("shop.view_cart"))


@shop_bp.route("/cart/remove", methods=["POST"])
def remove_from_cart():
    product_id = str(request.form.get("product_id", ""))
    cart = session.get("cart", {})
    removed = cart.pop(product_id, None)
    session["cart"] = cart
    if removed:
        flash("Item removed from cart.", "success")
    return redirect(url_for("shop.view_cart"))


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────

@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("shop.shop"))

    # Build cart items from DB
    cart_items = []
    subtotal = 0.0
    for product_id_str, qty in list(cart.items()):
        product = db.session.get(Product, int(product_id_str))
        if product and product.stock_quantity > 0:
            line_total = round(product.price * qty, 2)
            subtotal += line_total
            cart_items.append({
                "product": product,
                "quantity": qty,
                "subtotal": line_total,
            })
    subtotal = round(subtotal, 2)

    if request.method == "POST":
        delivery_type    = request.form.get("delivery_type", "collection")
        delivery_address = request.form.get("delivery_address", "").strip()
        use_loyalty      = request.form.get("use_loyalty") == "on"

        if delivery_type == "delivery" and not delivery_address:
            delivery_address = current_user.address

        # Loyalty discount: 100 points = £1, max 20% of order
        loyalty_discount = 0.0
        points_used = 0
        if use_loyalty and current_user.loyalty_points >= 100:
            max_discount = current_user.loyalty_points / 100.0
            loyalty_discount = min(round(max_discount, 2), round(subtotal * 0.20, 2))
            points_used = int(loyalty_discount * 100)

        final_total = round(subtotal - loyalty_discount, 2)

        # Create order
        order = Order(
            user_id         = current_user.id,
            total_amount    = final_total,
            order_status    = "Confirmed",
            delivery_type   = delivery_type,
            delivery_address= delivery_address if delivery_type == "delivery" else None,
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            oi = OrderItem(
                order_id   = order.id,
                product_id = item["product"].id,
                quantity   = item["quantity"],
                item_price = item["product"].price,
            )
            db.session.add(oi)

            # Deduct stock and log movement
            item["product"].stock_quantity -= item["quantity"]
            item["product"].update_availability()
            movement = StockMovement(
                product_id    = item["product"].id,
                change_amount = -item["quantity"],
                movement_type = "sale",
                note          = f"Order #{order.id}",
            )
            db.session.add(movement)

        # Update loyalty points: deduct used, award earned (1 point per £1 spent)
        points_earned = int(final_total)
        current_user.loyalty_points = (current_user.loyalty_points - points_used) + points_earned

        db.session.commit()
        session.pop("cart", None)

        msg = f"Order #GLH-{order.id:04d} placed! You earned {points_earned} loyalty points."
        if loyalty_discount > 0:
            msg += f" Loyalty discount applied: £{loyalty_discount:.2f}."
        flash(msg, "success")


        order_id = oi.order_id
        return redirect(url_for("shop.success", order_id=order_id))

    # Loyalty context for template
    available_discount = 0.0
    if current_user.loyalty_points >= 100:
        max_discount = current_user.loyalty_points / 100.0
        available_discount = min(round(max_discount, 2), round(subtotal * 0.20, 2))

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        subtotal=subtotal,
        available_discount=available_discount,
        loyalty_points=current_user.loyalty_points,
        nav_links=_get_nav(),
    )

@shop_bp.route("/success/<int:order_id>", methods=["GET", "POST"])
@login_required
def success(order_id):
    order = Order.query.get_or_404(order_id)
    #make sure its the user's order
    if order.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))

    if order.order_status != "confirmed":
        return redirect(url_for("shop.checkout", order_id=order_id))
    

    return render_template("success.html", order=order, nav_links=_get_nav() )