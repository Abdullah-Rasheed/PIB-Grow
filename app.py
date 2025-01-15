import os
from flask import Flask, request, redirect, render_template, url_for, flash
from flask_cors import CORS
import logging
from dotenv import load_dotenv

# Initialize the Flask app
app = Flask(__name__, static_folder="assets", template_folder="pages")
CORS(app)

# Load environment variables from a .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)


# Landing page (Sign-In)
@app.route("/", methods=["GET", "POST"])
@app.route("/sign-in", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        # On form submit, directly redirect to the dashboard
        return redirect(url_for("dashboard"))
    return render_template("sign-in.html")


# Dashboard route
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# Other pages (no login protection, just simple routes)
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


# Handle 404 errors gracefully
@app.errorhandler(404)
def page_not_found(e):
    """Render a custom 404 error page."""
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
