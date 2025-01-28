from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='assets', template_folder='pages')
app.secret_key = os.urandom(24)

# Environment variables
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID', '407721285698090')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET', '4775235855fcd971cfe6828ab439b4fc')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://pib-grow.vercel.app/auth/callback')

@app.route('/')
@app.route('/sign-up')
def sign_up():
    return render_template('sign-up.html', facebook_app_id=FACEBOOK_APP_ID, redirect_uri=REDIRECT_URI)

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
        return redirect(url_for('dashboard'))

    except requests.exceptions.RequestException as e:
        print("Error during token exchange:", e)
        return "An error occurred during authentication.", 500

@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('sign_up'))

    try:
        # Fetch user information
        user_response = requests.get(
            "https://graph.facebook.com/v18.0/me",
            params={"fields": "name,email", "access_token": access_token}
        )
        user_response.raise_for_status()
        user_data = user_response.json()

        # Fetch pages associated with the user
        pages_response = requests.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"fields": "name,id,access_token", "access_token": access_token}
        )
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        # Format the pages data for the template
        pages = [{
            'id': page['id'],
            'name': page['name'],
            'access_token': page['access_token']
        } for page in pages_data]

        return render_template(
            'dashboard.html',
            user_name=user_data.get('name', 'Unknown User'),
            user_email=user_data.get('email', 'Not Provided'),
            pages=pages
        )

    except requests.exceptions.RequestException as e:
        print("Error fetching data from Facebook:", e)
        return "An error occurred while fetching data from Facebook.", 500

@app.route('/api/page_metrics/<page_id>')
def get_page_metrics(page_id):
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        # Get date range from request or default to last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Format dates for the API
        since = request.args.get('since', start_date.strftime('%Y-%m-%d'))
        until = request.args.get('until', end_date.strftime('%Y-%m-%d'))

        # Fetch page insights with available metrics
        metrics = "page_impressions,page_fan_adds,page_views_total,page_post_engagements"
        insights_response = requests.get(
            f"https://graph.facebook.com/v18.0/{page_id}/insights",
            params={
                "metric": metrics,
                "period": "day",
                "since": since,
                "until": until,
                "access_token": access_token
            }
        )
        insights_response.raise_for_status()
        insights_data = insights_response.json().get('data', [])

        # Process metrics data
        processed_metrics = {
            'impressions': {
                'total': sum(value['value'] for metric in insights_data 
                    if metric['name'] == 'page_impressions' 
                    for value in metric['values']),
                'daily_data': [
                    {'date': value['end_time'][:10], 'value': value['value']}
                    for metric in insights_data
                    if metric['name'] == 'page_impressions'
                    for value in metric['values']
                ]
            },
            'new_fans': {
                'total': sum(value['value'] for metric in insights_data 
                    if metric['name'] == 'page_fan_adds' 
                    for value in metric['values']),
                'daily_data': [
                    {'date': value['end_time'][:10], 'value': value['value']}
                    for metric in insights_data
                    if metric['name'] == 'page_fan_adds'
                    for value in metric['values']
                ]
            },
            'page_views': {
                'total': sum(value['value'] for metric in insights_data 
                    if metric['name'] == 'page_views_total' 
                    for value in metric['values']),
                'daily_data': [
                    {'date': value['end_time'][:10], 'value': value['value']}
                    for metric in insights_data
                    if metric['name'] == 'page_views_total'
                    for value in metric['values']
                ]
            },
            'engagements': {
                'total': sum(value['value'] for metric in insights_data 
                    if metric['name'] == 'page_post_engagements' 
                    for value in metric['values']),
                'daily_data': [
                    {'date': value['end_time'][:10], 'value': value['value']}
                    for metric in insights_data
                    if metric['name'] == 'page_post_engagements'
                    for value in metric['values']
                ]
            }
        }

        return jsonify(processed_metrics)

    except requests.exceptions.RequestException as e:
        print(f"API request error: {str(e)}")
        return jsonify({"error": "Failed to fetch metrics"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
