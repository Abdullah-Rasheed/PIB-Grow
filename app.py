from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import requests
import os

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
        token_url = 'https://graph.facebook.com/v16.0/oauth/access_token'
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
        user_data = fetch_user_data(access_token)
        user_name = user_data.get('name', 'Unknown User')
        user_email = user_data.get('email', 'Not Provided')

        # Fetch pages and metrics
        pages_data = fetch_pages_data(access_token)
        partner_pages, total_revenue, labels, revenue_data, page_metrics, post_metrics = process_pages_data(access_token, pages_data)

        # Aggregate partner data
        partners = [{
            'name': user_name,
            'email': user_email,
            'pages': partner_pages,
            'total_revenue': f"${total_revenue:,.2f}",
            'status': 'green' if total_revenue > 50000 else 'yellow' if total_revenue > 30000 else 'red'
        }]

        performance = {
           
            'labels': labels or ["No data available"],
            'data': revenue_data or [0]
        }

        return render_template(
            'dashboard.html',
            partners=partners,
            performance=performance,
            page_metrics=page_metrics or [{"message": "No data found"}],
            post_metrics=post_metrics or [{"message": "No data found"}]
        )

    except requests.exceptions.RequestException as e:
        print("Error fetching data from Facebook:", e)
        return render_template('dashboard.html', error_message="An error occurred while fetching data from Facebook.")
    except Exception as e:
        print("Unexpected error:", e)
        return render_template('dashboard.html', error_message="An unexpected error occurred.")

# Helper functions
def fetch_user_data(access_token):
    try:
        user_url = "https://graph.facebook.com/v16.0/me"
        user_params = {"fields": "name,email", "access_token": access_token}
        user_response = requests.get(user_url, params=user_params)
        user_response.raise_for_status()
        return user_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user data: {e}")
        return {"name": "Unknown User", "email": "Not Provided"}

def fetch_pages_data(access_token):
    try:
        pages_url = "https://graph.facebook.com/v16.0/me/accounts"
        pages_params = {"fields": "name,id", "access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        return pages_response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pages data: {e}")
        return []

def process_pages_data(access_token, pages_data):
    partner_pages = []
    total_revenue = 0
    labels = []
    revenue_data = []
    page_metrics = []
    post_metrics = []

    for page in pages_data:
        page_id = page['id']
        page_name = page['name']

        # Fetch monetization revenue
        insights_url = f"https://graph.facebook.com/v16.0/{page_id}/insights"
        insights_params = {
            "metric": "estimated_revenue",
            "period": "month",
            "access_token": access_token
        }
        try:
            insights_response = requests.get(insights_url, params=insights_params)
            if insights_response.status_code == 200:
                insights_data = insights_response.json().get('data', [])
                monthly_revenue = [
                    float(entry.get('value', 0)) for entry in insights_data if 'value' in entry
                ]
                total_page_revenue = sum(monthly_revenue)
                total_revenue += total_page_revenue
                labels = [entry['title'] for entry in insights_data]
                partner_pages.append({'name': page_name, 'revenue': f"${total_page_revenue:,.2f}"})
                revenue_data.extend(monthly_revenue)
            else:
                partner_pages.append({'name': page_name, 'revenue': "Revenue not found"})
        except Exception as e:
            print(f"Error fetching revenue data for page {page_name}: {e}")
            partner_pages.append({'name': page_name, 'revenue': "No data found"})

        # Fetch page-level metrics
        try:
            page_performance_url = f"https://graph.facebook.com/v16.0/{page_id}/insights"
            page_performance_params = {
                "metric": "page_impressions,page_engaged_users,page_fans",
                "period": "day",
                "access_token": access_token
            }
            page_performance_response = requests.get(page_performance_url, params=page_performance_params)
            if page_performance_response.status_code == 200:
                page_metrics.append({
                    "page_name": page_name,
                    "metrics": page_performance_response.json().get('data', [])
                })
        except Exception as e:
            print(f"Error fetching page metrics for {page_name}: {e}")
            page_metrics.append({"page_name": page_name, "message": "No data found"})

        # Fetch post-level metrics
        try:
            posts_url = f"https://graph.facebook.com/v16.0/{page_id}/posts"
            posts_params = {"fields": "id,message,created_time", "access_token": access_token}
            posts_response = requests.get(posts_url, params=posts_params)
            posts_data = posts_response.json().get('data', [])
            for post in posts_data:
                post_id = post['id']
                post_metrics_url = f"https://graph.facebook.com/v16.0/{post_id}/insights"
                post_metrics_params = {
                    "metric": "post_impressions,post_engaged_users,post_reactions_like_total",
                    "access_token": access_token
                }
                post_metrics_response = requests.get(post_metrics_url, params=post_metrics_params)
                if post_metrics_response.status_code == 200:
                    post_metrics.append({
                        "post_id": post_id,
                        "metrics": post_metrics_response.json().get('data', [])
                    })
        except Exception as e:
            print(f"Error fetching post metrics for page {page_name}: {e}")
            post_metrics.append({"page_name": page_name, "message": "No data found"})

    return partner_pages, total_revenue, labels, revenue_data, page_metrics, post_metrics

# Serve static assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
