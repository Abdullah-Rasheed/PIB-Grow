import os
import requests
from flask import Flask, render_template, redirect, request, session, url_for, jsonify

app = Flask(__name__, static_folder='assets', template_folder='pages')

# Set a secure random key
app.secret_key = os.urandom(24)

# Environment variables for Facebook app
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')


# Routes
@app.route('/')
@app.route('/sign-up')
def sign_up():
    return render_template('sign-up.html')


@app.route('/login/facebook')
def login_facebook():
    facebook_auth_url = (
        f"https://www.facebook.com/v16.0/dialog/oauth?"
        f"client_id={FACEBOOK_APP_ID}&redirect_uri={REDIRECT_URI}&scope=pages_show_list"
    )
    return redirect(facebook_auth_url)


@app.route('/auth/callback')
def facebook_callback():
    code = request.args.get('code')
    if not code:
        return "Authorization failed.", 400

    # Exchange code for an access token
    token_url = "https://graph.facebook.com/v16.0/oauth/access_token"
    token_params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "client_secret": FACEBOOK_APP_SECRET,
        "code": code,
    }
    token_response = requests.get(token_url, params=token_params)
    if token_response.status_code != 200:
        return f"Error exchanging token: {token_response.json()}", 400
    access_token = token_response.json().get('access_token')

    # Save access token in session
    session['access_token'] = access_token

    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('sign_up'))

    # Fetch user data
    user_url = "https://graph.facebook.com/v16.0/me"
    user_params = {"fields": "name", "access_token": access_token}
    user_response = requests.get(user_url, params=user_params)
    if user_response.status_code != 200:
        return f"Error fetching user data: {user_response.json()}", 400
    user_data = user_response.json()
    user_name = user_data.get('name', 'Unknown User')

    # Fetch pages data
    pages_url = "https://graph.facebook.com/v16.0/me/accounts"
    pages_params = {"fields": "name", "access_token": access_token}
    pages_response = requests.get(pages_url, params=pages_params)
    if pages_response.status_code != 200:
        return f"Error fetching pages: {pages_response.json()}", 400
    pages_data = pages_response.json().get('data', [])

    # Mock revenue data
    for page in pages_data:
        page['revenue'] = f"${10000 + hash(page['id']) % 5000}"  # Randomized mock revenue

    # Calculate total revenue
    total_revenue = sum(
        int(page['revenue'].strip('$').replace(',', '')) for page in pages_data
    )

    # Pass data to dashboard.html
    return render_template('dashboard.html', user_name=user_name, pages=pages_data, total_revenue=f"${total_revenue:,}")


@app.route('/partners')
def partners():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('sign_up'))

    # Fetch the business name
    user_url = "https://graph.facebook.com/v16.0/me"
    user_params = {"fields": "name", "access_token": access_token}
    user_response = requests.get(user_url, params=user_params)
    if user_response.status_code != 200:
        return f"Error fetching user data: {user_response.json()}", 400
    user_data = user_response.json()
    partner_name = user_data.get('name', 'Unknown Partner')

    # Fetch pages
    pages_url = "https://graph.facebook.com/v16.0/me/accounts"
    pages_params = {"fields": "name", "access_token": access_token}
    pages_response = requests.get(pages_url, params=pages_params)
    if pages_response.status_code != 200:
        return f"Error fetching pages: {pages_response.json()}", 400
    pages_data = pages_response.json().get('data', [])

    # Mock revenue data
    for page in pages_data:
        page['revenue'] = f"${10000 + hash(page['id']) % 5000}"  # Randomized mock revenue

    # Calculate total revenue
    total_revenue = sum(
        int(page['revenue'].strip('$').replace(',', '')) for page in pages_data
    )

    # Render the partners page with data
    return render_template('dashboard.html', partner_name=partner_name, pages=pages_data, total_revenue=f"${total_revenue:,}")


# Serve static assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    app.run(debug=True)
