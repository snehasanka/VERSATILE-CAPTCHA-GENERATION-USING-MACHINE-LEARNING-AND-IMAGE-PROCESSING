import os
import json
from io import BytesIO
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

from captcha_generator import generate_random_object_captcha

# -------------------------------------------------
# Flask app config
# -------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "change_this_secret_for_your_project"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

os.makedirs(USER_DATA_DIR, exist_ok=True)


# -------------------------------------------------
# Helper functions for user JSON storage
# -------------------------------------------------
def safe_username(username: str) -> str:
    """Make username safe for folder name."""
    return "".join(
        ch if ch.isalnum() or ch in ("_", "-") else "_"
        for ch in username.strip()
    )


def get_user_folder(username: str) -> str:
    folder = os.path.join(USER_DATA_DIR, safe_username(username))
    os.makedirs(folder, exist_ok=True)
    return folder


def profile_path(username: str) -> str:
    return os.path.join(get_user_folder(username), "profile.json")


def logs_path(username: str) -> str:
    return os.path.join(get_user_folder(username), "logs.json")


def save_profile(username: str, email: str, password: str, password_hash: str) -> None:
    """
    Save profile info into profile.json
    WARNING: This stores real password only for mini-project demo.
    """
    data = {
        "username": username,
        "email": email,
        "password": password,             # Real password (for demo only)
        "password_hash": password_hash,   # Hashed password (proper check)
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    with open(profile_path(username), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_login_log(username: str) -> None:
    """Append each login time into logs.json."""
    path = logs_path(username)
    logs = {"logins": []}

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = {"logins": []}

    if "logins" not in logs:
        logs["logins"] = []

    logs["logins"].append(datetime.utcnow().isoformat() + "Z")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)


def load_profile_by_email(email: str):
    """Find user profile.json by email."""
    email = email.strip().lower()
    for name in os.listdir(USER_DATA_DIR):
        folder = os.path.join(USER_DATA_DIR, name)
        if not os.path.isdir(folder):
            continue
        p_path = os.path.join(folder, "profile.json")
        if not os.path.exists(p_path):
            continue
        try:
            with open(p_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("email", "").lower() == email:
                return data
        except Exception:
            continue
    return None


def username_exists(username: str) -> bool:
    """Check if username folder with profile.json already exists."""
    folder = os.path.join(USER_DATA_DIR, safe_username(username))
    return os.path.isdir(folder) and os.path.exists(os.path.join(folder, "profile.json"))


# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/captcha")
def captcha_image():
    """Generate CAPTCHA image and store answer in session."""
    backgrounds_folder = os.path.join(ASSETS_DIR, "backgrounds")
    objects_folder = os.path.join(ASSETS_DIR, "objects")

    img, question = generate_random_object_captcha(
        backgrounds_folder=backgrounds_folder,
        objects_folder=objects_folder,
    )

    # Question format: "How many objects are inserted in the image? Answer: N"
    answer_str = question.split("Answer:")[-1].strip()
    session["captcha_answer"] = answer_str

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        captcha_input = request.form.get("captcha", "").strip()

        correct_captcha = session.get("captcha_answer")

        # Basic checks
        if not username or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if not correct_captcha or captcha_input != correct_captcha:
            flash("Incorrect CAPTCHA. Please try again.", "error")
            return redirect(url_for("register"))

        # Unique username / email
        if username_exists(username):
            flash("Username already exists.", "error")
            return redirect(url_for("register"))

        if load_profile_by_email(email) is not None:
            flash("Email already registered.", "error")
            return redirect(url_for("register"))

        # Save profile
        password_hash = generate_password_hash(password)
        save_profile(username, email, password, password_hash)

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        captcha_input = request.form.get("captcha", "").strip()

        correct_captcha = session.get("captcha_answer")

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("login"))

        if not correct_captcha or captcha_input != correct_captcha:
            flash("Incorrect CAPTCHA. Please try again.", "error")
            return redirect(url_for("login"))

        profile = load_profile_by_email(email)
        if not profile:
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        if not check_password_hash(profile.get("password_hash", ""), password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        username = profile["username"]
        session["username"] = username

        append_login_log(username)

        flash("Login successful!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    username = session.get("username")
    if not username:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    return render_template("dashboard.html", username=username)


@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
