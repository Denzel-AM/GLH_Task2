import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
UPLOAD_FOLDER = os.path.join("static", "uploads", "products")


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file_storage) -> str | None:
    """
    Validate and save an uploaded image file.

    Args:
        file_storage: werkzeug FileStorage object from request.files

    Returns:
        URL string ('/static/uploads/products/<filename>') on success, or None
        if no file was provided or the extension is not allowed.
    """
    if not file_storage or file_storage.filename == "":
        return None

    if not _allowed(file_storage.filename):
        return None

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(unique_name)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_storage.save(os.path.join(UPLOAD_FOLDER, safe_name))

    return f"/static/uploads/products/{safe_name}"