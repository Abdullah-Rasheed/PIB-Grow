import os
from flask import Flask, request, redirect, render_template, send_from_directory, abort, session, url_for, flash
from flask_cors import CORS
from flask_session import Session
from functools import wraps
import logging
from dotenv import load_dotenv

# Initialize the Flask app
app = Flask(__name__, static_folder="assets", template_folder="pages")
CORS(app)

# Configure secret key and session
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Load environment variables from a .env file
load_dotenv()

# Test user credentials
TEST_USER = {"username": "testuser", "password": "testpassword"}

# Configure logging
logging.basicConfig(level=logging.DEBUG)


# Protect routes decorator
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("sign_in"))
        return func(*args, **kwargs)
    return wrapper


# Sign-In page and form handling
@app.route("/", methods=["GET", "POST"])
@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == TEST_USER["username"] and password == TEST_USER["password"]:
            session["user"] = username
            return redirect(url_for("dashboard"))  # Redirect to dashboard after login
        else:
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for("sign_in"))
    return render_template("sign-in.html")


# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("sign_in"))


# Dashboard route
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# Other protected pages
@app.route("/partners")
@login_required
def partners():
    return render_template("partners.html")


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/accounting")
@login_required
def accounting():
    return render_template("accounting.html")


@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html")


# Serve static assets
@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serve static files from the assets folder."""
    try:
        return send_from_directory(app.static_folder, filename)
    except FileNotFoundError:
        abort(404)


# Serve favicon if required
@app.route("/favicon.ico")
def favicon():
    """Serve the favicon if requested."""
    return send_from_directory(app.static_folder, "favicon.ico")


# Handle 404 errors gracefully
@app.errorhandler(404)
def page_not_found(e):
    """Render a custom 404 error page."""
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
