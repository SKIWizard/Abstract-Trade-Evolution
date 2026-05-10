from flask import Blueprint, request, jsonify, make_response
from eth_account import Account
from eth_account.messages import encode_defunct
from jose import jwt
from datetime import datetime, timedelta
import secrets
from expiringdict import ExpiringDict

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

SECRET_KEY = "NFHIBSNJKbOBFPHYBEDFnmdfsdufnNFIUDFODFJE8HFiupdhgbfyg)*^fd&^%dfSC7fyZScxUCBH78SGXCScbdsgb8&GBADSHfc_&(*DGFDSbgciuDGBCDSGBCDS&YGBVcfdbuGD&FVSBD87vgDSCFSdcvoihfbwsgrvOIUUWOIRRWVBNGOIU"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

nonce_storage = ExpiringDict(max_len=1000, max_age_seconds=300)

def generate_nonce():
    return secrets.token_hex(16)

def create_access_token(data, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_signature(address, message, signature):
    try:
        encoded_message = encode_defunct(text=message)
        recovered = Account.recover_message(encoded_message, signature=signature)
        return recovered.lower() == address.lower()
    except Exception:
        return False

@auth_bp.route("/nonce", methods=["POST"])
def get_nonce():
    data = request.get_json()
    address = data.get("address", "").lower()
    nonce = generate_nonce()
    nonce_storage[address] = nonce
    return jsonify({"nonce": nonce})

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    address = data.get("address", "").lower()
    signature = data.get("signature", "")
    stored_nonce = nonce_storage.get(address)
    if stored_nonce is None:
        return jsonify({"error": "nonce expired or not found"}), 400
    message = f"Вход на Abscure Trade: {stored_nonce}"
    if verify_signature(address, message, signature):
        del nonce_storage[address]
        access_token = create_access_token(
            data={"sub": address},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        response = make_response(jsonify({"access_token": access_token, "token_type": "bearer"}))
        response.set_cookie(
            'jwt_token',
            access_token,
            httponly=False,
            secure=False,
            samesite='Lax',
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return response
    return jsonify({"error": "auth failed"}), 401

@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"message": "Logged out successfully"}))
    response.delete_cookie('jwt_token')
    return response

@auth_bp.route("/me", methods=["GET"])
def get_me():
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
        if address:
            return jsonify({"address": address})
    except:
        pass

    return jsonify({"error": "unauthorized"}), 401