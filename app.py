from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import requests
import os
import traceback  # For detailed error logging

app = Flask(__name__, static_folder='assets', template_folder='pages')
app.secret_key = os.urandom(24)  # Secure session key

# Environment variables
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID', '407721285698090')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET', '4775235855fcd971cfe6828ab439b4fc')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://pib-grow.vercel.app/auth/callback')

# 🔹 Sign-Up Page
@app.route('/')
@app.route('/sign-up')
def sign_up():
    return render_template('sign-up.html', facebook_app_id=FACEBOOK_APP_ID, redirect_uri=REDIRECT_URI)

# 🔹 Facebook OAuth Callback
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
        print("✅ Access Token Retrieved:", access_token)

        return redirect(url_for('dashboard'))

    except requests.exceptions.RequestException as e:
        print("❌ Error during token exchange:", str(e))
        return "An error occurred during authentication.", 500

# 🔹 Dashboard Route
@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        print("⚠️ User not authenticated - Redirecting to sign-up")
        return redirect(url_for('sign_up'))

    try:
        # Fetch user data
        user_response = requests.get(
            "https://graph.facebook.com/v18.0/me",
            params={"fields": "name,email", "access_token": access_token}
        )
        user_response.raise_for_status()
        user_data = user_response.json()

        user_name = user_data.get('name', 'Unknown User')
        user_email = user_data.get('email', 'Not Provided')

        # Fetch pages
        pages_response = requests.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"fields": "name,id", "access_token": access_token}
        )
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        partner_pages = []
        total_engagement = 0
        engagement_data = []
        labels = []

        for page in pages_data:
            page_id, page_name = page.get('id'), page.get('name', 'Unknown Page')

            # Fetch page insights
            insights_response = requests.get(
                f"https://graph.facebook.com/v18.0/{page_id}/insights",
                params={"metric": "page_engaged_users", "period": "day", "access_token": access_token}
            )

            if insights_response.status_code == 200:
                insights_data = insights_response.json().get('data', [])
                daily_engagement = sum(
                    float(entry.get('value', 0))
                    for metric in insights_data
                    for entry in metric.get('values', [])
                )
                total_engagement += daily_engagement
                labels.extend([
                    entry.get('end_time', 'No Date')[:10]
                    for metric in insights_data
                    for entry in metric.get('values', [])
                ])
                engagement_data.append(daily_engagement)
            else:
                daily_engagement = 0  # Set engagement to zero if request fails

            partner_pages.append({'name': page_name, 'engagement': daily_engagement, 'status': 'Processed' if daily_engagement > 0 else 'Pending'})

        partners = [{
            'name': user_name,
            'email': user_email,
            'pages': partner_pages,
            'total_engagement': total_engagement,
            'status': 'active' if total_engagement > 0 else 'inactive'
        }]

        performance = {'labels': labels, 'data': engagement_data}

        return render_template('dashboard.html', partners=partners, performance=performance, partner=partners[0])

    except requests.exceptions.RequestException as e:
        print("❌ API Request Error:", str(e))
        return "An error occurred while fetching data from Facebook.", 500
    except Exception as e:
        print("❌ Unexpected Error:", traceback.format_exc())
        return "An unexpected error occurred.", 500

# 🔹 Fetch Page Metrics API
@app.route('/api/fetch_page_metrics/<page_name>')
def fetch_page_metrics(page_name):
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({"error": "User not authenticated"}), 401

    try:
        # Fetch pages
        pages_response = requests.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"fields": "name,id", "access_token": access_token}
        )
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        page_id = next((page['id'] for page in pages_data if page['name'].lower() == page_name.lower()), None)
        if not page_id:
            return jsonify({"error": f"Page '{page_name}' not found."}), 404

        # Fetch insights
        insights_response = requests.get(
            f"https://graph.facebook.com/v18.0/{page_id}/insights",
            params={"metric": "page_impressions,page_post_engagements,page_fans_add", "period": "day", "access_token": access_token}
        )
        insights_response.raise_for_status()
        insights_data = insights_response.json().get('data', [])

        # Process metrics
        page_metrics = {
            'reach': sum(metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_impressions'),
            'engagement': sum(metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_post_engagements'),
            'followers': next((metric['values'][0]['value'] for metric in insights_data if metric['name'] == 'page_fans_add'), 0)
        }

        # Fetch posts
        posts_response = requests.get(
            f"https://graph.facebook.com/v18.0/{page_id}/posts",
            params={"fields": "id,message,created_time", "access_token": access_token, "limit": 10}
        )
        posts_response.raise_for_status()
        posts_data = posts_response.json().get('data', [])

        return jsonify({
            "page_metrics": page_metrics,
            "posts": [{"id": post['id'], "message": post.get('message', 'No message')[:50], "date": post['created_time'][:10]} for post in posts_data]
        })

    except requests.exceptions.RequestException as e:
        print("❌ API Error:", str(e))
        return jsonify({"error": "Failed to fetch metrics from Facebook"}), 500
    except Exception as e:
        print("❌ Unexpected Error:", traceback.format_exc())
        return jsonify({"error": "An unexpected error occurred"}), 500

# 🔹 Serve Static Assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

# 🔹 Run Flask App
if __name__ == '__main__':
    app.run(debug=True)
