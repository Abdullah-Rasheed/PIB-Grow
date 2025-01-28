from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='assets', template_folder='pages')
app.secret_key = os.urandom(24)  # Ensure secret key is set for session management

# Environment variables
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID', '407721285698090')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET', '4775235855fcd971cfe6828ab439b4fc')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://pib-grow.vercel.app/auth/callback')

# Route: Sign-Up
@app.route('/')
@app.route('/sign-up')
def sign_up():
    return render_template('sign-up.html', facebook_app_id=FACEBOOK_APP_ID, redirect_uri=REDIRECT_URI)

# Route: Facebook OAuth Callback
@app.route('/auth/callback')
def facebook_callback():
    code = request.args.get('code')
    if not code:
        return "Error: Authorization code not found.", 400

    try:
        # Exchange code for access token
        token_url = 'https://graph.facebook.com/v18.0/oauth/access_token'
        token_params = {
            'client_id': FACEBOOK_APP_ID,
            'redirect_uri': REDIRECT_URI,
            'client_secret': FACEBOOK_APP_SECRET,
            'code': code,
        }
        token_response = requests.get(token_url, params=token_params)
        token_response.raise_for_status()

        access_token = token_response.json().get('access_token')
        if not access_token:
            return "Error: Failed to retrieve access token.", 500

        session['access_token'] = access_token
        print("Access token successfully retrieved:", access_token)  # Debug log

        return redirect(url_for('dashboard'))

    except requests.exceptions.RequestException as e:
        print("Error during token exchange:", e)
        return "An error occurred during authentication.", 500

# Route: Dashboard
@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('sign_up'))

    try:
        # Fetch user information
        user_url = "https://graph.facebook.com/v18.0/me"
        user_params = {"fields": "name,email", "access_token": access_token}
        user_response = requests.get(user_url, params=user_params)
        user_response.raise_for_status()
        user_data = user_response.json()
        user_name = user_data.get('name', 'Unknown User')
        user_email = user_data.get('email', 'Not Provided')

        # Fetch pages associated with the user
        pages_url = "https://graph.facebook.com/v18.0/me/accounts"
        pages_params = {"fields": "name,id", "access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        session['pages'] = pages_data  # Store pages in session for future use

        return render_template('dashboard.html', user_name=user_name, user_email=user_email, pages=pages_data)

    except requests.exceptions.RequestException as e:
        print("Error fetching data from Facebook:", e)
        return "An error occurred while fetching data from Facebook.", 500
    except Exception as e:
        print("Unexpected error:", e)
        return "An unexpected error occurred.", 500

# Route: Select Page and Store in Session
@app.route('/select_page', methods=['POST'])
def select_page():
    page_id = request.form.get('page_id')
    if not page_id:
        return jsonify({"error": "No page ID provided."}), 400

    session['selected_page_id'] = page_id
    print("Selected Page ID:", page_id)  # Debug log
    return redirect(url_for('fetch_page_metrics'))

# Route: Fetch Page Metrics
@app.route('/fetch_page_metrics')
def fetch_page_metrics():
    access_token = session.get('access_token')
    page_id = session.get('selected_page_id')

    if not access_token:
        return jsonify({"error": "User not authenticated."}), 401

    if not page_id:
        return jsonify({"error": "No page selected."}), 400

    try:
        # Fetch insights for the selected page
        insights_url = f"https://graph.facebook.com/v18.0/{page_id}/insights"
        insights_params = {
            "metric": "page_engaged_users,page_impressions,page_fans_add",
            "period": "day",
            "access_token": access_token
        }
        insights_response = requests.get(insights_url, params=insights_params)
        insights_response.raise_for_status()
        insights_data = insights_response.json().get('data', [])

        # Process insights data
        page_metrics = {
            'engaged_users': sum(metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_engaged_users'),
            'impressions': sum(metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_impressions'),
            'new_followers': sum(metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_fans_add')
        }

        # Fetch recent posts
        posts_url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
        posts_params = {"fields": "id,message,created_time", "access_token": access_token, "limit": 5}
        posts_response = requests.get(posts_url, params=posts_params)
        posts_response.raise_for_status()
        posts_data = posts_response.json().get('data', [])

        posts = [
            {
                "id": post['id'],
                "message": post.get('message', 'No message'),
                "date": post['created_time'][:10]
            } for post in posts_data
        ]

        return render_template('metrics.html', page_metrics=page_metrics, posts=posts)

    except requests.exceptions.RequestException as e:
        print("Error fetching page metrics:", e)
        return "An error occurred while fetching page metrics.", 500
    except Exception as e:
        print("Unexpected error:", e)
        return "An unexpected error occurred.", 500

# Serve static assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
