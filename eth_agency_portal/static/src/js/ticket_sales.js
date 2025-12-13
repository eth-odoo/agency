/**
 * Ticket Sales JavaScript
 * Handles ticket product selection and cart management
 * ETH Agency Portal
 */

// Global state
let currentTicketType = 'park';
let products = [];
let cart = { lines: [], visit_date: null, total: 0, item_count: 0 };

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTicketSales();
});

async function initializeTicketSales() {
    setDefaultDate();
    await loadCart();
    await loadProducts();
}

function setDefaultDate() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const dateInput = document.getElementById('visit_date');
    if (dateInput) {
        dateInput.value = formatDateForInput(tomorrow);
        dateInput.min = formatDateForInput(today);
    }
}

function formatDateForInput(date) {
    return date.toISOString().split('T')[0];
}

function formatDateForDisplay(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

// API call helper
async function apiCall(endpoint, params = {}) {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: Date.now()
        })
    });
    const data = await response.json();
    return data.result;
}

// Load products
async function loadProducts() {
    const visitDate = document.getElementById('visit_date')?.value;

    document.getElementById('productsLoading').style.display = 'block';
    document.getElementById('productsList').style.display = 'none';
    document.getElementById('noProducts').style.display = 'none';

    try {
        const result = await apiCall('/agency/api/tickets/products', {
            ticket_type: currentTicketType,
            visit_date: visitDate
        });

        document.getElementById('productsLoading').style.display = 'none';

        if (result && result.success) {
            products = result.data.products || [];
            renderProducts();
        } else {
            console.error('Failed to load products:', result?.error);
            document.getElementById('noProducts').style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading products:', error);
        document.getElementById('productsLoading').style.display = 'none';
        document.getElementById('noProducts').style.display = 'block';
    }
}

function renderProducts() {
    const container = document.getElementById('productsList');

    if (!products || products.length === 0) {
        container.style.display = 'none';
        document.getElementById('noProducts').style.display = 'block';
        return;
    }

    let html = '';
    products.forEach(product => {
        const variants = product.variants || [];
        const hasVariants = variants.length > 1;

        html += `
            <div class="product-card" data-product-id="${product.id}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <div class="product-image">
                                <i class="fas fa-ticket-alt fa-2x text-primary"></i>
                            </div>
                        </div>
                        <div class="col">
                            <h6 class="mb-1">${product.name}</h6>
                            <div class="text-muted small">
                                ${product.ticket_product_type || product.ticket_type || ''}
                            </div>
                        </div>
                        <div class="col-auto text-end">
                            <div class="h5 text-primary mb-1">${product.price.toFixed(2)} ${product.currency_symbol || product.currency || 'EUR'}</div>
                        </div>
                    </div>
        `;

        // Render variants
        if (variants.length > 0) {
            html += `<div class="mt-3">`;
            variants.forEach(variant => {
                const cartQty = getCartQuantity(variant.id);
                const stock = variant.available_stock || 0;
                const stockClass = stock > 10 ? 'bg-success' : (stock > 0 ? 'bg-warning' : 'bg-danger');
                const stockText = stock > 0 ? `${stock} available` : 'Out of stock';

                html += `
                    <div class="d-flex justify-content-between align-items-center py-2 border-top">
                        <div>
                            <span>${variant.name}</span>
                            <span class="badge ${stockClass} stock-badge ms-2">${stockText}</span>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${product.id}, ${variant.id}, '${escapeHtml(product.name + ' - ' + variant.name)}', ${product.price}, -1, ${stock})" ${stock === 0 || cartQty === 0 ? 'disabled' : ''}>
                                <i class="fas fa-minus"></i>
                            </button>
                            <input type="number" class="form-control form-control-sm quantity-input"
                                   id="qty_${variant.id}" value="${cartQty}" min="0" max="${stock}"
                                   onchange="setQuantity(${product.id}, ${variant.id}, '${escapeHtml(product.name + ' - ' + variant.name)}', ${product.price}, this.value, ${stock})"
                                   ${stock === 0 ? 'disabled' : ''}/>
                            <button class="btn btn-sm btn-outline-primary" onclick="updateQuantity(${product.id}, ${variant.id}, '${escapeHtml(product.name + ' - ' + variant.name)}', ${product.price}, 1, ${stock})" ${stock === 0 ? 'disabled' : ''}>
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        } else {
            // Single product without variants
            const cartQty = getCartQuantity(product.id);
            html += `
                <div class="d-flex justify-content-end mt-3">
                    <div class="d-flex align-items-center gap-2">
                        <button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${product.id}, ${product.id}, '${escapeHtml(product.name)}', ${product.price}, -1, 999)">
                            <i class="fas fa-minus"></i>
                        </button>
                        <input type="number" class="form-control form-control-sm quantity-input"
                               id="qty_${product.id}" value="${cartQty}" min="0"
                               onchange="setQuantity(${product.id}, ${product.id}, '${escapeHtml(product.name)}', ${product.price}, this.value, 999)"/>
                        <button class="btn btn-sm btn-outline-primary" onclick="updateQuantity(${product.id}, ${product.id}, '${escapeHtml(product.name)}', ${product.price}, 1, 999)">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </div>
            `;
        }

        html += `
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    container.style.display = 'block';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, "\\'");
}

function getCartQuantity(variantId) {
    const line = cart.lines.find(l => l.variant_id === variantId || l.product_id === variantId);
    return line ? line.quantity : 0;
}

// Quantity management
window.updateQuantity = async function(productId, variantId, name, price, delta, maxStock) {
    const input = document.getElementById(`qty_${variantId}`);
    let currentQty = parseInt(input?.value) || 0;
    let newQty = Math.max(0, currentQty + delta);

    if (newQty > maxStock) {
        newQty = maxStock;
        Swal.fire({
            icon: 'warning',
            title: 'Stock Limit',
            text: `Only ${maxStock} items available`,
            timer: 2000,
            showConfirmButton: false
        });
    }

    await setQuantity(productId, variantId, name, price, newQty, maxStock);
};

window.setQuantity = async function(productId, variantId, name, price, quantity, maxStock) {
    quantity = parseInt(quantity) || 0;

    if (quantity > maxStock) {
        quantity = maxStock;
        Swal.fire({
            icon: 'warning',
            title: 'Stock Limit',
            text: `Only ${maxStock} items available`,
            timer: 2000,
            showConfirmButton: false
        });
    }

    const input = document.getElementById(`qty_${variantId}`);
    if (input) input.value = quantity;

    const visitDate = document.getElementById('visit_date')?.value;

    try {
        const result = await apiCall('/agency/api/tickets/cart/add', {
            product_id: productId,
            variant_id: variantId,
            product_name: name,
            quantity: quantity,
            price: price,
            visit_date: visitDate
        });

        if (result && result.success) {
            cart = result.cart;
            renderCart();
        } else {
            console.error('Failed to update cart:', result?.error);
        }
    } catch (error) {
        console.error('Error updating cart:', error);
    }
};

// Cart management
async function loadCart() {
    try {
        const result = await apiCall('/agency/api/tickets/cart/get');
        if (result && result.success) {
            cart = result.cart || { lines: [], visit_date: null, total: 0, item_count: 0 };
            renderCart();
        }
    } catch (error) {
        console.error('Error loading cart:', error);
    }
}

function renderCart() {
    const container = document.getElementById('cartItems');
    const footer = document.getElementById('cartFooter');
    const countBadge = document.getElementById('cartItemCount');

    if (!cart.lines || cart.lines.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-shopping-cart fa-2x mb-2"></i>
                <p class="mb-0">Your cart is empty</p>
            </div>
        `;
        footer.style.display = 'none';
        countBadge.textContent = '0';
        return;
    }

    let html = '';
    cart.lines.forEach(line => {
        html += `
            <div class="cart-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="fw-medium">${line.product_name}</div>
                        <small class="text-muted">${line.quantity} x ${line.price.toFixed(2)} EUR</small>
                    </div>
                    <div class="text-end">
                        <div class="fw-bold">${(line.quantity * line.price).toFixed(2)} EUR</div>
                        <button class="btn btn-sm btn-link text-danger p-0" onclick="removeFromCart(${line.variant_id || line.product_id})">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    footer.style.display = 'block';

    document.getElementById('cartVisitDate').textContent = formatDateForDisplay(cart.visit_date);
    document.getElementById('cartTotal').textContent = `${cart.total.toFixed(2)} EUR`;
    countBadge.textContent = cart.item_count || cart.lines.reduce((sum, l) => sum + l.quantity, 0);
}

window.removeFromCart = async function(variantId) {
    const line = cart.lines.find(l => l.variant_id === variantId || l.product_id === variantId);
    if (line) {
        await setQuantity(line.product_id, variantId, line.product_name, line.price, 0, 999);
    }
};

window.clearCart = async function() {
    const result = await Swal.fire({
        title: 'Clear Cart?',
        text: 'Are you sure you want to remove all items from the cart?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        confirmButtonText: 'Yes, Clear',
        cancelButtonText: 'Cancel'
    });

    if (!result.isConfirmed) return;

    try {
        const apiResult = await apiCall('/agency/api/tickets/cart/clear');
        if (apiResult && apiResult.success) {
            cart = { lines: [], visit_date: null, total: 0, item_count: 0 };
            renderCart();
            renderProducts(); // Refresh quantities in products
        }
    } catch (error) {
        console.error('Error clearing cart:', error);
    }
};

// Order confirmation
window.confirmOrder = async function() {
    if (!cart.lines || cart.lines.length === 0) {
        Swal.fire('Error', 'Your cart is empty', 'error');
        return;
    }

    const result = await Swal.fire({
        title: 'Confirm Order',
        html: `
            <p>Visit Date: <strong>${formatDateForDisplay(cart.visit_date)}</strong></p>
            <p>Total: <strong>${cart.total.toFixed(2)} EUR</strong></p>
            <p>Items: <strong>${cart.item_count || cart.lines.reduce((sum, l) => sum + l.quantity, 0)}</strong></p>
        `,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#28a745',
        confirmButtonText: 'Confirm Order',
        cancelButtonText: 'Cancel'
    });

    if (!result.isConfirmed) return;

    try {
        Swal.fire({
            title: 'Creating Order...',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        const apiResult = await apiCall('/agency/api/tickets/order/create');

        if (apiResult && apiResult.success) {
            cart = { lines: [], visit_date: null, total: 0, item_count: 0 };
            renderCart();
            renderProducts();

            Swal.fire({
                icon: 'success',
                title: 'Order Created!',
                html: `
                    <p>Order Number: <strong>${apiResult.data.order_name}</strong></p>
                    <p>Total: <strong>${apiResult.data.amount_total?.toFixed(2) || cart.total.toFixed(2)} EUR</strong></p>
                `,
                confirmButtonText: 'OK'
            });
        } else {
            Swal.fire('Error', apiResult?.error || 'Failed to create order', 'error');
        }
    } catch (error) {
        console.error('Error creating order:', error);
        Swal.fire('Error', 'An error occurred while creating order', 'error');
    }
};

// Ticket type selection
window.selectTicketType = function(type, event) {
    if (event) event.preventDefault();

    currentTicketType = type;

    // Update tabs
    document.querySelectorAll('#ticketTypeTabs .nav-link').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.type === type) {
            tab.classList.add('active');
        }
    });

    loadProducts();
};

// Visit date change
window.onVisitDateChange = function() {
    // If cart has items, warn user
    if (cart.lines && cart.lines.length > 0) {
        Swal.fire({
            title: 'Change Date?',
            text: 'Changing the date will clear your cart. Continue?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, Change',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                clearCart();
                loadProducts();
            } else {
                // Revert date
                document.getElementById('visit_date').value = cart.visit_date;
            }
        });
    } else {
        loadProducts();
    }
};
