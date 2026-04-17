from flask import Flask, request, redirect, url_for, render_template_string, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO
import imghdr

app = Flask(__name__)

# Configure SQLite database in project root
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database model for storing images
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(50), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)  # Store image as binary

# Create tables
with app.app_context():
    db.create_all()

# HTML template (inline for simplicity)
UPLOAD_FORM = """
<!doctype html>
<title>Upload Image</title>
<h1>Upload an Image</h1>
<form method="POST" enctype="multipart/form-data">
  <input type="file" name="image" accept="image/*" required>
  <input type="submit" value="Upload">
</form>
<hr>
<h2>Stored Images</h2>
<ul>
{% for img in images %}
  <li>
    {{ img.filename }} - <a href="{{ url_for('get_image', image_id=img.id) }}" target="_blank">View</a>
  </li>
{% endfor %}
</ul>
"""

@app.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        file = request.files.get('image')

        # Validate file presence
        if not file or file.filename.strip() == '':
            return "No file selected", 400

        # Read file data
        file_data = file.read()

        # Validate it's an image
        if not imghdr.what(None, file_data):
            return "Invalid image file", 400

        # Save to DB
        new_image = Image(
            filename=file.filename,
            mimetype=file.mimetype,
            data=file_data
        )
        db.session.add(new_image)
        db.session.commit()

        return redirect(url_for('upload_image'))

    # GET request: show upload form and list of images
    images = Image.query.all()
    return render_template_string(UPLOAD_FORM, images=images)

@app.route('/image/<int:image_id>')
def get_image(image_id):
    img = Image.query.get(image_id)
    if not img:
        abort(404)
    return send_file(BytesIO(img.data), mimetype=img.mimetype)

if __name__ == '__main__':
    app.run(debug=True)



'''
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
        '''