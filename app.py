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
    f"pages_manage_metadata,read_insights,pages_manage_ads,ads_read"
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route("/")
def dashboard():
    """Render the dashboard using Facebook API data."""
    access_token = request.args.get("access_token")
    if not access_token:
        return redirect("/auth/start")

    # Fetch user info
    user_info = get_user_info(access_token)
    if "error" in user_info:
        return render_template("error.html", error=user_info["error"])

    # Fetch pages and their insights
    pages = get_user_pages(access_token)
    for page in pages.get("data", []):
        page_id = page["id"]
        # Fetch page-level metrics
        page["insights"] = get_page_engagement(access_token, page_id) or {}
        # Fetch monetization data
        page["monetization"] = get_page_monetization_data(access_token, page_id) or {}
        # Fetch post-level metrics
        page["posts"] = get_page_posts(access_token, page_id)

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
    return response.json()


def get_user_pages(access_token):
    """Fetch the list of pages the user manages."""
    url = f"https://graph.facebook.com/me/accounts?fields=id,name,category,roles&access_token={access_token}"
    response = requests.get(url)
    return response.json()


def get_page_engagement(access_token, page_id):
    """Fetch engagement data for a given page."""
    metrics = "page_impressions,page_engaged_users,page_views_total"
    url = f"https://graph.facebook.com/{page_id}/insights?metric={metrics}&access_token={access_token}"
    response = requests.get(url)
    data = response.json()
    return data if "data" in data else {}


def get_page_monetization_data(access_token, page_id):
    """Fetch monetization data for a given page."""
    url = f"https://graph.facebook.com/{page_id}/monetized_data?access_token={access_token}"
    response = requests.get(url)
    data = response.json()
    return data if "data" in data else {}


def get_page_posts(access_token, page_id):
    """Fetch post-level metrics for a given page."""
    posts_url = f"https://graph.facebook.com/{page_id}/posts?fields=id,message,created_time,insights.metric(post_impressions,post_engaged_users)&access_token={access_token}"
    response = requests.get(posts_url)
    data = response.json()
    if "data" in data:
        for post in data["data"]:
            post["insights"] = post.get("insights", {}).get("data", [])
    return data.get("data", [])


@app.route("/data-deletion", methods=["POST"])
def data_deletion():
    """Handle Facebook data deletion requests."""
    body = request.json
    if not body or "signed_request" not in body:
        return jsonify({"error": "Invalid request"}), 400

    response = {
        "url": "https://your-app-url/",
        "confirmation_code": "123456789"
    }
    return jsonify(response)


# Expose the `app` object for deployment
if __name__ == "__main__":
    app.run(debug=True)
