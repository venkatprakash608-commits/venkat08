from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General')
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'stock': self.stock,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(25), nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(60), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Pending') 
    # Valid statuses: 'Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'
    tracking_note = db.Column(db.String(255), default='Order received and is pending processing.')
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_name': self.customer_name,
            'email': self.email,
            'phone': self.phone,
            'shipping_address': self.shipping_address,
            'city': self.city,
            'postal_code': self.postal_code,
            'total_amount': self.total_amount,
            'status': self.status,
            'tracking_note': self.tracking_note,
            'created_at': self.created_at.strftime('%b %d, %Y %I:%M %p') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%b %d, %Y %I:%M %p') if self.updated_at else None,
            'items': [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product_name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship('Product', foreign_keys=[product_id], lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'price': self.price,
            'quantity': self.quantity,
            'subtotal': round(self.price * self.quantity, 2)
        }
