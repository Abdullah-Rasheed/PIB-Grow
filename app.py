import os
from flask import Flask, request, jsonify, redirect, render_template
from flask_cors import CORS
import requests
import logging
from dotenv import load_dotenv

# Initialize the Flask app
app = Flask(__name__, template_folder="templates/pages")
CORS(app)

# Load environment variables from a .env file
load_dotenv()

# Facebook App credentials
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = "https://pib-grow.vercel.app/auth/callback"

# Facebook OAuth URL configuration
FB_AUTH_URL = (
    f"https://www.facebook.com/v17.0/dialog/oauth?client_id={FACEBOOK_APP_ID}"
    f"&redirect_uri={REDIRECT_URI}&scope=pages_show_list,pages_read_engagement,"
    f"business_management,ads_read,pages_manage_metadata,read_insights,pages_manage_cta,pages_manage_ads"
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route("/")
def dashboard():
    """Render the dashboard with dummy data."""
    access_token = request.args.get("access_token")
    if not access_token:
        return redirect("/auth/start")

    user_info = get_user_info(access_token)
    if "error" in user_info:
        return render_template("error.html", error=user_info["error"])

    # Render the dashboard with dummy data since permissions are not available
    dummy_data = {
        "money": "$53,000",
        "views": "392,300",
        "likes": "+3,462",
        "revenue": "$103,430",
        "growth": "4% more in 2024",
        "countries": [
            {"name": "United States", "clicks": "2,206,590", "earnings": "$30,900", "bounce": "29.9%"},
            {"name": "Germany", "clicks": "93,900", "earnings": "$540", "bounce": "40.22%"},
            {"name": "Great Britain", "clicks": "19,400", "earnings": "$300", "bounce": "23.44%"},
            {"name": "Brasil", "clicks": "1,890,562", "earnings": "$3,960", "bounce": "32.14%"},
        ],
        "insights": {
            "impressions": "234,790",
            "clicks": "19,300",
            "monetization": "$46,000 Earned, $7,000 Pending",
            "pages": "7 active, 5 selected",
            "users": "+430 Happy Users"
        }
    }
    return render_template("dashboard.html", data=dummy_data)

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
    url = f"https://graph.facebook.com/me/accounts?fields=id,name,category,roles&access_token={access_token}"
    response = requests.get(url)
    return response.json()


def get_page_engagement(access_token, page_id):
    """Fetch engagement data for a given page."""
    metrics = "page_impressions,page_engaged_users,page_fan_adds"
    url = f"https://graph.facebook.com/{page_id}/insights?metric={metrics}&access_token={access_token}"
    response = requests.get(url)
    data = response.json()
    # Handle empty or error responses from Facebook
    if "data" in data:
        return data
    else:
        return {}

def get_page_ads_data(access_token, page_id):
    """Fetch monetization data for a given page."""
    url = f"https://graph.facebook.com/{page_id}/monetized_data?access_token={access_token}"
    response = requests.get(url)
    data = response.json()
    # Handle empty or error responses from Facebook
    if "data" in data:
        return data
    else:
        return {}


@app.route("/data-deletion", methods=["POST"])
def data_deletion():
    """Handle Facebook data deletion requests."""
    body = request.json
    if not body or "signed_request" not in body:
        return jsonify({"error": "Invalid request"}), 400

    response = {
        "url": "https://pib-grow.vercel.app/",
        "confirmation_code": "123456789"
    }
    return jsonify(response)


# Expose the `app` object for deployment
if __name__ == "__main__":
    app.run(debug=True)
