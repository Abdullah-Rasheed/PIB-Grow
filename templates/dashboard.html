import os
from flask import Flask, request, jsonify, redirect, render_template
from flask_cors import CORS
import requests
import logging
from dotenv import load_dotenv

# Initialize the Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)

# Load environment variables from a .env file
load_dotenv()

# Facebook App credentials
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "https://your-app-url/auth/callback")

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
    """Render the dashboard using Facebook API data."""
    access_token = request.args.get("access_token")
    if not access_token:
        return redirect("/auth/start")

    user_info = get_user_info(access_token)
    if "error" in user_info:
        return render_template("error.html", error=user_info["error"])

    # Log the access token and user data
    logging.debug(f"Access Token: {access_token}")
    logging.debug(f"User Info: {user_info}")

    pages = get_user_pages(access_token)
    logging.debug(f"Pages Data: {pages}")

    # Add dummy data or fallback for missing insights/monetization
    for page in pages.get("data", []):
        page_id = page["id"]
        page["insights"] = get_page_engagement(access_token, page_id) or get_dummy_insights()
        page["monetization"] = get_page_ads_data(access_token, page_id) or get_dummy_monetization()
        page["posts"] = get_page_posts(access_token, page_id) or get_dummy_posts()

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
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch user info: {response.text}")
        return {"name": "Guest", "id": "dummy_user_id"}


def get_user_pages(access_token):
    """Fetch the list of pages the user manages or return dummy data if API fails."""
    url = f"https://graph.facebook.com/me/accounts?fields=id,name,category,roles&access_token={access_token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch user pages: {response.text}")
        return {"data": [get_dummy_page()]}


def get_page_engagement(access_token, page_id):
    """Fetch engagement data for a given page."""
    metrics = "page_impressions,page_engaged_users,page_fan_adds"
    url = f"https://graph.facebook.com/{page_id}/insights?metric={metrics}&access_token={access_token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch engagement data for page {page_id}: {response.text}")
        return {}


def get_page_ads_data(access_token, page_id):
    """Fetch monetization data for a given page."""
    url = f"https://graph.facebook.com/{page_id}/monetized_data?access_token={access_token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch monetization data for page {page_id}: {response.text}")
        return {}


def get_page_posts(access_token, page_id):
    """Fetch recent posts for a given page."""
    url = f"https://graph.facebook.com/{page_id}/posts?fields=id,message,insights&access_token={access_token}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Failed to fetch posts for page {page_id}: {response.text}")
        return {}


def get_dummy_page():
    """Return dummy page data."""
    return {
        "id": "dummy_page_id",
        "name": "Dummy Page",
        "category": "Community",
        "roles": ["ADMIN"],
    }


def get_dummy_insights():
    """Return dummy insights data."""
    return {
        "data": [
            {"name": "page_impressions", "values": [{"value": 1000}]},
            {"name": "page_engaged_users", "values": [{"value": 200}]},
        ]
    }


def get_dummy_monetization():
    """Return dummy monetization data."""
    return {
        "data": [{"name": "revenue", "value": 50.0}],
    }


def get_dummy_posts():
    """Return dummy posts data."""
    return [
        {
            "id": "dummy_post_1",
            "message": "Dummy Post Message",
            "insights": [
                {"name": "post_impressions", "values": [{"value": 500}]},
                {"name": "post_engaged_users", "values": [{"value": 50}]},
            ],
        }
    ]


@app.route("/data-deletion", methods=["POST"])
def data_deletion():
    """Handle Facebook data deletion requests."""
    body = request.json
    if not body or "signed_request" not in body:
        return jsonify({"error": "Invalid request"}), 400

    response = {
        "url": "https://your-app-url/",
        "confirmation_code": "123456789",
    }
    return jsonify(response)


# Expose the `app` object for deployment
if __name__ == "__main__":
    app.run(debug=True)
