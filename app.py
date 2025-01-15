import os
from flask import Flask, request, redirect, render_template, send_from_directory, abort, session, url_for, flash
from flask_cors import CORS
from flask_session import Session
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

# Facebook App credentials
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = "https://pib-grow.vercel.app/auth/callback"  # Updated for local testing

# Facebook OAuth URL configuration
FB_AUTH_URL = (
    f"https://www.facebook.com/v17.0/dialog/oauth?client_id={FACEBOOK_APP_ID}"
    f"&redirect_uri={REDIRECT_URI}&scope=pages_show_list,pages_read_engagement,"
    f"business_management,ads_read,pages_manage_metadata,read_insights,pages_manage_cta,pages_manage_ads"
)

# Test user credentials
TEST_USER = {"username": "testuser", "password": "testpassword"}

# Configure logging
logging.basicConfig(level=logging.DEBUG)


# Landing page (Sign-In)
@app.route("/")
@app.route("/sign-in")
def sign_up():
    return render_template("sign-in.html")


# Login route
@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == TEST_USER["username"] and password == TEST_USER["password"]:
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for("sign_in"))
    return render_template("sign-in.html")


# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("sign_in"))


# Protect routes decorator
def login_required(func):
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("sign_in"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# Facebook OAuth start route
@app.route("/auth/start", methods=["GET"])
def start_auth():
    """Redirect users to Facebook login."""
    return redirect(FB_AUTH_URL)


# Facebook OAuth callback route
@app.route("/auth/callback", methods=["GET"])
def auth_callback():
    """Handle the callback and simulate a successful OAuth process."""
    code = request.args.get("code")
    if not code:
        return "Authorization code not found", 400

    # Simulate successful login and redirect to the dashboard
    return redirect("/dashboard")


# Dashboard route
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# Other pages (protected by login)
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


# Handle Facebook data deletion
@app.route("/data-deletion", methods=["POST"])
def data_deletion():
    """Handle Facebook data deletion requests."""
    body = request.json
    if not body or "signed_request" not in body:
        return "Invalid request", 400

    response = {
        "url": "https://pib-grow.vercel.app/",
        "confirmation_code": "123456789",
    }
    return response


# Handle 404 errors gracefully
@app.errorhandler(404)
def page_not_found(e):
    """Render a custom 404 error page."""
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
