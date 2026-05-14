from flask import Blueprint, jsonify, request
from models import db, User, Fractal, Listing
from routers.auth import get_current_user_from_token
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/marketplace')
MAX_PRICE = float(os.getenv("MAX_PRICE", 10000))

def login_required_marketplace(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user_from_token()
        if not user:
            return jsonify({"error": "unauthorized"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

@marketplace_bp.route("/list", methods=["POST"])
@login_required_marketplace
def list_fractal():
    try:
        data = request.get_json()
        fractal_id = data.get("fractal_id")
        price = data.get("price")

        if not fractal_id or not price or price <= 0 or price > MAX_PRICE:
            return jsonify({"error": f"Invalid price. Must be between 0.01 and {MAX_PRICE}"}), 400

        fractal = Fractal.query.filter_by(id=fractal_id, user_id=request.current_user.id).first()
        if not fractal:
            return jsonify({"error": "fractal not found"}), 404

        if fractal.is_listed:
            return jsonify({"error": "fractal already listed"}), 400

        existing_listing = Listing.query.filter_by(fractal_id=fractal_id, status='active').first()
        if existing_listing:
            return jsonify({"error": "fractal already has active listing"}), 400

        listing = Listing(
            fractal_id=fractal_id,
            seller_id=request.current_user.id,
            price=price,
            status='active'
        )

        fractal.is_listed = True

        db.session.add(listing)
        db.session.commit()

        return jsonify({
            "success": True,
            "listing": {
                "id": listing.id,
                "fractal_id": fractal_id,
                "price": price,
                "status": listing.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route("/unlist/<int:listing_id>", methods=["DELETE"])
@login_required_marketplace
def unlist_fractal(listing_id):
    try:
        listing = Listing.query.filter_by(id=listing_id, seller_id=request.current_user.id, status='active').first()
        if not listing:
            return jsonify({"error": "listing not found"}), 404

        fractal = Fractal.query.get(listing.fractal_id)
        if fractal:
            fractal.is_listed = False

        listing.status = 'cancelled'
        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route("/listings", methods=["GET"])
def get_listings():
    try:
        listings = Listing.query.filter_by(status='active').order_by(Listing.created_at.desc()).all()

        listings_data = []
        for listing in listings:
            fractal = Fractal.query.get(listing.fractal_id)
            if not fractal or fractal.user_id != listing.seller_id:
                continue

            seller = User.query.get(listing.seller_id)

            listings_data.append({
                "id": listing.id,
                "fractal_id": listing.fractal_id,
                "fractal_name": fractal.name if fractal and fractal.name else f"Fractal #{listing.fractal_id}",
                "price": listing.price,
                "seller_address": seller.wallet_address if seller else "unknown",
                "created_at": listing.created_at.isoformat() if listing.created_at else None
            })

        return jsonify({"success": True, "listings": listings_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route("/buy/<int:listing_id>", methods=["POST"])
@login_required_marketplace
def buy_fractal(listing_id):
    try:
        listing = Listing.query.filter_by(id=listing_id, status='active').first()
        if not listing:
            return jsonify({"error": "listing not found"}), 404

        if listing.seller_id == request.current_user.id:
            return jsonify({"error": "cannot buy your own fractal"}), 400

        seller = User.query.get(listing.seller_id)
        fractal = Fractal.query.get(listing.fractal_id)

        if not fractal:
            return jsonify({"error": "fractal not found"}), 404

        if fractal.user_id != listing.seller_id:
            return jsonify({"error": "fractal ownership mismatch, listing invalid"}), 400

        if request.current_user.balance < listing.price:
            return jsonify({"error": "insufficient balance"}), 400

        request.current_user.balance -= listing.price
        seller.balance += listing.price

        fractal.user_id = request.current_user.id
        fractal.is_listed = False

        listing.status = 'sold'

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Fractal purchased successfully",
            "new_balance": request.current_user.balance
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@marketplace_bp.route("/my-listings", methods=["GET"])
@login_required_marketplace
def get_my_listings():
    try:
        listings = Listing.query.filter_by(seller_id=request.current_user.id, status='active').all()

        listings_data = []
        for listing in listings:
            fractal = Fractal.query.get(listing.fractal_id)
            if not fractal or fractal.user_id != listing.seller_id:
                continue
            listings_data.append({
                "id": listing.id,
                "fractal_id": listing.fractal_id,
                "fractal_name": fractal.name if fractal and fractal.name else f"Fractal #{listing.fractal_id}",
                "price": listing.price,
                "created_at": listing.created_at.isoformat() if listing.created_at else None
            })

        return jsonify({"success": True, "listings": listings_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500