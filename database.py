from models import db, Product, Order, OrderItem

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_initial_data()

def seed_initial_data():
    """Seed initial products if the database table is empty."""
    if Product.query.count() > 0:
        return

    sample_products = [
        Product(
            name="Wireless Noise-Canceling Headphones",
            description="Premium over-ear wireless headphones featuring active noise cancellation, 40-hour battery life, and crystal-clear audio fidelity.",
            price=149.99,
            category="Electronics",
            stock=25,
            image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
            is_active=True
        ),
        Product(
            name="Minimalist Mechanical Keyboard",
            description="Tenkeyless mechanical gaming keyboard with hot-swappable tactile switches, RGB per-key backlighting, and aluminum chassis.",
            price=89.99,
            category="Electronics",
            stock=18,
            image_url="https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
            is_active=True
        ),
        Product(
            name="Smart Fitness Tracker Watch",
            description="Sleek health companion tracking heart rate, sleep stages, SpO2, and workout metrics with water resistance up to 50m.",
            price=79.50,
            category="Electronics",
            stock=30,
            image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80",
            is_active=True
        ),
        Product(
            name="Classic Cotton Oxford Shirt",
            description="Tailored slim-fit button-down made from 100% breathable organic combed cotton. Perfect for smart casual or business attire.",
            price=45.00,
            category="Apparel",
            stock=40,
            image_url="https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&auto=format&fit=crop&q=80",
            is_active=True
        ),
        Product(
            name="Everyday Canvas Backpack",
            description="Water-resistant 20L canvas daypack featuring a dedicated 15-inch padded laptop sleeve and ergonomic breathable shoulder straps.",
            price=59.95,
            category="Accessories",
            stock=15,
            image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
            is_active=True
        ),
        Product(
            name="Insulated Stainless Steel Tumbler",
            description="Double-wall vacuum insulated 750ml flask keeping drinks ice-cold for 24 hours or piping hot for 12 hours. BPA-free lid.",
            price=24.99,
            category="Home & Living",
            stock=50,
            image_url="https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80",
            is_active=True
        ),
        Product(
            name="Ceramic Pour-Over Coffee Dripper Set",
            description="Artisan matte ceramic dripper with heat-resistant borosilicate glass server and reusable stainless steel mesh filter.",
            price=38.50,
            category="Home & Living",
            stock=12,
            image_url="https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80",
            is_active=True
        ),
        Product(
            name="Polarized Aviator Sunglasses",
            description="Timeless gold-rim aviator sunglasses with UV400 polarized anti-glare scratch-resistant lenses and leather carry case.",
            price=49.00,
            category="Accessories",
            stock=22,
            image_url="https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=600&auto=format&fit=crop&q=80",
            is_active=True
        )
    ]

    for p in sample_products:
        db.session.add(p)
    
    db.session.commit()
    print("Database seeded with sample products.")
