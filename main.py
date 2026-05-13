from flask import Flask, render_template, make_response, request, redirect, url_for, jsonify
from flask_cors import CORS
from routers.auth import SECRET_KEY, ALGORITHM
from routers import auth_bp, fractal_bp, marketplace_bp
from jose import jwt
from functools import wraps
from models import db
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='static')
CORS(app, supports_credentials=True, origins=['http://localhost:8000', 'http://127.0.0.1:8000'])

app.config['JSON_AS_ASCII'] = False
app.jinja_env.encoding = 'utf-8'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///abstract_trade.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = False

db.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(fractal_bp)
app.register_blueprint(marketplace_bp)

with app.app_context():
    db.create_all()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('jwt_token')
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        if not token:
            if request.headers.get('Content-Type') == 'application/json' or request.path.startswith('/api'):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for('serve_index'))
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request.user_address = payload.get('sub')
        except:
            if request.headers.get('Content-Type') == 'application/json' or request.path.startswith('/api'):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for('serve_index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def serve_index():
    resp = make_response(render_template('index.html'))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/create')
def serve_create():
    resp = make_response(render_template('create.html'))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/profile')
@login_required
def serve_profile():
    resp = make_response(render_template('profile.html', user_address=request.user_address))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/my-nfts')
@login_required
def serve_my_nfts():
    resp = make_response(render_template('my_nfts.html', user_address=request.user_address))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/settings')
@login_required
def serve_settings():
    resp = make_response(render_template('settings.html', user_address=request.user_address))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/collections')
def serve_collections():
    resp = make_response(render_template('collections.html'))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/analytics')
def serve_analytics():
    resp = make_response(render_template('analytics.html'))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/about')
def serve_about():
    resp = make_response(render_template('about.html'))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

@app.route('/marketplace')
def serve_marketplace():
    resp = make_response(render_template('marketplace.html'))
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)