from flask import Flask, render_template, redirect, request, url_for, session
import requests
import os

app = Flask(__name__, static_folder='assets', template_folder='pages')

# Facebook App Configuration
FB_APP_ID = os.getenv("FACEBOOK_APP_ID", "407721285698090")
FB_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "4775235855fcd971cfe6828ab439b4fc")
FB_REDIRECT_URI = os.getenv("REDIRECT_URI", "https://pib-grow.vercel.app/auth/callback")


# Sign-Up Page Route
@app.route('/')
@app.route('/sign-up')
def sign_up():
    # Generate Facebook login URL
    fb_login_url = (
        f"https://www.facebook.com/v16.0/dialog/oauth"
        f"?client_id={FB_APP_ID}"
        f"&redirect_uri={FB_REDIRECT_URI}"
        f"&scope=pages_read_engagement,pages_show_list,pages_read_user_content"
    )
    return render_template('sign-up.html', fb_login_url=fb_login_url)


# Facebook OAuth Callback
@app.route('/auth/callback')
def facebook_callback():
    # Get the authorization code from Facebook's callback
    code = request.args.get('code')
    if not code:
        return "Error: Authorization code not received", 400

    # Exchange authorization code for an access token
    token_url = "https://graph.facebook.com/v16.0/oauth/access_token"
    params = {
        'client_id': FB_APP_ID,
        'redirect_uri': FB_REDIRECT_URI,
        'client_secret': FB_APP_SECRET,
        'code': code
    }
    response = requests.get(token_url, params=params)
    if response.status_code != 200:
        return f"Error: Unable to fetch access token ({response.json()})", 400

    access_token = response.json().get('access_token')
    session['access_token'] = access_token

    # Fetch the user's Facebook pages
    pages_url = "https://graph.facebook.com/v16.0/me/accounts"
    headers = {"Authorization": f"Bearer {access_token}"}
    pages_response = requests.get(pages_url, headers=headers)
    if pages_response.status_code != 200:
        return f"Error: Unable to fetch pages data ({pages_response.json()})", 400

    pages_data = pages_response.json().get('data', [])
    session['pages'] = pages_data  # Store pages data in session

    return redirect(url_for('dashboard'))


# Dashboard Route
@app.route('/dashboard')
def dashboard():
    pages = session.get('pages', [])  # Retrieve pages data from session
    return render_template('dashboard.html', pages=pages)


# Other Routes
@app.route('/partners')
def partners():
    return render_template('partners.html')


@app.route('/profile')
def profile():
    return render_template('profile.html')


@app.route('/accounting')
def accounting():
    return render_template('accounting.html')


@app.route('/reports')
def reports():
    return render_template('reports.html')


# Serve Static Assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)


if __name__ == '__main__':
    app.run(debug=True)
