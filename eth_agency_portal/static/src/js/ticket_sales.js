/**
 * Ticket Sales JavaScript
 * Handles ticket product selection and cart management
 * ETH Agency Portal
 */

// Global state
let currentTicketType = 'park';
let products = [];
let cart = { lines: [], visit_date: null, total: 0, item_count: 0 };
let visitors = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTicketSales();
});

async function initializeTicketSales() {
    setDefaultDate();
    await loadCart();
    await loadVisitors();
    await loadProducts();
    renderVisitors();
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
                const cartLine = getCartLine(variant.id);
                const cartQty = cartLine ? cartLine.quantity : 0;
                const stock = variant.available_stock || 0;
                const stockClass = stock > 10 ? 'bg-success' : (stock > 0 ? 'bg-warning' : 'bg-danger');
                const stockText = stock > 0 ? `${stock} available` : 'Out of stock';
                // Get ticket_product_type from cart first (most reliable), then from API
                const ticketProductType = (cartLine ? cartLine.ticket_product_type : '') || variant.ticket_product_type || product.ticket_product_type || '';
                const productName = product.name + ' - ' + variant.name;

                html += `
                    <div class="variant-row py-2 border-top">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <span>${variant.name}</span>
                                <span class="badge ${stockClass} stock-badge ms-2">${stockText}</span>
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${product.id}, ${variant.id}, '${escapeHtml(productName)}', ${product.price}, -1, ${stock}, '${ticketProductType}')" ${stock === 0 || cartQty === 0 ? 'disabled' : ''}>
                                    <i class="fas fa-minus"></i>
                                </button>
                                <input type="number" class="form-control form-control-sm quantity-input"
                                       id="qty_${variant.id}" value="${cartQty}" min="0" max="${stock}"
                                       onchange="setQuantity(${product.id}, ${variant.id}, '${escapeHtml(productName)}', ${product.price}, this.value, ${stock}, '${ticketProductType}')"
                                       ${stock === 0 ? 'disabled' : ''}/>
                                <button class="btn btn-sm btn-outline-primary" onclick="updateQuantity(${product.id}, ${variant.id}, '${escapeHtml(productName)}', ${product.price}, 1, ${stock}, '${ticketProductType}')" ${stock === 0 ? 'disabled' : ''}>
                                    <i class="fas fa-plus"></i>
                                </button>
                            </div>
                        </div>
                        ${renderInlineVisitors(variant.id, productName, cartQty, ticketProductType)}
                    </div>
                `;
            });
            html += `</div>`;
        } else {
            // Single product without variants
            const cartLine = getCartLine(product.id);
            const cartQty = cartLine ? cartLine.quantity : 0;
            const ticketProductType = (cartLine ? cartLine.ticket_product_type : '') || product.ticket_product_type || '';
            html += `
                <div class="variant-row mt-3">
                    <div class="d-flex justify-content-end">
                        <div class="d-flex align-items-center gap-2">
                            <button class="btn btn-sm btn-outline-secondary" onclick="updateQuantity(${product.id}, ${product.id}, '${escapeHtml(product.name)}', ${product.price}, -1, 999, '${ticketProductType}')">
                                <i class="fas fa-minus"></i>
                            </button>
                            <input type="number" class="form-control form-control-sm quantity-input"
                                   id="qty_${product.id}" value="${cartQty}" min="0"
                                   onchange="setQuantity(${product.id}, ${product.id}, '${escapeHtml(product.name)}', ${product.price}, this.value, 999, '${ticketProductType}')"/>
                            <button class="btn btn-sm btn-outline-primary" onclick="updateQuantity(${product.id}, ${product.id}, '${escapeHtml(product.name)}', ${product.price}, 1, 999, '${ticketProductType}')">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                    </div>
                    ${renderInlineVisitors(product.id, product.name, cartQty, ticketProductType)}
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

// Render inline visitors for a variant - shows visitor cards directly under the quantity controls
function renderInlineVisitors(variantId, productName, quantity, ticketProductType) {
    console.log('renderInlineVisitors:', { variantId, quantity, ticketProductType, visitorsCount: visitors.length });

    // Only show for adult/child ticket types
    if (!ticketProductType || (ticketProductType !== 'adult' && ticketProductType !== 'child')) {
        console.log('Skipping - not adult/child type');
        return '';
    }

    if (quantity <= 0) {
        return '';
    }

    let html = `<div class="visitor-inline-container mt-2 ms-2 ps-3 border-start border-2 border-info">`;

    for (let i = 1; i <= quantity; i++) {
        // Use loose equality (==) for type coercion (variant_id might be string or number)
        const visitor = visitors.find(v =>
            v.variant_id == variantId && v.visitor_index == i
        );

        const hasVisitor = visitor && visitor.first_name;
        const visitorName = hasVisitor ? `${visitor.first_name} ${visitor.last_name}` : '';
        const buttonText = hasVisitor ? 'Edit' : 'Add';
        const buttonClass = hasVisitor ? 'btn-outline-success btn-sm' : 'btn-outline-warning btn-sm';
        const iconClass = hasVisitor ? 'fa-check-circle text-success' : 'fa-exclamation-circle text-warning';
        const typeLabel = ticketProductType === 'adult' ? 'Adult' : 'Child';

        html += `
            <div class="visitor-inline-item d-flex align-items-center justify-content-between py-1 ${i < quantity ? 'border-bottom' : ''}">
                <div class="d-flex align-items-center">
                    <i class="fas ${iconClass} me-2"></i>
                    <span class="small">
                        <strong>${i}. ${typeLabel}</strong>
                        ${hasVisitor ? `: ${visitorName}` : ''}
                    </span>
                </div>
                <button type="button" class="btn ${buttonClass}"
                    onclick="openAgencyVisitorModal(${variantId}, '${escapeHtml(productName)}', ${i}, '${ticketProductType}')"
                    data-bs-toggle="modal"
                    data-bs-target="#visitorFormModal">
                    <i class="fas fa-${hasVisitor ? 'edit' : 'plus'} me-1"></i>${buttonText}
                </button>
            </div>
        `;
    }

    html += `</div>`;
    return html;
}

function getCartLine(variantId) {
    if (!cart.lines) return null;
    return cart.lines.find(l => l.variant_id == variantId || l.product_id == variantId);
}

function getCartQuantity(variantId) {
    const line = getCartLine(variantId);
    return line ? line.quantity : 0;
}

// Quantity management
window.updateQuantity = async function(productId, variantId, name, price, delta, maxStock, ticketProductType = '') {
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

    // If decreasing quantity, delete the last visitor for this variant
    if (delta < 0 && currentQty > 0) {
        await deleteLastVisitor(variantId, currentQty);
    }

    await setQuantity(productId, variantId, name, price, newQty, maxStock, ticketProductType);
};

// Delete the last visitor for a variant
async function deleteLastVisitor(variantId, visitorIndex) {
    try {
        const result = await apiCall('/agency/api/tickets/visitors/delete', {
            variant_id: variantId,
            visitor_index: visitorIndex
        });
        if (result && result.success) {
            visitors = result.visitors || [];
        }
    } catch (error) {
        console.error('Error deleting visitor:', error);
    }
}

window.setQuantity = async function(productId, variantId, name, price, quantity, maxStock, ticketProductType = '') {
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
            visit_date: visitDate,
            ticket_product_type: ticketProductType
        });

        if (result && result.success) {
            cart = result.cart;
            // Load visitors separately
            await loadVisitors();
            renderCart();
            renderProducts();
            renderVisitors();
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
            visitors = []; // Clear visitors too
            renderCart();
            renderVisitors();
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

// ==================== Visitor Management ====================

// Load visitors
async function loadVisitors() {
    try {
        const result = await apiCall('/agency/api/tickets/visitors/get');
        if (result && result.success) {
            visitors = result.visitors || [];
        }
    } catch (error) {
        console.error('Error loading visitors:', error);
    }
}

// Render visitors section - shows visitor cards for each ticket in cart
function renderVisitors() {
    const section = document.getElementById('visitorsSection');
    const container = document.getElementById('visitorsContainer');

    if (!section || !container) return;

    // Check if there are any ticket lines (adult/child) in cart
    const ticketLines = cart.lines.filter(line =>
        line.ticket_product_type === 'adult' || line.ticket_product_type === 'child'
    );

    if (ticketLines.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';

    let html = '';

    // Group lines by product
    ticketLines.forEach(line => {
        const variantId = line.variant_id || line.product_id;
        const ticketProductType = line.ticket_product_type;
        const productName = line.product_name;
        const quantity = line.quantity;

        html += `
            <div class="mb-4">
                <h6 class="mb-3">
                    <i class="fas fa-${ticketProductType === 'adult' ? 'user' : 'child'} me-2"></i>
                    ${ticketProductType === 'adult' ? 'Adults' : 'Children (4-11)'} - ${productName}
                </h6>
                <div class="row g-3">
        `;

        // Create a card for each visitor
        for (let i = 1; i <= quantity; i++) {
            const visitor = visitors.find(v =>
                v.variant_id == variantId && v.visitor_index == i
            );

            const hasVisitor = visitor && visitor.first_name;
            const visitorName = hasVisitor ? `${visitor.first_name} ${visitor.last_name}` : '';
            const buttonText = hasVisitor ? 'Edit' : 'Add';
            const buttonClass = hasVisitor ? 'btn-outline-success' : 'btn-outline-primary';
            const cardBorderClass = hasVisitor ? 'border-success' : 'border-warning';

            html += `
                <div class="col-md-6 col-lg-4">
                    <div class="card h-100 ${cardBorderClass}">
                        <div class="card-body p-3">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="badge bg-secondary">${i}. ${ticketProductType === 'adult' ? 'Adult' : 'Child'}</span>
                                ${hasVisitor ? '<i class="fas fa-check-circle text-success"></i>' : '<i class="fas fa-exclamation-circle text-warning"></i>'}
                            </div>
                            ${hasVisitor ? `
                                <div class="visitor-info mb-2">
                                    <div class="fw-bold">${visitorName}</div>
                                    ${visitor.phone ? `<small class="text-muted"><i class="fas fa-phone me-1"></i>${visitor.phone}</small>` : ''}
                                </div>
                            ` : `
                                <div class="text-muted small mb-2">
                                    <i class="fas fa-info-circle me-1"></i>No information yet
                                </div>
                            `}
                            <button type="button" class="btn ${buttonClass} btn-sm w-100"
                                onclick="openAgencyVisitorModal(${variantId}, '${escapeHtml(productName)}', ${i}, '${ticketProductType}')"
                                data-bs-toggle="modal"
                                data-bs-target="#visitorFormModal">
                                <i class="fas fa-${hasVisitor ? 'edit' : 'plus'} me-1"></i>${buttonText}
                            </button>
                        </div>
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
}

// Open visitor modal
window.openAgencyVisitorModal = function(variantId, productName, index, ticketProductType) {
    // Set hidden fields
    document.getElementById('visitor_variant_id').value = variantId;
    document.getElementById('visitor_product_name').value = productName;
    document.getElementById('visitor_index').value = index;
    document.getElementById('ticket_product_type').value = ticketProductType;

    // Update modal title
    const modalTitle = document.getElementById('visitorModalTitle');
    modalTitle.textContent = ticketProductType === 'child' ? 'Child Information' : 'Adult Information';

    // Adult/child field visibility
    const adultFields = document.getElementById('adult_fields');
    const phoneField = document.getElementById('visitor_phone');
    const emailField = document.getElementById('visitor_email');
    const identityField = document.getElementById('visitor_identity');

    if (ticketProductType === 'child') {
        adultFields.style.display = 'none';
        if (phoneField) phoneField.required = false;
        if (emailField) emailField.required = false;
        if (identityField) identityField.required = false;
    } else {
        adultFields.style.display = 'block';
        if (phoneField) phoneField.required = true;
        if (emailField) emailField.required = true;
        if (identityField) identityField.required = true;
    }

    // Find existing visitor data (use loose equality for type safety)
    const visitor = visitors.find(v =>
        v.variant_id == variantId && v.visitor_index == index
    );

    // Fill form with existing data or clear
    document.getElementById('visitor_first_name').value = visitor?.first_name || '';
    document.getElementById('visitor_last_name').value = visitor?.last_name || '';

    if (ticketProductType !== 'child') {
        if (phoneField) phoneField.value = visitor?.phone || '';
        if (emailField) emailField.value = visitor?.email || '';
        if (identityField) identityField.value = visitor?.identity || '';
    } else {
        if (phoneField) phoneField.value = '';
        if (emailField) emailField.value = '';
        if (identityField) identityField.value = '';
    }
};

// Save visitor form
window.handleAgencySaveVisitor = async function(event) {
    event.preventDefault();

    const variantId = parseInt(document.getElementById('visitor_variant_id').value);
    const productName = document.getElementById('visitor_product_name').value;
    const visitorIndex = parseInt(document.getElementById('visitor_index').value);
    const ticketProductType = document.getElementById('ticket_product_type').value;

    const visitorData = {
        variant_id: variantId,
        product_name: productName,
        visitor_index: visitorIndex,
        ticket_product_type: ticketProductType,
        first_name: document.getElementById('visitor_first_name').value,
        last_name: document.getElementById('visitor_last_name').value,
        phone: ticketProductType === 'child' ? '' : (document.getElementById('visitor_phone')?.value || ''),
        email: ticketProductType === 'child' ? '' : (document.getElementById('visitor_email')?.value || ''),
        identity: ticketProductType === 'child' ? '' : (document.getElementById('visitor_identity')?.value || ''),
    };

    try {
        const result = await apiCall('/agency/api/tickets/visitors/save', {
            visitor_data: visitorData
        });

        if (result && result.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('visitorFormModal'));
            if (modal) modal.hide();

            // Use visitors from response if available, otherwise update locally
            if (result.visitors) {
                visitors = result.visitors;
            } else {
                const existingIndex = visitors.findIndex(v =>
                    v.variant_id == variantId && v.visitor_index == visitorIndex
                );
                if (existingIndex >= 0) {
                    visitors[existingIndex] = result.visitor;
                } else {
                    visitors.push(result.visitor);
                }
            }

            console.log('Visitor saved, visitors array:', visitors);

            // Re-render products (visitors are now inline)
            renderProducts();
            renderVisitors();

            Swal.fire({
                icon: 'success',
                title: 'Saved!',
                text: 'Visitor information saved successfully.',
                timer: 1500,
                showConfirmButton: false
            });
        } else {
            Swal.fire('Error', result?.error || 'Failed to save visitor', 'error');
        }
    } catch (error) {
        console.error('Error saving visitor:', error);
        Swal.fire('Error', 'An error occurred while saving visitor', 'error');
    }

    return false;
};
