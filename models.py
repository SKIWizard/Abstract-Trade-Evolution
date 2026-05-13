from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(100), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    avatar = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    fractals = db.relationship('Fractal', backref='owner', lazy=True)


class Fractal(db.Model):
    __tablename__ = 'fractals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=True)
    formula = db.Column(db.Text, nullable=False)
    cmap = db.Column(db.String(50), nullable=False)
    x_min = db.Column(db.String(30), nullable=False)
    x_max = db.Column(db.String(30), nullable=False)
    y_min = db.Column(db.String(30), nullable=False)
    y_max = db.Column(db.String(30), nullable=False)
    res = db.Column(db.Integer, nullable=False)
    max_iter = db.Column(db.Integer, nullable=False)
    escape_radius = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)