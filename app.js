// Cart & Frontend Interaction Manager

const Cart = {
    STORAGE_KEY: 'nova_store_cart',

    getItems() {
        try {
            return JSON.parse(localStorage.getItem(this.STORAGE_KEY)) || [];
        } catch (e) {
            console.error('Failed to parse cart:', e);
            return [];
        }
    },

    save(items) {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(items));
        this.updateBadge();
        window.dispatchEvent(new CustomEvent('cart-updated', { detail: items }));
    },

    addItem(product, quantity = 1) {
        let items = this.getItems();
        let existing = items.find(item => item.id === product.id);

        if (existing) {
            const newQty = existing.quantity + quantity;
            if (product.stock && newQty > product.stock) {
                showToast(`Cannot add more. Maximum available stock is ${product.stock}.`, 'warning');
                return false;
            }
            existing.quantity = newQty;
        } else {
            if (product.stock && quantity > product.stock) {
                showToast(`Cannot add. Maximum available stock is ${product.stock}.`, 'warning');
                return false;
            }
            items.push({
                id: product.id,
                name: product.name,
                price: parseFloat(product.price),
                image_url: product.image_url,
                category: product.category,
                stock: product.stock,
                quantity: quantity
            });
        }

        this.save(items);
        showToast(`Added "${product.name}" to cart!`, 'success');
        return true;
    },

    updateQuantity(productId, quantity) {
        let items = this.getItems();
        let item = items.find(i => i.id === productId);
        if (!item) return;

        if (quantity <= 0) {
            this.removeItem(productId);
            return;
        }

        if (item.stock && quantity > item.stock) {
            showToast(`Only ${item.stock} units available in stock.`, 'warning');
            item.quantity = item.stock;
        } else {
            item.quantity = quantity;
        }

        this.save(items);
    },

    removeItem(productId) {
        let items = this.getItems();
        const removed = items.find(i => i.id === productId);
        items = items.filter(item => item.id !== productId);
        this.save(items);
        if (removed) {
            showToast(`Removed "${removed.name}" from cart.`, 'info');
        }
    },

    clear() {
        localStorage.removeItem(this.STORAGE_KEY);
        this.updateBadge();
        window.dispatchEvent(new CustomEvent('cart-updated', { detail: [] }));
    },

    getTotalCount() {
        const items = this.getItems();
        return items.reduce((sum, item) => sum + item.quantity, 0);
    },

    getSubtotal() {
        const items = this.getItems();
        return items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    },

    updateBadge() {
        const count = this.getTotalCount();
        const badges = document.querySelectorAll('.cart-count-badge');
        badges.forEach(badge => {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-flex' : 'none';
        });
    }
};

// Toast notification helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-3 text-white max-w-sm transition-all duration-300 shadow-xl ${
        type === 'success' ? 'bg-emerald-600' :
        type === 'warning' ? 'bg-amber-600' :
        type === 'error' ? 'bg-rose-600' : 'bg-indigo-600'
    }`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    if (type === 'warning') icon = '⚠️';
    if (type === 'error') icon = '✕';

    toast.innerHTML = `
        <span class="text-base font-bold">${icon}</span>
        <span class="flex-1">${message}</span>
        <button onclick="this.parentElement.remove()" class="text-white/80 hover:text-white font-bold ml-2">×</button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-fadeout');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    Cart.updateBadge();

    // Attach click listeners for quick-add buttons
    document.querySelectorAll('[data-add-to-cart]').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            try {
                const productData = JSON.parse(button.getAttribute('data-product'));
                Cart.addItem(productData, 1);
            } catch (err) {
                console.error('Failed to add product to cart', err);
            }
        });
    });
});
