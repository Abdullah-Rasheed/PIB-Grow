from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, make_response
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='assets', template_folder='pages')

# Environment variables
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID', '407721285698090')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET', '4775235855fcd971cfe6828ab439b4fc')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://pib-grow.vercel.app/auth/callback')

# Route: Sign-Up (Login Page)
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

        print("✅ Access Token Retrieved:", access_token)  # Debugging log

        # Store access token in a secure HTTP-only cookie
        response = make_response(redirect(url_for('dashboard')))
        response.set_cookie('fb_access_token', access_token, httponly=True, secure=True, max_age=3600)  # 1-hour expiration
        return response

    except requests.exceptions.RequestException as e:
        print("❌ Error during token exchange:", e)
        return "An error occurred during authentication.", 500

# Route: Dashboard
@app.route('/dashboard')
def dashboard():
    access_token = request.cookies.get('fb_access_token')

    if not access_token:
        print("❌ User Not Authenticated - Redirecting to Login...")
        return redirect(url_for('sign_up'))

    try:
        # Fetch user information
        user_url = "https://graph.facebook.com/v18.0/me"
        user_params = {"fields": "name,email", "access_token": access_token}
        user_response = requests.get(user_url, params=user_params)
        user_response.raise_for_status()
        user_data = user_response.json()

        print("✅ User Data:", user_data)  # Debugging log

        # Fetch pages associated with the user
        pages_url = "https://graph.facebook.com/v18.0/me/accounts"
        pages_params = {"fields": "name,id", "access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        partner_pages = []
        total_engagement = 0
        labels = []
        engagement_data = []

        for page in pages_data:
            page_id = page.get('id')
            page_name = page.get('name', 'Unknown Page')

            # Fetch page insights
            insights_url = f"https://graph.facebook.com/v18.0/{page_id}/insights"
            insights_params = {
                "metric": "page_engaged_users",
                "period": "day",
                "access_token": access_token
            }
            insights_response = requests.get(insights_url, params=insights_params)

            if insights_response.status_code == 200:
                insights_data = insights_response.json().get('data', [])
                daily_engagement = [
                    float(entry.get('value', 0)) 
                    for metric in insights_data 
                    for entry in metric.get('values', [])
                ]
                total_page_engagement = sum(daily_engagement)
                total_engagement += total_page_engagement

                labels.extend([entry.get('end_time', 'No Date')[:10] 
                    for metric in insights_data 
                    for entry in metric.get('values', [])])
                
                partner_pages.append({
                    'name': page_name, 
                    'engagement': total_page_engagement,
                    'status': 'Processed'
                })
                engagement_data.extend(daily_engagement)
            else:
                partner_pages.append({
                    'name': page_name, 
                    'engagement': 0,
                    'status': 'Pending'
                })

        partners = [{
            'name': user_data.get('name', 'Unknown User'),
            'email': user_data.get('email', 'Not Provided'),
            'pages': partner_pages,
            'total_engagement': total_engagement,
            'status': 'active' if total_engagement > 0 else 'inactive'
        }]

        performance = {
            'labels': labels,
            'data': engagement_data
        }

        return render_template('dashboard.html', partners=partners, performance=performance)

    except requests.exceptions.RequestException as e:
        print("❌ Error fetching data from Facebook:", e)
        return "An error occurred while fetching data from Facebook.", 500

# API: Fetch Page Metrics
@app.route('/api/fetch_page_metrics/<page_name>')
def fetch_page_metrics(page_name):
    access_token = request.cookies.get('fb_access_token')

    if not access_token:
        return jsonify({"error": "User not authenticated"}), 401

    try:
        # Get date range
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))

        # Fetch pages
        pages_response = requests.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"fields": "name,id", "access_token": access_token}
        )
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        # Get page ID
        page_id = next((page['id'] for page in pages_data if page['name'].lower() == page_name.lower()), None)
        if not page_id:
            return jsonify({"error": "Page not found"}), 404

        # Fetch page insights
        insights_response = requests.get(
            f"https://graph.facebook.com/v18.0/{page_id}/insights",
            params={
                "metric": "page_impressions,page_post_engagements,page_fans_add",
                "period": "day",
                "since": start_date,
                "until": end_date,
                "access_token": access_token
            }
        )
        insights_response.raise_for_status()
        insights_data = insights_response.json().get('data', [])

        page_metrics = {
            'reach': sum(metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_impressions'),
            'engagement': sum(metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_post_engagements'),
            'followers': next((metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_fans_add'), 0)
        }

        return jsonify({"page_metrics": page_metrics})

    except requests.exceptions.RequestException as e:
        print("❌ API request error:", e)
        return jsonify({"error": "Failed to fetch metrics from Facebook"}), 500

# Serve static assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
