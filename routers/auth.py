from flask import Blueprint, request, jsonify, make_response
from eth_account import Account
from eth_account.messages import encode_defunct
from jose import jwt
from datetime import datetime, timedelta
import secrets
from expiringdict import ExpiringDict
from models import db, User
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
MAX_BALANCE_ADD = float(os.getenv("MAX_BALANCE_ADD", 10))

nonce_storage = ExpiringDict(max_len=1000, max_age_seconds=300)

def generate_nonce():
    return secrets.token_hex(16)

def create_access_token(data, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_signature(address, message, signature):
    try:
        encoded_message = encode_defunct(text=message)
        recovered = Account.recover_message(encoded_message, signature=signature)
        return recovered.lower() == address.lower()
    except Exception:
        return False

def get_or_create_user(address):
    user = User.query.filter_by(wallet_address=address.lower()).first()
    if user:
        user.last_login = datetime.utcnow()
        db.session.commit()
        return user
    user = User(
        wallet_address=address.lower(),
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()
    return user

def get_current_user_from_token():
    token = request.cookies.get('jwt_token')
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        address = payload.get('sub')
        if address:
            user = User.query.filter_by(wallet_address=address).first()
            return user
    except:
        pass
    return None

def login_required_for_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user_from_token()
        if not user:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/nonce", methods=["POST", "OPTIONS"])
def get_nonce():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    data = request.get_json()
    if not data:
        return jsonify({"error": "invalid request"}), 400
    address = data.get("address", "").lower()
    if not address:
        return jsonify({"error": "address required"}), 400
    nonce = generate_nonce()
    nonce_storage[address] = nonce
    response = jsonify({"nonce": nonce})
    return _corsify_actual_response(response)

@auth_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    data = request.get_json()
    if not data:
        return jsonify({"error": "invalid request body"}), 400
    address = data.get("address", "").lower()
    signature = data.get("signature", "")
    if not address or not signature:
        return jsonify({"error": "address and signature required"}), 400
    stored_nonce = nonce_storage.get(address)
    if stored_nonce is None:
        return jsonify({"error": "nonce expired or not found"}), 400
    message = f"Вход на Abstract Trade: {stored_nonce}"
    if verify_signature(address, message, signature):
        del nonce_storage[address]
        user = get_or_create_user(address)
        access_token = create_access_token(
            data={"sub": address, "user_id": user.id}
        )
        response = make_response(jsonify({
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "wallet_address": address
        }))
        response.set_cookie(
            'jwt_token',
            access_token,
            httponly=True,
            secure=False,
            samesite='Lax',
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path='/'
        )
        return _corsify_actual_response(response)
    return jsonify({"error": "auth failed"}), 401

@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"message": "Logged out successfully"}))
    response.delete_cookie('jwt_token', path='/')
    return response

@auth_bp.route("/me", methods=["GET", "OPTIONS"])
def get_me():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    token = request.cookies.get('jwt_token')
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    if not token:
        return jsonify({"error": "unauthorized"}), 401
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        address = payload.get("sub")
        user_id = payload.get("user_id")
        if address:
            user = User.query.filter_by(wallet_address=address).first()
            if user:
                response = jsonify({
                    "address": address,
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "avatar": user.avatar,
                    "balance": user.balance,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                })
                return _corsify_actual_response(response)
    except:
        pass
    return jsonify({"error": "unauthorized"}), 401

@auth_bp.route("/balance", methods=["GET", "OPTIONS"])
@login_required_for_auth
def get_balance():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    try:
        user = get_current_user_from_token()
        if not user:
            return jsonify({"error": "unauthorized"}), 401
        response = jsonify({"balance": user.balance})
        return _corsify_actual_response(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/add-balance", methods=["POST", "OPTIONS"])
@login_required_for_auth
def add_balance():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    try:
        user = get_current_user_from_token()
        if not user:
            return jsonify({"error": "unauthorized"}), 401
        data = request.get_json()
        amount = data.get("amount", 0)
        if not isinstance(amount, (int, float)) or amount <= 0 or amount > MAX_BALANCE_ADD:
            return jsonify({"error": f"Invalid amount. Must be between 0.01 and {MAX_BALANCE_ADD}"}), 400
        amount = round(amount, 2)
        user.balance = (user.balance or 0) + amount
        db.session.commit()
        response = jsonify({"success": True, "balance": user.balance})
        return _corsify_actual_response(response)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:8000")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

def _corsify_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:8000")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response