from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    orders = db.relationship("Order", backref="user", lazy=True, cascade="all, delete-orphan")
    enquiries = db.relationship("Enquiry", backref="user", lazy=True, cascade="all, delete-orphan")
    loyalty_account = db.relationship("Loyalty", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"



class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False, unique=True)

    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.category_name}>"



class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(255), nullable=True)
    availability_status = db.Column(db.String(50), default="In Stock")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    order_items = db.relationship("OrderItem", backref="product", lazy=True)
    stock_movements = db.relationship("StockMovement", backref="product", lazy=True, cascade="all, delete-orphan")

    def update_availability(self):
        self.availability_status = "Out of Stock" if self.stock_quantity <= 0 else "In Stock"

    def __repr__(self):
        return f"<Product {self.product_name}>"



class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    order_status = db.Column(db.String(50), nullable=False, default="Pending")

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    order_items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.id}>"



class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    item_price = db.Column(db.Float, nullable=False)

    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    def __repr__(self):
        return f"<OrderItem {self.id}>"



class Enquiry(db.Model):
    __tablename__ = "enquiries"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<Enquiry {self.email}>"



class Loyalty(db.Model):
    __tablename__ = "loyalty"

    id = db.Column(db.Integer, primary_key=True)
    points = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)

    def __repr__(self):
        return f"<Loyalty User {self.user_id}>"



class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    id = db.Column(db.Integer, primary_key=True)
    change_amount = db.Column(db.Integer, nullable=False)
    movement_type = db.Column(db.String(50), nullable=False)  # sale, restock, manual_adjustment
    movement_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    note = db.Column(db.String(255), nullable=True)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    def __repr__(self):
        return f"<StockMovement {self.id}>"