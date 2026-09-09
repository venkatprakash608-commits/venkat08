import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Product, Order, OrderItem
from database import init_db

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-store-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)

def generate_order_number():
    prefix = "ORD"
    digits = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}-{digits}"

# ----------------- CUSTOMER STOREFRONT ----------------- #

@app.route('/')
def index():
    category = request.args.get('category', '').strip()
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'newest')

    query = Product.query.filter_by(is_active=True)

    if category and category != 'All':
        query = query.filter_by(category=category)

    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.description.ilike(f'%{search_query}%'))
        )

    if sort_by == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'name':
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.id.desc())

    products = query.all()

    # Get distinct categories for filter buttons
    categories = [row[0] for row in db.session.query(Product.category).distinct().all()]

    return render_template(
        'index.html',
        products=products,
        categories=categories,
        selected_category=category or 'All',
        search_query=search_query,
        sort_by=sort_by
    )

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    related_products = Product.query.filter(
        Product.category == product.category,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()
    return render_template('product_detail.html', product=product, related_products=related_products)

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/api/products/batch', methods=['POST'])
def get_products_batch():
    """Retrieve multiple products by IDs (useful for refreshing cart item details)."""
    data = request.get_json() or {}
    product_ids = data.get('ids', [])
    if not product_ids:
        return jsonify({'products': []})

    products = Product.query.filter(Product.id.in_(product_ids), Product.is_active == True).all()
    return jsonify({'products': [p.to_dict() for p in products]})

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request payload'}), 400

    customer_name = data.get('customer_name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    shipping_address = data.get('shipping_address', '').strip()
    city = data.get('city', '').strip()
    postal_code = data.get('postal_code', '').strip()
    cart_items = data.get('items', [])

    if not customer_name or not email or not phone or not shipping_address:
        return jsonify({'success': False, 'message': 'All required shipping fields must be filled.'}), 400

    if not cart_items:
        return jsonify({'success': False, 'message': 'Your cart is empty.'}), 400

    # Validate stock and calculate total
    total_amount = 0.0
    validated_items = []

    for item in cart_items:
        p_id = item.get('id')
        qty = int(item.get('quantity', 1))

        if qty <= 0:
            continue

        product = db.session.get(Product, p_id)
        if not product or not product.is_active:
            return jsonify({'success': False, 'message': f'Product {item.get("name", "Unknown")} is unavailable.'}), 400

        if product.stock < qty:
            return jsonify({
                'success': False,
                'message': f'Insufficient stock for "{product.name}". Available: {product.stock}, requested: {qty}.'
            }), 400

        item_total = round(product.price * qty, 2)
        total_amount += item_total
        validated_items.append((product, qty, product.price))

    if not validated_items:
        return jsonify({'success': False, 'message': 'No valid items to purchase.'}), 400

    total_amount = round(total_amount, 2)

    # Unique order number
    order_number = generate_order_number()
    while Order.query.filter_by(order_number=order_number).first():
        order_number = generate_order_number()

    # Create Order
    new_order = Order(
        order_number=order_number,
        customer_name=customer_name,
        email=email,
        phone=phone,
        shipping_address=shipping_address,
        city=city,
        postal_code=postal_code,
        total_amount=total_amount,
        status='Pending',
        tracking_note='Order placed and awaiting warehouse processing.'
    )
    db.session.add(new_order)
    db.session.flush()

    # Deduct stock and create OrderItems
    for product, qty, price in validated_items:
        product.stock -= qty
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            product_name=product.name,
            price=price,
            quantity=qty
        )
        db.session.add(order_item)

    db.session.commit()

    return jsonify({
        'success': True,
        'order_number': order_number,
        'message': 'Order successfully placed!'
    })

@app.route('/order-confirmation/<order_number>')
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('order_confirmation.html', order=order)

# ----------------- ORDER TRACKING ----------------- #

@app.route('/track')
def track_order():
    query = request.args.get('order_number', '').strip()
    order = None
    if query:
        order = Order.query.filter(
            (Order.order_number == query) | (Order.email.ilike(query))
        ).order_by(Order.id.desc()).first()

    return render_template('track_order.html', order=order, query=query)

@app.route('/api/track/<order_number>')
def api_track_order(order_number):
    order = Order.query.filter_by(order_number=order_number.strip()).first()
    if not order:
        return jsonify({'found': False, 'message': 'Order not found.'}), 404
    return jsonify({'found': True, 'order': order.to_dict()})

# ----------------- ADMIN DASHBOARD & MANAGEMENT ----------------- #

@app.route('/admin')
def admin_dashboard():
    total_orders = Order.query.count()
    total_products = Product.query.count()
    low_stock_products = Product.query.filter(Product.stock <= 5, Product.is_active == True).all()
    
    # Calculate revenue
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(Order.status != 'Cancelled').scalar() or 0.0

    recent_orders = Order.query.order_by(Order.id.desc()).limit(8).all()

    status_counts = {
        'Pending': Order.query.filter_by(status='Pending').count(),
        'Processing': Order.query.filter_by(status='Processing').count(),
        'Shipped': Order.query.filter_by(status='Shipped').count(),
        'Delivered': Order.query.filter_by(status='Delivered').count(),
        'Cancelled': Order.query.filter_by(status='Cancelled').count(),
    }

    return render_template(
        'admin/dashboard.html',
        total_orders=total_orders,
        total_products=total_products,
        total_revenue=round(total_revenue, 2),
        low_stock_products=low_stock_products,
        recent_orders=recent_orders,
        status_counts=status_counts
    )

@app.route('/admin/products')
def admin_products():
    category = request.args.get('category', '').strip()
    search = request.args.get('q', '').strip()

    query = Product.query
    if category and category != 'All':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    products = query.order_by(Product.id.desc()).all()
    categories = [row[0] for row in db.session.query(Product.category).distinct().all()]

    return render_template(
        'admin/products.html',
        products=products,
        categories=categories,
        selected_category=category or 'All',
        search=search
    )

@app.route('/admin/products/add', methods=['POST'])
def admin_add_product():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price = float(request.form.get('price', 0.0))
    category = request.form.get('category', 'General').strip()
    stock = int(request.form.get('stock', 0))
    image_url = request.form.get('image_url', '').strip()

    if not name or price <= 0:
        flash('Valid product name and price greater than 0 are required.', 'error')
        return redirect(url_for('admin_products'))

    if not image_url:
        image_url = "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600&auto=format&fit=crop&q=80"

    product = Product(
        name=name,
        description=description,
        price=price,
        category=category or 'General',
        stock=max(0, stock),
        image_url=image_url,
        is_active=True
    )
    db.session.add(product)
    db.session.commit()
    flash(f'Product "{name}" added successfully!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/edit/<int:product_id>', methods=['POST'])
def admin_edit_product(product_id):
    product = db.get_or_404(Product, product_id)
    product.name = request.form.get('name', product.name).strip()
    product.description = request.form.get('description', product.description).strip()
    product.price = float(request.form.get('price', product.price))
    product.category = request.form.get('category', product.category).strip()
    product.stock = int(request.form.get('stock', product.stock))
    image_url = request.form.get('image_url', '').strip()
    if image_url:
        product.image_url = image_url

    db.session.commit()
    flash(f'Product "{product.name}" updated successfully!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/toggle/<int:product_id>', methods=['POST'])
def admin_toggle_product(product_id):
    product = db.get_or_404(Product, product_id)
    product.is_active = not product.is_active
    db.session.commit()
    status_str = "active" if product.is_active else "inactive"
    flash(f'Product "{product.name}" set to {status_str}.', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
def admin_delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    name = product.name
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{name}" deleted.', 'warning')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
def admin_orders():
    status = request.args.get('status', '').strip()
    search = request.args.get('q', '').strip()

    query = Order.query
    if status and status != 'All':
        query = query.filter_by(status=status)
    if search:
        query = query.filter(
            (Order.order_number.ilike(f'%{search}%')) |
            (Order.customer_name.ilike(f'%{search}%')) |
            (Order.email.ilike(f'%{search}%'))
        )

    orders = query.order_by(Order.id.desc()).all()

    return render_template(
        'admin/orders.html',
        orders=orders,
        selected_status=status or 'All',
        search=search
    )

@app.route('/admin/orders/update-status/<int:order_id>', methods=['POST'])
def admin_update_order_status(order_id):
    order = db.get_or_404(Order, order_id)
    new_status = request.form.get('status')
    note = request.form.get('tracking_note', '').strip()

    valid_statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    if new_status in valid_statuses:
        order.status = new_status
        if note:
            order.tracking_note = note
        else:
            default_notes = {
                'Pending': 'Order received and is pending warehouse processing.',
                'Processing': 'Order is being packed and prepared for carrier pickup.',
                'Shipped': 'Package has been dispatched and is in transit with carrier.',
                'Delivered': 'Package has been delivered to destination address.',
                'Cancelled': 'Order has been cancelled.'
            }
            order.tracking_note = default_notes.get(new_status, order.tracking_note)

        db.session.commit()
        flash(f'Order {order.order_number} status updated to {new_status}.', 'success')
    else:
        flash('Invalid status update requested.', 'error')

    return redirect(request.referrer or url_for('admin_orders'))

@app.route('/admin/orders/<int:order_id>')
def admin_order_detail(order_id):
    order = db.get_or_404(Order, order_id)
    return render_template('admin/order_detail.html', order=order)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
