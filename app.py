import os
from flask import Flask, request, jsonify, redirect, render_template
from flask_cors import CORS
import requests
import logging
from dotenv import load_dotenv

# Initialize the Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)

# Load environment variables
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

# Dummy data for fallback
DUMMY_USER = {"id": "12345", "name": "Demo User"}
DUMMY_PAGES = [
    {
        "id": "1",
        "name": "Demo Page 1",
        "insights": {
            "data": [
                {"values": [{"value": 1500}]},  # Total impressions
                {"values": [{"value": 450}]}   # Engaged users
            ]
        },
        "monetization": {
            "data": [{"value": 200.00}]
        },
        "posts": []
    }
]

@app.route("/")
def dashboard():
    """Render the dashboard using Facebook API data."""
    access_token = request.args.get("access_token")
    if not access_token:
        return redirect("/auth/start")

    try:
        # Fetch user info and pages
        user_info = get_user_info(access_token)
        pages = get_user_pages(access_token)

        # Check for errors; fallback to dummy data if necessary
        if "error" in user_info or "error" in pages:
            user_info = DUMMY_USER
            pages = {"data": DUMMY_PAGES}

        # Process insights and monetization data
        for page in pages.get("data", []):
            page_id = page["id"]
            page["insights"] = get_page_engagement(access_token, page_id) or DUMMY_PAGES[0]["insights"]
            page["monetization"] = get_page_ads_data(access_token, page_id) or DUMMY_PAGES[0]["monetization"]

        return render_template("dashboard.html", user=user_info, pages=pages.get("data", []))
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return render_template("dashboard.html", user=DUMMY_USER, pages=DUMMY_PAGES, error=str(e))

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

# Helper functions
def get_user_info(access_token):
    """Fetch user profile information from Facebook."""
    try:
        url = f"https://graph.facebook.com/me?fields=id,name&access_token={access_token}"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching user info: {e}")
        return {"error": "Failed to fetch user info"}

def get_user_pages(access_token):
    """Fetch the list of pages the user manages."""
    try:
        url = f"https://graph.facebook.com/me/accounts?fields=id,name,category,roles&access_token={access_token}"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching user pages: {e}")
        return {"error": "Failed to fetch pages"}

def get_page_engagement(access_token, page_id):
    """Fetch engagement data for a given page."""
    try:
        metrics = "page_impressions,page_engaged_users"
        url = f"https://graph.facebook.com/{page_id}/insights?metric={metrics}&access_token={access_token}"
        response = requests.get(url)
        data = response.json()
        return data if "data" in data else {}
    except Exception as e:
        logging.error(f"Error fetching page engagement: {e}")
        return {}

def get_page_ads_data(access_token, page_id):
    """Fetch monetization data for a given page."""
    try:
        url = f"https://graph.facebook.com/{page_id}/monetized_data?access_token={access_token}"
        response = requests.get(url)
        data = response.json()
        return data if "data" in data else {}
    except Exception as e:
        logging.error(f"Error fetching page ads data: {e}")
        return {}

if __name__ == "__main__":
    app.run(debug=True)
