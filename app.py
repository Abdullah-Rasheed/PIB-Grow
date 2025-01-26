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
    return _fetch_partner_data_and_render('dashboard.html')

# Route: Partners
@app.route('/partners')
def partners():
    return _fetch_partner_data_and_render('partners.html')

# Helper function to fetch partner data and render a given template
def _fetch_partner_data_and_render(template_name):
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('sign_up'))

    try:
        # Fetch user information
        user_url = "https://graph.facebook.com/v16.0/me"
        user_params = {"fields": "name,email", "access_token": access_token}
        user_response = requests.get(user_url, params=user_params)
        user_response.raise_for_status()
        user_data = user_response.json()
        user_name = user_data.get('name', 'Unknown User')
        user_email = user_data.get('email', 'Not Provided')

        # Fetch pages associated with the user
        pages_url = "https://graph.facebook.com/v16.0/me/accounts"
        pages_params = {"fields": "name,id", "access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        # Prepare partner data
        partner_pages = []
        total_revenue = 0
        revenue_data = []
        labels = []  # For monthly labels
        for page in pages_data:
            page_id = page['id']
            page_name = page['name']

            # Fetch monetization revenue for the page
            insights_url = f"https://graph.facebook.com/v16.0/{page_id}/insights"
            insights_params = {
                "metric": "estimated_revenue",
                "period": "month",
                "access_token": access_token
            }
            insights_response = requests.get(insights_url, params=insights_params)
            
            if insights_response.status_code == 200:
                insights_data = insights_response.json().get('data', [])
                monthly_revenue = [
                    float(entry['value']) for entry in insights_data if 'value' in entry
                ]
                total_page_revenue = sum(monthly_revenue)
                total_revenue += total_page_revenue
                labels = [entry['title'] for entry in insights_data]  # Update labels dynamically
                partner_pages.append({'name': page_name, 'revenue': f"${total_page_revenue:,.2f}"})
                revenue_data.extend(monthly_revenue)
            else:
                partner_pages.append({'name': page_name, 'revenue': "Revenue not found"})

        # Aggregate partner data
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
            template_name,
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

# Serve static assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
