import unittest
import json
from app import app
from models import db, Product, Order, OrderItem

class OnlineStoreTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            # Seed a couple of products
            p1 = Product(
                name="Ultra Wireless Mouse",
                description="Ergonomic optical mouse",
                price=29.99,
                category="Electronics",
                stock=10,
                image_url="https://example.com/mouse.jpg"
            )
            p2 = Product(
                name="Cotton Hoodie",
                description="Comfortable fleece hoodie",
                price=49.99,
                category="Apparel",
                stock=5,
                image_url="https://example.com/hoodie.jpg"
            )
            db.session.add_all([p1, p2])
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_storefront_catalog(self):
        """Verify storefront catalog and filtering."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Ultra Wireless Mouse', resp.data)
        self.assertIn(b'Cotton Hoodie', resp.data)

        # Filter category
        resp_cat = self.client.get('/?category=Apparel')
        self.assertEqual(resp_cat.status_code, 200)
        self.assertIn(b'Cotton Hoodie', resp_cat.data)

    def test_product_detail(self):
        """Verify product detail view."""
        with app.app_context():
            p = Product.query.first()
            p_id = p.id

        resp = self.client.get(f'/product/{p_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Ultra Wireless Mouse', resp.data)

    def test_checkout_and_stock_decrement(self):
        """Verify placing an order decrements stock and creates order items."""
        with app.app_context():
            p = Product.query.filter_by(name="Ultra Wireless Mouse").first()
            p_id = p.id
            initial_stock = p.stock

        payload = {
            'customer_name': 'Alex Smith',
            'email': 'alex@example.com',
            'phone': '123-456-7890',
            'shipping_address': '123 Tech Blvd',
            'city': 'San Jose',
            'postal_code': '95112',
            'items': [{'id': p_id, 'quantity': 2, 'name': 'Ultra Wireless Mouse'}]
        }

        resp = self.client.post('/api/checkout', 
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        order_number = data['order_number']
        self.assertTrue(order_number.startswith('ORD-'))

        # Verify stock decrement and order record
        with app.app_context():
            updated_p = db.session.get(Product, p_id)
            self.assertEqual(updated_p.stock, initial_stock - 2)

            order = Order.query.filter_by(order_number=order_number).first()
            self.assertIsNotNone(order)
            self.assertEqual(order.customer_name, 'Alex Smith')
            self.assertEqual(order.status, 'Pending')
            self.assertEqual(len(order.items), 1)
            self.assertEqual(order.items[0].quantity, 2)
            self.assertEqual(order.total_amount, round(29.99 * 2, 2))

    def test_checkout_insufficient_stock(self):
        """Ensure ordering more than available stock is rejected."""
        with app.app_context():
            p = Product.query.filter_by(name="Cotton Hoodie").first()
            p_id = p.id

        payload = {
            'customer_name': 'Over Buyer',
            'email': 'buyer@example.com',
            'phone': '1234567890',
            'shipping_address': '999 High St',
            'items': [{'id': p_id, 'quantity': 99, 'name': 'Cotton Hoodie'}]
        }

        resp = self.client.post('/api/checkout', 
                                data=json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertFalse(data['success'])
        self.assertIn('Insufficient stock', data['message'])

    def test_order_tracking(self):
        """Verify tracking order by order number and API."""
        with app.app_context():
            order = Order(
                order_number="ORD-777888",
                customer_name="Jordan Lee",
                email="jordan@example.com",
                phone="555-0101",
                shipping_address="456 Elm St",
                total_amount=59.98,
                status="Pending",
                tracking_note="Order verified."
            )
            db.session.add(order)
            db.session.commit()

        # Web page tracking
        resp = self.client.get('/track?order_number=ORD-777888')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'ORD-777888', resp.data)
        self.assertIn(b'Jordan Lee', resp.data)

        # JSON API tracking
        resp_api = self.client.get('/api/track/ORD-777888')
        self.assertEqual(resp_api.status_code, 200)
        data = json.loads(resp_api.data)
        self.assertTrue(data['found'])
        self.assertEqual(data['order']['customer_name'], 'Jordan Lee')

    def test_admin_product_and_order_management(self):
        """Verify admin CRUD operations and order status transitions."""
        # 1. Add Product
        resp = self.client.post('/admin/products/add', data={
            'name': 'Ergonomic Desk Mat',
            'description': 'Waterproof vegan leather desk pad',
            'price': '24.50',
            'category': 'Office',
            'stock': '15',
            'image_url': 'https://example.com/mat.jpg'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Ergonomic Desk Mat', resp.data)

        # 2. Update status of an order
        with app.app_context():
            order = Order(
                order_number="ORD-111222",
                customer_name="Sam Taylor",
                email="sam@example.com",
                phone="555-0909",
                shipping_address="789 Pine Rd",
                total_amount=100.0,
                status="Pending"
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id

        # Update order to Shipped with tracking note
        resp_update = self.client.post(f'/admin/orders/update-status/{order_id}', data={
            'status': 'Shipped',
            'tracking_note': 'Shipped via DHL. Tracking # DHL-998822'
        }, follow_redirects=True)
        self.assertEqual(resp_update.status_code, 200)

        with app.app_context():
            updated_order = db.session.get(Order, order_id)
            self.assertEqual(updated_order.status, 'Shipped')
            self.assertIn('DHL-998822', updated_order.tracking_note)

        # Verify customer tracking reflects the updated status
        resp_track = self.client.get('/track?order_number=ORD-111222')
        self.assertIn(b'Shipped', resp_track.data)
        self.assertIn(b'DHL-998822', resp_track.data)

if __name__ == '__main__':
    unittest.main()
