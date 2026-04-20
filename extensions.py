import stripe
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app, jsonify
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
# CHECKOUT  (collects delivery info + loyalty choice, then goes to payment)
# ─────────────────────────────────────────────────────────────────────────────

@shop_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("shop.shop"))

    # Build cart items — recheck stock at this point
    cart_items = []
    subtotal = 0.0
    for product_id_str, qty in list(cart.items()):
        product = db.session.get(Product, int(product_id_str))
        if not product:
            continue
        actual_qty = min(qty, product.stock_quantity)
        if actual_qty <= 0:
            continue
        line_total = round(product.price * actual_qty, 2)
        subtotal += line_total
        cart_items.append({
            "product": product,
            "quantity": actual_qty,
            "subtotal": line_total,
        })
    subtotal = round(subtotal, 2)

    if not cart_items:
        flash("All items in your cart are out of stock.", "warning")
        return redirect(url_for("shop.shop"))

    if request.method == "POST":
        delivery_type    = request.form.get("delivery_type", "collection")
        delivery_address = request.form.get("delivery_address", "").strip()
        use_loyalty      = request.form.get("use_loyalty") == "on"

        if delivery_type == "delivery" and not delivery_address:
            delivery_address = current_user.address

        # Loyalty discount calculation
        loyalty_discount = 0.0
        points_used = 0
        if use_loyalty and current_user.loyalty_points >= 100:
            max_discount = current_user.loyalty_points / 100.0
            loyalty_discount = min(round(max_discount, 2), round(subtotal * 0.20, 2))
            points_used = int(loyalty_discount * 100)

        final_total = round(subtotal - loyalty_discount, 2)

        # Store checkout details in session so payment route can use them
        session["pending_order"] = {
            "delivery_type":    delivery_type,
            "delivery_address": delivery_address if delivery_type == "delivery" else None,
            "loyalty_discount": loyalty_discount,
            "points_used":      points_used,
            "final_total":      final_total,
        }

        return redirect(url_for("shop.payment"))

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


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT  (Stripe Elements card entry)
# ─────────────────────────────────────────────────────────────────────────────

@shop_bp.route("/payment", methods=["GET"])
@login_required
def payment():
    pending = session.get("pending_order")
    if not pending:
        flash("Please complete checkout first.", "warning")
        return redirect(url_for("shop.checkout"))

    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("shop.shop"))

    final_total = pending["final_total"]

    # Create a Stripe PaymentIntent
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    intent = stripe.PaymentIntent.create(
        amount=int(final_total * 100),   # Stripe uses pence
        currency="gbp",
        metadata={
            "user_id":  current_user.id,
            "email":    current_user.email,
        },
    )

    # Store client_secret in session so confirm route can verify
    session["stripe_pi"] = intent.id

    return render_template(
        "payment.html",
        client_secret=intent.client_secret,
        stripe_public_key=current_app.config["STRIPE_PUBLIC_KEY"],
        final_total=final_total,
        pending=pending,
        nav_links=_get_nav(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT CONFIRM  (called after Stripe confirms on the frontend)
# ─────────────────────────────────────────────────────────────────────────────

@shop_bp.route("/payment/confirm", methods=["POST"])
@login_required
def payment_confirm():
    pending = session.get("pending_order")
    cart    = session.get("cart", {})
    pi_id   = session.get("stripe_pi")

    if not pending or not cart or not pi_id:
        flash("Session expired. Please try again.", "warning")
        return redirect(url_for("shop.checkout"))

    # Verify payment actually succeeded with Stripe
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    try:
        intent = stripe.PaymentIntent.retrieve(pi_id)
    except stripe.error.StripeError as e:
        flash(f"Payment verification failed: {e.user_message}", "danger")
        return redirect(url_for("shop.payment"))

    if intent.status != "succeeded":
        flash("Payment was not completed. Please try again.", "danger")
        return redirect(url_for("shop.payment"))

    # ── Build order ──
    cart_items = []
    for product_id_str, qty in list(cart.items()):
        product = db.session.get(Product, int(product_id_str))
        if not product:
            continue
        actual_qty = min(qty, product.stock_quantity)
        if actual_qty <= 0:
            continue
        cart_items.append({
            "product":  product,
            "quantity": actual_qty,
        })

    if not cart_items:
        flash("All items went out of stock. Your payment will be refunded.", "warning")
        # Refund the PaymentIntent
        stripe.Refund.create(payment_intent=pi_id)
        session.pop("pending_order", None)
        session.pop("stripe_pi", None)
        return redirect(url_for("shop.shop"))

    loyalty_discount = pending["loyalty_discount"]
    points_used      = pending["points_used"]
    final_total      = pending["final_total"]

    order = Order(
        user_id          = current_user.id,
        total_amount     = final_total,
        order_status     = "Confirmed",
        delivery_type    = pending["delivery_type"],
        delivery_address = pending["delivery_address"],
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
        item["product"].stock_quantity -= item["quantity"]
        item["product"].update_availability()
        db.session.add(StockMovement(
            product_id    = item["product"].id,
            change_amount = -item["quantity"],
            movement_type = "sale",
            note          = f"Order #{order.id}",
        ))

    points_earned = int(final_total)
    current_user.loyalty_points = (current_user.loyalty_points - points_used) + points_earned

    db.session.commit()

    # Clear session
    session.pop("cart", None)
    session.pop("pending_order", None)
    session.pop("stripe_pi", None)

    msg = f"Order #GLH-{order.id:04d} placed! You earned {points_earned} loyalty points."
    if loyalty_discount > 0:
        msg += f" Loyalty discount applied: £{loyalty_discount:.2f}."
    flash(msg, "success")

    return redirect(url_for("shop.success", order_id=order.id))


# ─────────────────────────────────────────────────────────────────────────────
# SUCCESS
# ─────────────────────────────────────────────────────────────────────────────

@shop_bp.route("/success/<int:order_id>")
@login_required
def success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("success.html", order=order, nav_links=_get_nav())