from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import requests
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, static_folder='assets', template_folder='pages')
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=7)  # Set session lifetime

# Environment variables
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID', '407721285698090')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET', '4775235855fcd971cfe6828ab439b4fc')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://pib-grow.vercel.app/auth/callback')

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = session.get('access_token')
        if not access_token:
            return redirect(url_for('sign_up'))
        
        # Verify token validity
        try:
            debug_url = 'https://graph.facebook.com/debug_token'
            debug_params = {
                'input_token': access_token,
                'access_token': f"{FACEBOOK_APP_ID}|{FACEBOOK_APP_SECRET}"
            }
            debug_response = requests.get(debug_url, params=debug_params)
            debug_data = debug_response.json()
            
            if not debug_data.get('data', {}).get('is_valid', False):
                session.clear()
                return redirect(url_for('sign_up'))
                
        except requests.exceptions.RequestException:
            session.clear()
            return redirect(url_for('sign_up'))
            
        return f(*args, **kwargs)
    return decorated_function

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
        token_url = 'https://graph.facebook.com/v22.0/oauth/access_token'
        token_params = {
            'client_id': FACEBOOK_APP_ID,
            'redirect_uri': REDIRECT_URI,
            'client_secret': FACEBOOK_APP_SECRET,
            'code': code,
        }
        token_response = requests.get(token_url, params=token_params)
        token_response.raise_for_status()

        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            return "Error: Failed to retrieve access token.", 500

        # Make session permanent and store token
        session.permanent = True
        session['access_token'] = access_token
        
        # Store token expiration if provided
        if 'expires_in' in token_data:
            session['token_expiration'] = datetime.now() + timedelta(seconds=token_data['expires_in'])

        return redirect(url_for('dashboard'))

    except requests.exceptions.RequestException as e:
        print("Error during token exchange:", e)
        return "An error occurred during authentication.", 500
        
@app.route('/dashboard')
@login_required
def dashboard():
    access_token = session.get('access_token')
    try:
        # Fetch user information
        user_url = "https://graph.facebook.com/v22.0/me"
        user_params = {
            "fields": "name,email",
            "access_token": access_token
        }
        user_response = requests.get(user_url, params=user_params)
        user_response.raise_for_status()
        user_data = user_response.json()
        user_name = user_data.get('name', 'Unknown User')
        user_email = user_data.get('email', 'Not Provided')

        # Fetch pages with extended permissions
        pages_url = "https://graph.facebook.com/v22.0/me/accounts"
        pages_params = {
            "fields": "name,id,access_token",  # Added access_token to fields
            "access_token": access_token
        }
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        # Store page tokens in session
        session['page_tokens'] = {
            page['id']: page['access_token'] 
            for page in pages_data
        }

        partner_pages = []
        total_engagement = 0
        engagement_data = []
        labels = []

        for page in pages_data:
            page_id = page['id']
            page_name = page['name']
            page_token = page['access_token']  # Use page-specific token

            # Fetch page insights using page token
            insights_url = f"https://graph.facebook.com/v22.0/{page_id}/insights"
            insights_params = {
                "metric": "page_impressions,page_post_engagements,page_fans",  # Added metrics
                "period": "day",
                "access_token": page_token
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

                labels.extend([
                    entry.get('end_time', 'No Date')[:10] 
                    for metric in insights_data 
                    for entry in metric.get('values', [])
                ])

                # Fetch detailed metrics (reach, engagement, followers)
                def get_metric_value(name):
                    metric = next((m for m in insights_data if m['name'] == name), None)
                    if metric and metric.get('values'):
                        return metric['values'][0].get('value', 0)
                    return 0

                page_metrics = {
                    "reach": get_metric_value("page_impressions"),
                    "engagement": get_metric_value("page_post_engagements"),
                    "followers": get_metric_value("page_fans")
                }

                partner_pages.append({
                    'name': page_name,
                    'id': page_id,
                    'engagement': total_page_engagement,
                    'status': 'Processed',
                    'metrics': page_metrics  # Add detailed metrics
                })
                engagement_data.extend(daily_engagement)
            else:
                partner_pages.append({
                    'name': page_name,
                    'id': page_id,
                    'engagement': 0,
                    'status': 'Pending',
                    'metrics': {
                        "reach": 0,
                        "engagement": 0,
                        "followers": 0
                    }
                })

        partners = [{
            'name': user_name,
            'email': user_email,
            'pages': partner_pages,
            'total_engagement': total_engagement,
            'status': 'active' if total_engagement > 0 else 'inactive'
        }]

        performance = {
            'labels': labels,
            'data': engagement_data
        }

        return render_template(
            'dashboard.html',
            partners=partners,
            performance=performance,
            partner=partners[0]
        )

    except requests.exceptions.RequestException as e:
        print("Error fetching data from Facebook:", e)
        session.clear()  # Clear session on API error
        return redirect(url_for('sign_up'))
    except Exception as e:
        print("Unexpected error:", e)
        return "An unexpected error occurred.", 500


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('sign_up'))

if __name__ == '__main__':
    app.run(debug=True)
