import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests

# Initialize the Flask app
app = Flask(__name__)
CORS(app)

# Load environment variables from a .env file
from dotenv import load_dotenv
load_dotenv()

# Facebook App credentials (replace these with your app details from Facebook Developer portal)
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/auth/callback")

# Facebook OAuth URL configuration
FB_AUTH_URL = (
    f"https://www.facebook.com/v17.0/dialog/oauth?client_id={FACEBOOK_APP_ID}"
    f"&redirect_uri={REDIRECT_URI}&scope=pages_show_list,pages_read_monetization_insights"
)

@app.route("/auth/start", methods=["GET"])
def start_auth():
    """Step 1: Redirect users to Facebook login."""
    return redirect(FB_AUTH_URL)

@app.route("/auth/callback", methods=["GET"])
def auth_callback():
    """Step 2: Handle the callback and exchange code for access token."""
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
        return jsonify({"access_token": data["access_token"]})
    else:
        return jsonify({"error": data.get("error", "Unknown error")}), 400

@app.route("/auth/validate", methods=["GET"])
def validate_token():
    """Step 3: Validate the access token."""
    access_token = request.args.get("access_token")
    if not access_token:
        return jsonify({"error": "Access token is required"}), 400

    debug_url = f"https://graph.facebook.com/debug_token"
    params = {
        "input_token": access_token,
        "access_token": f"{FACEBOOK_APP_ID}|{FACEBOOK_APP_SECRET}",
    }
    response = requests.get(debug_url, params=params)
    data = response.json()

    return jsonify(data)

# Data Deletion Endpoint
@app.route("/data-deletion", methods=["POST"])
def data_deletion():
    """Handle data deletion requests."""
    user_email = request.json.get("email")
    if not user_email:
        return jsonify({"error": "Email is required"}), 400

    # Simulating data deletion
    return jsonify({"message": "Data deletion request successful for email: " + user_email}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
