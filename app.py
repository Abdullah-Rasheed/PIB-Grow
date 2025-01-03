import os
from flask import Flask, request, jsonify, redirect, render_template
from flask_cors import CORS
import requests
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

# Facebook OAuth URL configuration with updated permissions
FB_AUTH_URL = (
    f"https://www.facebook.com/v17.0/dialog/oauth?client_id={FACEBOOK_APP_ID}"
    f"&redirect_uri={REDIRECT_URI}&scope=ads_management,pages_read_engagement,"
    f"pages_show_list,pages_manage_ads,pages_manage_posts,pages_manage_metadata,pages_messaging"
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
    for page in pages.get("data", []):
        page_id = page["id"]
        page["insights"] = get_page_engagement(access_token, page_id)
        page["monetization"] = get_page_monetization(access_token, page_id)

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
    metrics = "page_impressions,page_engaged_users,page_fan_adds,page_views,post_engagement"
    url = f"https://graph.facebook.com/{page_id}/insights?metric={metrics}&access_token={access_token}"
    response = requests.get(url)
    return response.json()


def get_page_monetization(access_token, page_id):
    """Fetch monetization data for a given page."""
    url = f"https://graph.facebook.com/{page_id}/monetized_data?access_token={access_token}"
    response = requests.get(url)
    return response.json()


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
