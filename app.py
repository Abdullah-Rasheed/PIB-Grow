import os
from flask import Flask, request, redirect, render_template, send_from_directory, abort
from flask_cors import CORS
import logging
from dotenv import load_dotenv

# Initialize the Flask app
app = Flask(__name__, static_folder="assets", template_folder="pages")
CORS(app)

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

# Configure logging
logging.basicConfig(level=logging.DEBUG)


# Landing page (Sign-Up)
@app.route("/")
@app.route("/sign-up")
def sign_up():
    return render_template("sign-up.html")


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
def dashboard():
    return render_template("dashboard.html")


# Other pages
@app.route("/partners")
def partners():
    return render_template("partners.html")


@app.route("/profile")
def profile():
    return render_template("profile.html")


@app.route("/accounting")
def accounting():
    return render_template("accounting.html")


@app.route("/reports")
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
