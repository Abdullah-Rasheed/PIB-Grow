from flask import Flask, render_template, request, redirect, url_for, session
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
        # Fetch user and partner information
        user_url = "https://graph.facebook.com/v16.0/me"
        user_params = {"fields": "name,email", "access_token": access_token}
        user_response = requests.get(user_url, params=user_params)
        user_response.raise_for_status()
        user_data = user_response.json()
        user_name = user_data.get('name', 'Unknown User')
        user_email = user_data.get('email', 'Not Provided')

        pages_url = "https://graph.facebook.com/v16.0/me/accounts"
        pages_params = {"fields": "name,id", "access_token": access_token}
        pages_response = requests.get(pages_url, params=pages_params)
        pages_response.raise_for_status()
        pages_data = pages_response.json().get('data', [])

        partner_pages = []
        total_revenue = 0
        revenue_growth_percentage = 10  # Example growth percentage for this month
        growth_chart_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May']  # Example months
        growth_chart_data = []  # Example revenue data per month
        monthly_growth = 1.1  # Example monthly growth factor

        for page in pages_data:
            page_revenue = 10000 + hash(page['id']) % 5000  # Mock revenue generation
            total_revenue += page_revenue
            partner_pages.append({'name': page['name'], 'revenue': f"${page_revenue:,}"})
            growth_chart_data.append(page_revenue * monthly_growth)  # Mock growth data

        partners = [{
            'name': user_name,
            'email': user_email,
            'pages': partner_pages,
            'total_revenue': f"${total_revenue:,}",
            'status': 'green' if total_revenue > 50000 else 'yellow' if total_revenue > 30000 else 'red'
        }]

        # Annual growth percentage (mock data)
        annual_growth_percentage = 4
        current_year = 2024

        return render_template(
            'dashboard.html',
            partners=partners,
            partner=partners[0],
            pib_total_revenue=f"${total_revenue:,}",
            revenue_growth_percentage=revenue_growth_percentage,
            growth_chart={
                'labels': growth_chart_labels,
                'data': growth_chart_data,
            },
            annual_growth_percentage=annual_growth_percentage,
            current_year=current_year,
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
