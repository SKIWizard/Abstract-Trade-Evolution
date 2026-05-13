from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Fractal(db.Model):
    __tablename__ = 'fractals'

    id = db.Column(db.Integer, primary_key=True)
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