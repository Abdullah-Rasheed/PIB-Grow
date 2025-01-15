from flask import Flask, render_template, send_from_directory, abort

app = Flask(__name__, static_folder='assets', template_folder='pages')

# Route for specific pages
@app.route('/')
@app.route('/sign-up')
def sign_up():
    return render_template('sign-up.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

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

# Serve static assets
@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(debug=True)
