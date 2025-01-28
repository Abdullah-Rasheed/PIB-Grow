from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
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
        token_url = 'https://graph.facebook.com/v22.0/oauth/access_token'
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
        user_url = "https://graph.facebook.com/v22.0/me"
        user_params = {"fields": "name,email", "access_token": access_token}
        user_response = requests.get(user_url, params=user_params)
        user_response.raise_for_status()
        user_data = user_response.json()
        user_name = user_data.get('name', 'Unknown User')
        user_email = user_data.get('email', 'Not Provided')

        # Fetch pages associated with the user
        pages_url = "https://graph.facebook.com/v22.0/me/accounts"
        pages_params = {"fields": "name,id", "access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        partner_pages = []
        total_revenue = 0
        revenue_data = []
        labels = []  # For monthly labels

        for page in pages_data:
            page_id = page.get('id')
            page_name = page.get('name', 'Unknown Page')

            # Fetch monetization revenue for the page
            insights_url = f"https://graph.facebook.com/v22.0/{page_id}/insights"
            insights_params = {
                "metric": "estimated_revenue",
                "period": "month",
                "access_token": access_token
            }
            insights_response = requests.get(insights_url, params=insights_params)

            if insights_response.status_code == 200:
                insights_data = insights_response.json().get('data', [])
                monthly_revenue = [
                    float(entry.get('value', 0)) for entry in insights_data if 'value' in entry
                ]
                total_page_revenue = sum(monthly_revenue)
                total_revenue += total_page_revenue

                labels.extend([entry.get('title', 'No Title') for entry in insights_data])
                partner_pages.append({'name': page_name, 'revenue': f"${total_page_revenue:,.2f}"})
                revenue_data.extend(monthly_revenue)
            else:
                partner_pages.append({'name': page_name, 'revenue': "Revenue not found"})

        partners = [{
            'name': user_name,
            'email': user_email,
            'pages': partner_pages,
            'total_revenue': f"${total_revenue:,.2f}",
            'status': 'green' if total_revenue > 50000 else 'yellow' if total_revenue > 30000 else 'red'
        }]

        performance = {
            'labels': labels,
            'data': revenue_data
        }

        return render_template(
            'dashboard.html',
            partners=partners,
            performance=performance,
            partner=partners[0]
        )

    except requests.exceptions.RequestException as e:
        print("Error fetching data from Facebook:", e)
        return "An error occurred while fetching data from Facebook.", 500
    except Exception as e:
        print("Unexpected error:", e)
        return "An unexpected error occurred.", 500

# Route: Fetch Page Metrics
@app.route('/api/fetch_page_metrics/<page_name>', methods=['GET'])
def fetch_page_metrics(page_name):
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({"error": "User not authenticated."}), 401

    try:
        pages_url = "https://graph.facebook.com/v22.0/me/accounts"
        pages_params = {"fields": "name,id", "access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        page_id = next((page['id'] for page in pages_data if page['name'] == page_name), None)
        if not page_id:
            return jsonify({"error": "Page not found."}), 404

        page_metrics_url = f"https://graph.facebook.com/v22.0/{page_id}/insights"
        page_metrics_params = {
            "metric": "page_impressions,page_fans,page_views_total",
            "period": "day",
            "access_token": access_token
        }
        page_metrics_response = requests.get(page_metrics_url, params=page_metrics_params)
        page_metrics_response.raise_for_status()
        page_metrics_data = page_metrics_response.json().get('data', [])

        posts_url = f"https://graph.facebook.com/v22.0/{page_id}/posts"
        posts_params = {
            "fields": "id,message,insights.metric(post_impressions,post_engaged_users)",
            "access_token": access_token
        }
        posts_response = requests.get(posts_url, params=posts_params)
        posts_response.raise_for_status()
        posts_data = posts_response.json().get('data', [])

        page_metrics = {
            'reach': next((metric['values'][0]['value'] for metric in page_metrics_data if metric['name'] == 'page_impressions'), 0),
            'engagement': next((metric['values'][0]['value'] for metric in page_metrics_data if metric['name'] == 'page_engaged_users'), 0),
            'likes': next((metric['values'][0]['value'] for metric in page_metrics_data if metric['name'] == 'page_fans'), 0),
            'views': next((metric['values'][0]['value'] for metric in page_metrics_data if metric['name'] == 'page_views_total'), 0),
        }

        post_metrics = {
            'labels': [post['message'][:20] + '...' if 'message' in post else 'No Title' for post in posts_data],
            'values': [
                next((insight['values'][0]['value'] for insight in post['insights']['data'] if insight['name'] == 'post_engaged_users'), 0)
                for post in posts_data
            ]
        }

        revenue_data = {
            'labels': [f"Month {i+1}" for i in range(len(post_metrics['values']))],
            'values': post_metrics['values']
        }

        return jsonify({
            "page_metrics": page_metrics,
            "post_metrics": post_metrics,
            "revenue_data": revenue_data
        })

    except requests.exceptions.RequestException as e:
        print("Error fetching page metrics:", e)
        return jsonify({"error": "An error occurred while fetching metrics."}), 500
    except Exception as e:
        print("Unexpected error:", e)
        return jsonify({"error": "An unexpected error occurred."}), 500

# Serve static assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
