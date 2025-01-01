import os
import csv
from flask import Flask, request, jsonify, redirect, render_template, send_file
from flask_cors import CORS
import requests
from dotenv import load_dotenv
from io import StringIO

# Initialize the Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)

# Load environment variables from a .env file
load_dotenv()

# Facebook App credentials
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://pib-grow.vercel.app/auth/callback")

# Facebook OAuth URL configuration (removed pages_read_monetization_insights)
FB_AUTH_URL = (
    f"https://www.facebook.com/v17.0/dialog/oauth?client_id={FACEBOOK_APP_ID}"
    f"&redirect_uri={REDIRECT_URI}&scope=public_profile,pages_show_list,pages_read_engagement,"
    f"pages_read_user_content,pages_messaging,pages_manage_metadata"
)

@app.route("/")
def dashboard():
    """Render the dashboard using Facebook API data."""
    access_token = request.args.get("access_token")
    if not access_token:
        return redirect("/auth/start")

    user_info = get_user_info(access_token)
    if "error" in user_info:
        return render_template("error.html", error=user_info["error"])

    pages = get_user_pages(access_token)
    if "error" in pages:
        return render_template("error.html", error=pages["error"])

    # Removed insights and monetization fetching part for now
    return render_template("dashboard.html", user=user_info, pages=pages.get("data", []))


@app.route("/auth/start", methods=["GET"])
def start_auth():
    """Redirect users to Facebook login."""
    return redirect(FB_AUTH_URL)


@app.route("/auth/callback", methods=["GET"])
def auth_callback():
    """Handle the callback and exchange code for access token."""
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Authorization code not found"}), 400

    # Exchange the code for an access token
    token_url = "https://graph.facebook.com/v17.0/oauth/access_token"
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "client_secret": FACEBOOK_APP_SECRET,
        "code": code,
    }
    response = requests.get(token_url, params=params)
    data = response.json()

    if "access_token" in data:
        access_token = data["access_token"]
        return redirect(f"/?access_token={access_token}")
    else:
        return jsonify({"error": data.get("error", "Unknown error")}), 400


def get_user_info(access_token):
    """Fetch user profile information from Facebook."""
    url = f"https://graph.facebook.com/me?fields=id,name&access_token={access_token}"
    response = requests.get(url)
    return response.json()


def get_user_pages(access_token):
    """Fetch the list of pages the user manages."""
    url = f"https://graph.facebook.com/me/accounts?access_token={access_token}"
    response = requests.get(url)
    return response.json()


@app.route("/data-deletion", methods=["POST"])
def data_deletion():
    """Handle Facebook data deletion requests."""
    body = request.json
    if not body or "signed_request" not in body:
        return jsonify({"error": "Invalid request"}), 400

    # Generate the response for data deletion
    response = {
        "url": "https://pib-grow.vercel.app/",
        "confirmation_code": "123456789"
    }
    return jsonify(response)


@app.route("/download_csv")
def download_csv():
    """Generate and download a CSV file of pages' data."""
    access_token = request.args.get("access_token")
    if not access_token:
        return redirect("/auth/start")

    pages = get_user_pages(access_token)
    if "error" in pages:
        return jsonify({"error": pages["error"]}), 400

    # Prepare CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Page ID", "Page Name"])

    for page in pages.get("data", []):
        writer.writerow([page["id"], page["name"]])

    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="pages_data.csv")


# Expose the `app` object for Vercel deployment
