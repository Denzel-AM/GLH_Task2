import re
from datetime import datetime, date

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, abort,
)
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user,
)
from flask_login import UserMixin

from models import db, User, Loyalty



# BLUEPRINT & LOGIN MANAGER

auth_bp    = Blueprint("auth", __name__)
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id: str):
    """
    Flask-Login callback — resolve a session user_id string to a User object.
    Supports plain integers ("42") and legacy prefixed IDs ("user-42").
    """
    if user_id.isdigit():
        return db.session.get(User, int(user_id))

    if "-" in user_id:
        try:
            _, real_id = user_id.split("-", 1)
            return db.session.get(User, int(real_id))
        except (ValueError, TypeError):
            return None

    return None


@login_manager.unauthorized_handler
def unauthorized():
    flash("Please log in to access that page.", "warning")
    return redirect(url_for("auth.login"))


NAV = {
    "public": [
        {"name": "Home",    "url": "/"},
        {"name": "About",   "url": "/about"},
        {"name": "Shop",    "url": "/shop"},
        {"name": "Contact", "url": "/contact-us"},
    ],
    "login": [
        {"name": "Home",     "url": "/"},
        {"name": "About",    "url": "/about"},
        {"name": "Shop",     "url": "/shop"},
        {"name": "Register", "url": "/register"},
    ],
    "register": [
        {"name": "Home",  "url": "/"},
        {"name": "About", "url": "/about"},
        {"name": "Shop",  "url": "/shop"},
        {"name": "Login", "url": "/login"},
    ],
    "customer": [
        {"name": "Home",      "url": "/"},
        {"name": "Shop",      "url": "/shop"},
        {"name": "My Orders", "url": "/orders"},
        {"name": "Dashboard", "url": "/dashboard"},
        {"name": "Logout",    "url": "/logout"},
    ],
    "producer": [
        {"name": "Home",         "url": "/"},
        {"name": "Dashboard",    "url": "/producer/dashboard"},
        {"name": "Manage Stock", "url": "/producer/manage-stock"},
        {"name": "Settings",     "url": "/producer/settings"},
        {"name": "Logout",       "url": "/logout"},
    ],
    "admin": [
        {"name": "Home",             "url": "/"},
        {"name": "Admin Dashboard",  "url": "/admin/dashboard"},
        {"name": "Manage Accounts",  "url": "/admin/manage-accounts"},
        {"name": "Manage Products",  "url": "/admin/manage-products"},
        {"name": "All Orders",       "url": "/admin/orders"},
        {"name": "Settings",         "url": "/account-settings"},
        {"name": "Logout",           "url": "/logout"},
    ],
}

def nav_for(user) -> list:
    """Return the correct nav link set for the given user."""
    if user.role == "producer":
        return NAV["producer"]
    if user.role == "admin":
        return NAV["admin"]
    return NAV["customer"]





# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_PASSWORD_RE = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$'
)


def is_valid_password(password: str) -> bool:
    """
    Return True if password satisfies all strength rules:
    - At least 8 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    """
    return bool(_PASSWORD_RE.match(password))


def validate_dob(dob_str: str) -> tuple[date | None, str | None]:
    """
    Parse and validate a date-of-birth string (YYYY-MM-DD).
    Returns (date_object, None) on success or (None, error_message) on failure.
    Age must be between 16 and 120.
    """
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None, "Please enter a valid date of birth."

    today = date.today()
    if dob > today:
        return None, "Date of birth cannot be in the future."

    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 16:
        return None, "You must be at least 16 years old to register."
    if age > 120:
        return None, "Please enter a valid date of birth."

    return dob, None


def _dashboard_url_for(user: User) -> str:
    """Return the correct post-login redirect endpoint for a given user."""
    if user.role == "admin":
        return url_for("admin.dashboard")
    if user.role == "producer":
        return url_for("producer.dashboard")
    return url_for("customer.dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Show the login form (GET) and authenticate the user (POST).
    Redirects to role-appropriate dashboard on success.
    Inactive accounts are rejected even if credentials are correct.
    """
    if current_user.is_authenticated:
        return redirect(_dashboard_url_for(current_user))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember_me"))

        # --- Fetch user ---
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", nav_links=NAV["login"])

        if not user.is_active:
            flash("Your account has been deactivated. Please contact support.", "warning")
            return render_template("auth/login.html", nav_links=NAV["login"])

        # --- Login ---
        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        db.session.commit()

        flash(f"Welcome back, {user.name.split()[0]}!", "success")

        # Honour ?next= param (Flask-Login sets this on unauthorised redirect)
        next_page = request.args.get("next")
        return redirect(next_page or _dashboard_url_for(user))

    return render_template("auth/login.html", nav_links=NAV["login"])


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    New customer registration.
    On success: creates a User, a linked Loyalty account, then redirects to login.
    """
    if current_user.is_authenticated:
        return redirect(_dashboard_url_for(current_user))

    if request.method == "POST":
        name             = request.form.get("name", "").strip()
        email            = request.form.get("email", "").strip().lower()
        phone            = request.form.get("phone", "").strip()
        dob_str          = request.form.get("dob", "").strip()
        address          = request.form.get("address", "").strip()
        password         = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")# fixed

        ctx = {"nav_links": NAV["register"]}   # shorthand for re-renders

        # ── Name ─────────────────────────────────────────────────────────────
        if not name or len(name) < 2:
            flash("Please enter a valid full name (at least 2 characters).", "danger")
            return render_template("auth/register.html", **ctx)

        # Allow spaces and hyphens for compound names (e.g. "Mary-Jane")
        if not re.match(r"^[A-Za-z][A-Za-z '-]{1,}$", name):
            flash("Name must contain only letters, spaces, hyphens, or apostrophes.", "danger")
            return render_template("auth/register.html", **ctx)

        # ── Email ─────────────────────────────────────────────────────────────
        if not email:
            flash("An email address is required.", "danger")
            return render_template("auth/register.html", **ctx)

        if User.query.filter_by(email=email).first():
            flash("That email is already registered. Please log in or use a different address.", "danger")
            return render_template("auth/register.html", **ctx)

        # ── Date of Birth ─────────────────────────────────────────────────────
        dob, dob_error = validate_dob(dob_str)
        if dob_error:
            flash(dob_error, "danger")
            return render_template("auth/register.html", **ctx)

        # ── Address ───────────────────────────────────────────────────────────
        if not address or len(address) < 5:
            flash("Please enter a valid delivery address (at least 5 characters).", "danger")
            return render_template("auth/register.html", **ctx)

        # ── Password ──────────────────────────────────────────────────────────
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", **ctx)

        if not is_valid_password(password):
            flash(
                "Password must be at least 8 characters and include an uppercase letter, "
                "a lowercase letter, a number, and a special character.",
                "danger",
            )
            return render_template("auth/register.html", **ctx)

        # ── Create user and linked loyalty account ────────────────────────────
        new_user = User(
            name    = name,
            email   = email,
            phone   = phone or None,
            address = address,
            #role    = Role.CUSTOMER,
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.flush()   # get new_user.id before committing

        # Every new customer gets a Loyalty account starting at 0 points
        loyalty = Loyalty(user_id=new_user.id, points=0)
        db.session.add(loyalty)

        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", nav_links=NAV["register"])


# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("auth.login"))




# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT SETTINGS (auth-owned route for password change)
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/account-settings", methods=["GET", "POST"])
@login_required
def account_settings():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password     = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "danger")
        elif not is_valid_password(new_password):
            flash(
                "New password must be at least 8 characters with uppercase, lowercase, "
                "a number, and a special character.",
                "danger",
            )
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Password updated successfully.", "success")

    return render_template(
        "auth/account_settings.html",
        user=current_user,
        nav_links=nav_for(current_user),
    )

@auth_bp.route("/account/update", methods=["POST"])
@login_required
def update_account():
    """Update name, email, phone, and address for the current user."""
    user    = current_user
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip().lower()
    phone   = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    # ── Validation ────────────────────────────────────────────────────────────
    if not name or len(name) < 2:
        flash("Name must be at least 2 characters.", "danger")
        return redirect(url_for("auth.account_settings"))

    if not re.match(r"^[A-Za-z][A-Za-z '-]{1,}$", name):
        flash("Name must contain only letters, spaces, hyphens, or apostrophes.", "danger")
        return redirect(url_for("auth.account_settings"))

    if not email:
        flash("Email address is required.", "danger")
        return redirect(url_for("auth.account_settings"))

    # Check email uniqueness — exclude the current user's own record
    taken = User.query.filter(User.email == email, User.id != user.id).first()
    if taken:
        flash("That email address is already in use.", "danger")
        return redirect(url_for("auth.account_settings"))

    if address and len(address) < 5:
        flash("Please enter a valid address (at least 5 characters).", "danger")
        return redirect(url_for("auth.account_settings"))

    # ── Persist ───────────────────────────────────────────────────────────────
    user.name    = name
    user.email   = email
    user.phone   = phone or None
    user.address = address or user.address

    db.session.commit()
    flash("Account details updated successfully.", "success")
    return redirect(url_for("auth.account_settings"))





@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Step 1 of password reset flow.
    Accepts an email address and — if it belongs to a registered user —
    generates a signed time-limited token and logs a reset link (dev mode).
    """
    if current_user.is_authenticated:
        return redirect(_dashboard_url_for(current_user))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Please enter your email address.", "danger")
            return render_template("auth/forgot_password.html", nav_links=NAV["login"])

        user = User.query.filter_by(email=email).first()

        # Always show the same message to prevent user enumeration attacks.
        flash(
            "If that email is registered, you will receive a reset link shortly.",
            "success",
        )

        if user and user.is_active:
            token = _generate_reset_token(user)
            _send_reset_email(user, token)

        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", nav_links=NAV["login"])




@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    """
    Step 2 of the password reset flow.
    Validates the token, then lets the user choose a new password.
    """
    if current_user.is_authenticated:
        return redirect(_dashboard_url_for(current_user))

    user = _verify_reset_token(token)
    if user is None:
        flash("This reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_password     = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/reset_password.html", token=token, nav_links=NAV["login"])

        if not is_valid_password(new_password):
            flash(
                "Password must be at least 8 characters and include an uppercase letter, "
                "a lowercase letter, a number, and a special character.",
                "danger",
            )
            return render_template("auth/reset_password.html", token=token, nav_links=NAV["login"])

        user.set_password(new_password)
        db.session.commit()

        flash("Password reset successfully. Please sign in with your new password.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token, nav_links=NAV["login"])



#__________________________________________________________________________
#delete account
#______________________________________________________________________




@auth_bp.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    """
    Permanently delete the current user's account and all related data.
    Requires password confirmation and the user typing 'DELETE'.
    Admin accounts cannot be self-deleted for safety.
    """
    user                = current_user
    current_password    = request.form.get("current_password", "")
    confirmation_text   = request.form.get("confirm_text", "").strip().upper()

    # Prevent admins from accidentally deleting themselves via this route
    if user.role == "admin":
        flash("Admin accounts cannot be deleted through this interface. Contact the system owner.", "danger")
        return redirect(url_for("auth.account_settings"))

    if not user.check_password(current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("auth.account_settings"))

    if confirmation_text != "DELETE":
        flash("Please type DELETE (in capitals) to confirm account deletion.", "danger")
        return redirect(url_for("auth.account_settings"))

    logout_user()
    db.session.delete(user)   # cascade in models.py removes orders, loyalty, enquiries
    db.session.commit()

    flash("Your account and all associated data have been permanently deleted.", "success")
    return redirect(url_for("auth.login"))

# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET TOKEN HELPERS
# ─────────────────────────────────────────────────────────────────────────────

import hashlib
import hmac
import time
from flask import current_app

# Re-export Loyalty for use in register route above
from models import Loyalty

_RESET_TOKEN_MAX_AGE_SECONDS = 3600   # 1 hour


def _generate_reset_token(user: User) -> str:
    """
    Build a signed token: base64( user_id | timestamp | HMAC-SHA256 ).
    No extra dependency required — uses only Python stdlib.
    """
    import base64
    ts      = int(time.time())
    payload = f"{user.id}:{ts}"
    sig     = _sign(payload)
    raw     = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _verify_reset_token(token: str):
    """Return the User if the token is valid and unexpired, else None."""
    import base64
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        user_id_str, ts_str, sig = raw.rsplit(":", 2)
        payload = f"{user_id_str}:{ts_str}"

        expected = _sign(payload)
        if not hmac.compare_digest(expected, sig):
            return None

        if time.time() - int(ts_str) > _RESET_TOKEN_MAX_AGE_SECONDS:
            return None

        return db.session.get(User, int(user_id_str))

    except Exception:
        return None

def _sign(payload: str) -> str:
    """HMAC-SHA256 signature using the app's SECRET_KEY."""
    key = current_app.secret_key
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def _send_reset_email(user: User, token: str) -> None:
    """
    Sends a password reset link. In development, the link is printed to console.
    Replace with your email provider (Flask-Mail, SendGrid, etc.) for production.
    """
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    print(f"[GLH DEV] Password reset link for {user.email}: {reset_url}")