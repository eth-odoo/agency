/**
 * Hotel Bookings JavaScript
 * Handles hotel room search and booking with bonus usage
 * ETH Agency Portal - mirrors eth_travel_agency_web functionality
 */

// Global state
let hotelsData = [];
let marketsData = [];
let searchResults = null;
let selectedRoom = null;
let selectedRate = null;
let walletBalance = 0;
let currentGalleryImages = [];
let currentGalleryIndex = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeHotelBookings();
});

async function initializeHotelBookings() {
    try {
        await Promise.all([
            loadHotels(),
            loadMarkets(),
            loadWalletBalance(),
            loadBookingsList()
        ]);

        setupEventListeners();
        setDefaultDates();

    } catch (error) {
        console.error('Error initializing hotel bookings:', error);
    }
}

function setupEventListeners() {
    const searchForm = document.getElementById('hotelSearchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            searchHotelRooms();
        });
    }

    const childrenInput = document.getElementById('search_children');
    if (childrenInput) {
        childrenInput.addEventListener('change', function() {
            updateChildAgesInputs(parseInt(this.value) || 0);
        });
    }

    const bonusInput = document.getElementById('bonus_amount');
    if (bonusInput) {
        bonusInput.addEventListener('input', function() {
            updatePriceSummary();
        });
    }

    // Keyboard navigation for gallery
    document.addEventListener('keydown', function(e) {
        const galleryModal = document.getElementById('imageGalleryModal');
        if (galleryModal && galleryModal.classList.contains('show')) {
            if (e.key === 'ArrowLeft') prevGalleryImage();
            else if (e.key === 'ArrowRight') nextGalleryImage();
            else if (e.key === 'Escape') closeGalleryModal();
        }
    });
}

function setDefaultDates() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dayAfter = new Date(tomorrow);
    dayAfter.setDate(dayAfter.getDate() + 3);

    const checkinInput = document.getElementById('search_checkin');
    const checkoutInput = document.getElementById('search_checkout');

    if (checkinInput) {
        checkinInput.value = formatDateForInput(tomorrow);
        checkinInput.min = formatDateForInput(today);
    }
    if (checkoutInput) {
        checkoutInput.value = formatDateForInput(dayAfter);
        checkoutInput.min = formatDateForInput(tomorrow);
    }
}

function formatDateForInput(date) {
    return date.toISOString().split('T')[0];
}

function formatDateForAPI(dateStr) {
    const parts = dateStr.split('-');
    return `${parts[2]}.${parts[1]}.${parts[0]}`;
}

function formatDateDisplay(dateStr) {
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

// Data loading functions
async function loadHotels() {
    try {
        const result = await apiCall('/agency/api/hotel-bookings/hotels');
        if (result && result.success) {
            hotelsData = result.data || [];
            populateHotelsDropdown();
        }
    } catch (error) {
        console.error('Error loading hotels:', error);
    }
}

async function loadMarkets() {
    try {
        const result = await apiCall('/agency/api/hotel-bookings/markets');
        if (result && result.success) {
            marketsData = result.data || [];
            populateMarketsDropdown(result.default_market_id);
        }
    } catch (error) {
        console.error('Error loading markets:', error);
    }
}

async function loadWalletBalance() {
    try {
        const result = await apiCall('/agency/api/hotel-bookings/wallet-balance');
        if (result && result.success) {
            walletBalance = result.data.balance || 0;
            updateBonusDisplay();
        }
    } catch (error) {
        console.error('Error loading wallet balance:', error);
    }
}

async function loadBookingsList() {
    try {
        const result = await apiCall('/agency/api/hotel-bookings/list');
        if (result && result.success) {
            const bookings = result.data.bookings || [];
            const stats = result.data.stats || {};
            updateStats(stats);
            displayBookingsTable(bookings);
        }
    } catch (error) {
        console.error('Error loading bookings list:', error);
    }
}

// Make loadBookings global for refresh button
window.loadBookings = loadBookingsList;

function updateStats(stats) {
    const totalEl = document.getElementById('stat-total');
    const pendingEl = document.getElementById('stat-pending');
    const confirmedEl = document.getElementById('stat-confirmed');

    if (totalEl) totalEl.textContent = stats.total || 0;
    if (pendingEl) pendingEl.textContent = stats.pending || 0;
    if (confirmedEl) confirmedEl.textContent = stats.confirmed || 0;
}

function updateBonusDisplay() {
    const bonusElement = document.getElementById('stat-bonus');
    if (bonusElement) bonusElement.textContent = walletBalance.toFixed(2);

    const availableElement = document.getElementById('availableBonusAmount');
    if (availableElement) availableElement.textContent = walletBalance.toFixed(2);

    const bonusInput = document.getElementById('bonus_amount');
    if (bonusInput) bonusInput.max = walletBalance;
}

function displayBookingsTable(bookings) {
    const tbody = document.getElementById('bookings-tbody');
    if (!tbody) return;

    if (!bookings || bookings.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center text-muted py-4">
                    <i class="fas fa-inbox fa-2x mb-2"></i>
                    <div>No hotel bookings yet</div>
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    bookings.forEach(booking => {
        const stateClass = getStateClass(booking.state);
        const stateLabel = getStateLabel(booking.state);

        html += `
            <tr>
                <td><strong>${booking.booking_code || '-'}</strong></td>
                <td>${booking.hotel_name || '-'}</td>
                <td>${booking.room_name || '-'}</td>
                <td>${booking.guest_name || '-'}</td>
                <td>${booking.checkin_date || '-'}</td>
                <td>${booking.checkout_date || '-'}</td>
                <td><strong>${(booking.final_total || 0).toFixed(2)} ${booking.currency || 'EUR'}</strong></td>
                <td>${booking.bonus_used > 0 ? booking.bonus_used.toFixed(2) : '-'}</td>
                <td><span class="badge ${stateClass}">${stateLabel}</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewBookingDetails(${booking.id})" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${['draft', 'pending'].includes(booking.state) ? `
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteBooking(${booking.id})" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function getStateClass(state) {
    switch (state) {
        case 'pending': return 'bg-warning text-dark';
        case 'confirmed': return 'bg-success';
        case 'cancelled': return 'bg-danger';
        case 'completed': return 'bg-info';
        default: return 'bg-secondary';
    }
}

function getStateLabel(state) {
    switch (state) {
        case 'pending': return 'Pending';
        case 'confirmed': return 'Confirmed';
        case 'cancelled': return 'Cancelled';
        case 'completed': return 'Completed';
        case 'draft': return 'Draft';
        default: return state || 'Unknown';
    }
}

function populateHotelsDropdown() {
    const select = document.getElementById('search_hotel_id');
    if (!select) return;

    select.innerHTML = '<option value="">Select Hotel</option>';
    hotelsData.forEach(hotel => {
        const option = document.createElement('option');
        option.value = hotel.id;
        option.textContent = `${hotel.name}${hotel.category ? ' (' + hotel.category + '*)' : ''}${hotel.city ? ' - ' + hotel.city : ''}`;
        select.appendChild(option);
    });
}

function populateMarketsDropdown(defaultMarketId) {
    const select = document.getElementById('search_market_id');
    if (!select) return;

    select.innerHTML = '<option value="">Select Market</option>';
    marketsData.forEach(market => {
        const option = document.createElement('option');
        option.value = market.id;
        option.textContent = market.name;
        if (market.id === defaultMarketId) option.selected = true;
        select.appendChild(option);
    });
}

function updateChildAgesInputs(count) {
    const container = document.getElementById('childAgesContainer');
    const inputs = document.getElementById('childAgesInputs');

    if (count > 0) {
        container.style.display = 'block';
        inputs.innerHTML = '';
        for (let i = 0; i < count; i++) {
            inputs.innerHTML += `
                <div class="col-md-3 mb-2">
                    <input type="number" class="form-control child-age-input"
                           placeholder="Child ${i + 1} age" min="0" max="17" value="5"/>
                </div>
            `;
        }
    } else {
        container.style.display = 'none';
        inputs.innerHTML = '';
    }
}

// Modal functions
window.openNewBookingModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('newBookingModal'));
    document.getElementById('hotelSearchForm').reset();
    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('searchProgress').style.display = 'none';
    setDefaultDates();
    updateChildAgesInputs(0);
    modal.show();
};

// Search function
async function searchHotelRooms() {
    const hotelId = document.getElementById('search_hotel_id').value;
    const marketId = document.getElementById('search_market_id').value;
    const checkin = document.getElementById('search_checkin').value;
    const checkout = document.getElementById('search_checkout').value;
    const adults = parseInt(document.getElementById('search_adults').value) || 2;
    const children = parseInt(document.getElementById('search_children').value) || 0;

    if (!hotelId || !marketId || !checkin || !checkout) {
        Swal.fire('Error', 'Please fill all required fields', 'error');
        return;
    }

    const childAges = [];
    document.querySelectorAll('.child-age-input').forEach(input => {
        childAges.push(parseInt(input.value) || 5);
    });

    document.getElementById('searchProgress').style.display = 'block';
    document.getElementById('searchResults').style.display = 'none';

    try {
        const result = await apiCall('/agency/api/hotel-bookings/search', {
            hotel_id: hotelId,
            market_id: marketId,
            checkin: formatDateForAPI(checkin),
            checkout: formatDateForAPI(checkout),
            adults: adults,
            children: children,
            child_ages: childAges
        });

        document.getElementById('searchProgress').style.display = 'none';

        if (result && result.success) {
            searchResults = result.data;
            searchResults._searchParams = {
                hotel_id: hotelId,
                market_id: marketId,
                checkin: formatDateForAPI(checkin),
                checkout: formatDateForAPI(checkout),
                checkin_display: checkin,
                checkout_display: checkout,
                adults: adults,
                children: children,
                child_ages: childAges
            };
            displaySearchResults(searchResults);
        } else {
            Swal.fire('Error', result?.error || 'Search failed', 'error');
        }
    } catch (error) {
        document.getElementById('searchProgress').style.display = 'none';
        console.error('Search error:', error);
        Swal.fire('Error', 'An error occurred during search', 'error');
    }
}

function displaySearchResults(results) {
    const container = document.getElementById('roomResultsContainer');
    const resultsDiv = document.getElementById('searchResults');

    if (!results || !results.rooms || results.rooms.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>
                No rooms available for selected dates and criteria.
            </div>
        `;
        resultsDiv.style.display = 'block';
        return;
    }

    const currency = results.currency || 'EUR';
    let html = `
        <div class="hotel-info-header mb-3 p-2 bg-light rounded">
            <h6 class="mb-0">
                <i class="fas fa-hotel me-2"></i>${results.hotel.name}
                <span class="text-muted fw-normal">- ${results.hotel.destination || ''}</span>
            </h6>
        </div>
    `;

    results.rooms.forEach((room, roomIndex) => {
        const hasRates = room.rate_results && room.rate_results.length > 0;
        const imageCount = 1 + (room.room_gallery_images ? room.room_gallery_images.length : 0);

        html += `
            <div class="room-card mb-3" data-room-index="${roomIndex}">
                <div class="row g-0">
                    <!-- Room Image -->
                    <div class="col-md-2">
                        <div class="room-image-wrapper position-relative" style="cursor:pointer;" onclick="openGallery(${roomIndex})">
                            ${room.room_master_image
                                ? `<img src="${room.room_master_image}" alt="${room.room_name}" class="img-fluid rounded-start" style="height:120px; width:100%; object-fit:cover;"/>`
                                : `<div class="bg-light d-flex align-items-center justify-content-center rounded-start" style="height:120px;">
                                     <i class="fas fa-bed fa-2x text-muted"></i>
                                   </div>`
                            }
                            ${imageCount > 1 ? `
                                <span class="position-absolute bottom-0 end-0 badge bg-dark m-1">
                                    <i class="fas fa-images me-1"></i>${imageCount}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                    <!-- Room Info -->
                    <div class="col-md-3">
                        <div class="p-2">
                            <h6 class="mb-1">${room.room_name || 'Room'}</h6>
                            <div class="small text-muted">
                                <span class="me-2"><i class="fas fa-users"></i> ${room.room_max_adult || '-'} Ad</span>
                                <span><i class="fas fa-child"></i> ${room.room_max_child || '-'} Ch</span>
                            </div>
                            ${room.room_code ? `<span class="badge bg-secondary mt-1">${room.room_code}</span>` : ''}
                        </div>
                    </div>
                    <!-- Rates -->
                    <div class="col-md-7">
                        <div class="p-2">
        `;

        if (hasRates) {
            room.rate_results.forEach((rate, rateIndex) => {
                const totalAmount = rate.total_amount || 0;
                const finalAmount = rate.final_amount || totalAmount;
                const discount = rate.total_discount || 0;
                const hasDiscount = discount > 0;
                const discountPercent = hasDiscount && totalAmount > 0 ? Math.round((discount / totalAmount) * 100) : 0;
                const boardName = rate.rate_board || rate.rate_name || 'Room Only';

                html += `
                    <div class="d-flex justify-content-between align-items-center py-1 border-bottom">
                        <div>
                            <i class="fas fa-utensils text-muted me-1"></i>
                            <span>${boardName}</span>
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            ${hasDiscount ? `<span class="text-decoration-line-through text-muted small">${totalAmount.toFixed(0)}</span>` : ''}
                            <strong class="text-primary">${finalAmount.toFixed(2)} ${currency}</strong>
                            ${hasDiscount ? `<span class="badge bg-success">-${discountPercent}%</span>` : ''}
                            <button class="btn btn-sm btn-primary" onclick="selectRate(${roomIndex}, ${rateIndex})">
                                <i class="fas fa-check me-1"></i>Book
                            </button>
                        </div>
                    </div>
                `;
            });
        } else {
            html += `<div class="text-muted small">No rates available</div>`;
        }

        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    resultsDiv.style.display = 'block';
}

// Gallery functions
window.openGallery = function(roomIndex) {
    if (!searchResults || !searchResults.rooms) return;

    const room = searchResults.rooms[roomIndex];
    currentGalleryImages = [];
    currentGalleryIndex = 0;

    if (room.room_master_image) {
        currentGalleryImages.push({ url: room.room_master_image, name: room.room_name + ' - Main' });
    }

    if (room.room_gallery_images && room.room_gallery_images.length > 0) {
        room.room_gallery_images.forEach((img, idx) => {
            currentGalleryImages.push({
                url: `/web/image/${img.id}`,
                name: img.name || `Image ${idx + 1}`
            });
        });
    }

    if (currentGalleryImages.length === 0) return;

    // Create gallery modal if not exists
    let galleryModal = document.getElementById('imageGalleryModal');
    if (!galleryModal) {
        const modalHtml = `
            <div class="modal fade" id="imageGalleryModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content bg-dark">
                        <div class="modal-header border-0">
                            <h6 class="modal-title text-white" id="galleryRoomName"></h6>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-0 position-relative">
                            <div class="text-center">
                                <img src="" alt="" id="galleryMainImage" class="img-fluid" style="max-height:60vh;"/>
                            </div>
                            <button class="btn btn-dark position-absolute start-0 top-50 translate-middle-y" onclick="prevGalleryImage()" style="z-index:10;">
                                <i class="fas fa-chevron-left"></i>
                            </button>
                            <button class="btn btn-dark position-absolute end-0 top-50 translate-middle-y" onclick="nextGalleryImage()" style="z-index:10;">
                                <i class="fas fa-chevron-right"></i>
                            </button>
                            <div class="text-center text-white py-2" id="galleryCounter"></div>
                        </div>
                        <div class="modal-footer border-0 justify-content-center p-2" id="galleryThumbnails" style="gap:5px;">
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        galleryModal = document.getElementById('imageGalleryModal');
    }

    document.getElementById('galleryRoomName').textContent = room.room_name || 'Room Gallery';

    const thumbsContainer = document.getElementById('galleryThumbnails');
    thumbsContainer.innerHTML = currentGalleryImages.map((img, idx) => `
        <img src="${img.url}" alt="${img.name}" onclick="goToGalleryImage(${idx})"
             class="rounded ${idx === 0 ? 'border border-primary' : ''}"
             style="width:60px; height:40px; object-fit:cover; cursor:pointer;" data-index="${idx}"/>
    `).join('');

    updateGalleryImage();
    new bootstrap.Modal(galleryModal).show();
};

function updateGalleryImage() {
    if (currentGalleryImages.length === 0) return;

    const img = currentGalleryImages[currentGalleryIndex];
    document.getElementById('galleryMainImage').src = img.url;
    document.getElementById('galleryCounter').textContent = `${currentGalleryIndex + 1} / ${currentGalleryImages.length}`;

    document.querySelectorAll('#galleryThumbnails img').forEach((thumb, idx) => {
        thumb.classList.toggle('border', idx === currentGalleryIndex);
        thumb.classList.toggle('border-primary', idx === currentGalleryIndex);
    });
}

window.prevGalleryImage = function() {
    if (currentGalleryImages.length <= 1) return;
    currentGalleryIndex = (currentGalleryIndex - 1 + currentGalleryImages.length) % currentGalleryImages.length;
    updateGalleryImage();
};

window.nextGalleryImage = function() {
    if (currentGalleryImages.length <= 1) return;
    currentGalleryIndex = (currentGalleryIndex + 1) % currentGalleryImages.length;
    updateGalleryImage();
};

window.goToGalleryImage = function(index) {
    currentGalleryIndex = index;
    updateGalleryImage();
};

function closeGalleryModal() {
    const galleryModal = document.getElementById('imageGalleryModal');
    if (galleryModal) {
        const modal = bootstrap.Modal.getInstance(galleryModal);
        if (modal) modal.hide();
    }
}

// Rate selection
window.selectRate = function(roomIndex, rateIndex) {
    if (!searchResults || !searchResults.rooms) return;

    selectedRoom = searchResults.rooms[roomIndex];
    selectedRate = selectedRoom.rate_results[rateIndex];

    if (!selectedRoom || !selectedRate) {
        console.error('Room or rate not found');
        return;
    }

    openBookingModal();
};

function openBookingModal() {
    const params = searchResults._searchParams;
    const checkin = params.checkin_display;
    const checkout = params.checkout_display;
    const adults = params.adults;
    const children = params.children;

    const checkinDate = new Date(checkin);
    const checkoutDate = new Date(checkout);
    const nights = Math.ceil((checkoutDate - checkinDate) / (1000 * 60 * 60 * 24));

    const totalAmount = selectedRate.total_amount || 0;
    const finalAmount = selectedRate.final_amount || totalAmount;
    const discount = selectedRate.total_discount || 0;
    const currency = selectedRate.currency || searchResults.currency || 'EUR';
    const boardName = selectedRate.rate_board || selectedRate.rate_name || 'Room Only';

    const summaryDiv = document.getElementById('selectedRoomSummary');
    summaryDiv.innerHTML = `
        <div class="row">
            <div class="col-md-3">
                ${selectedRoom.room_master_image
                    ? `<img src="${selectedRoom.room_master_image}" alt="${selectedRoom.room_name}" class="img-fluid rounded"/>`
                    : `<div class="bg-light rounded p-4 text-center"><i class="fas fa-bed fa-2x text-muted"></i></div>`
                }
            </div>
            <div class="col-md-5">
                <h6><i class="fas fa-hotel me-2"></i>${searchResults.hotel.name}</h6>
                <p class="mb-1"><strong>${selectedRoom.room_name || 'Room'}</strong></p>
                <p class="mb-1"><span class="badge bg-primary">${boardName}</span></p>
                <small class="text-muted">
                    <i class="fas fa-calendar me-1"></i>
                    ${formatDateDisplay(checkin)} - ${formatDateDisplay(checkout)} (${nights} nights)
                </small>
                <div class="mt-1">
                    <small class="text-muted">
                        <i class="fas fa-users me-1"></i>
                        ${adults} Adults${children > 0 ? `, ${children} Children` : ''}
                    </small>
                </div>
            </div>
            <div class="col-md-4 text-end">
                ${discount > 0 ? `
                    <p class="mb-0 text-muted text-decoration-line-through">${totalAmount.toFixed(2)} ${currency}</p>
                    <span class="badge bg-success mb-1">-${Math.round((discount / totalAmount) * 100)}% Discount</span>
                ` : ''}
                <h4 class="text-primary mb-0">${finalAmount.toFixed(2)} ${currency}</h4>
            </div>
        </div>
    `;

    selectedRoom._bookingParams = {
        hotel_id: searchResults.hotel.id,
        room_id: selectedRoom.room_id,
        rate_id: selectedRate.rate_id,
        market_id: params.market_id,
        checkin: params.checkin,
        checkout: params.checkout,
        adults: adults,
        children: children,
        child_ages: params.child_ages,
        roomTotal: finalAmount,
        originalTotal: totalAmount,
        discount: discount,
        currency: currency,
        board_name: boardName
    };

    document.getElementById('summaryRoomTotal').textContent = totalAmount.toFixed(2) + ' ' + currency;
    document.getElementById('summaryDiscount').textContent = '-' + discount.toFixed(2) + ' ' + currency;

    const maxBonus = Math.min(walletBalance, finalAmount);
    document.getElementById('bonus_amount').max = maxBonus;
    document.getElementById('bonus_amount').value = 0;

    updatePriceSummary();

    document.getElementById('guest_name').value = '';
    document.getElementById('guest_surname').value = '';
    document.getElementById('guest_email').value = '';
    document.getElementById('guest_phone').value = '';
    document.getElementById('special_requests').value = '';

    const searchModal = bootstrap.Modal.getInstance(document.getElementById('newBookingModal'));
    if (searchModal) searchModal.hide();

    new bootstrap.Modal(document.getElementById('roomSelectionModal')).show();
}

function updatePriceSummary() {
    if (!selectedRoom || !selectedRoom._bookingParams) return;

    const originalTotal = selectedRoom._bookingParams.originalTotal;
    const roomTotal = selectedRoom._bookingParams.roomTotal;
    const discount = selectedRoom._bookingParams.discount;
    const currency = selectedRoom._bookingParams.currency;
    const bonusUsed = parseFloat(document.getElementById('bonus_amount').value) || 0;

    if (bonusUsed > walletBalance) {
        document.getElementById('bonus_amount').value = walletBalance;
        return updatePriceSummary();
    }

    if (bonusUsed > roomTotal) {
        document.getElementById('bonus_amount').value = roomTotal;
        return updatePriceSummary();
    }

    const finalTotal = roomTotal - bonusUsed;

    document.getElementById('summaryRoomTotal').textContent = originalTotal.toFixed(2) + ' ' + currency;
    document.getElementById('summaryDiscount').textContent = '-' + discount.toFixed(2) + ' ' + currency;
    document.getElementById('summaryBonus').textContent = '-' + bonusUsed.toFixed(2) + ' ' + currency;
    document.getElementById('summaryFinalTotal').textContent = finalTotal.toFixed(2) + ' ' + currency;
}

// Booking submission
window.submitBooking = async function() {
    if (!selectedRoom || !selectedRoom._bookingParams) {
        Swal.fire('Error', 'Please select a room first', 'error');
        return;
    }

    const guestName = document.getElementById('guest_name').value.trim();
    const guestSurname = document.getElementById('guest_surname').value.trim();

    if (!guestName || !guestSurname) {
        Swal.fire('Error', 'Please enter guest name and surname', 'error');
        return;
    }

    const params = selectedRoom._bookingParams;
    const bonusUsed = parseFloat(document.getElementById('bonus_amount').value) || 0;
    const finalTotal = params.roomTotal - bonusUsed;

    const bookingData = {
        hotel_id: params.hotel_id,
        room_id: params.room_id,
        rate_id: params.rate_id,
        market_id: params.market_id,
        checkin: params.checkin,
        checkout: params.checkout,
        adults: params.adults,
        children: params.children,
        child_ages: params.child_ages,
        guest_name: guestName,
        guest_surname: guestSurname,
        guest_email: document.getElementById('guest_email').value || '',
        guest_phone: document.getElementById('guest_phone').value || '',
        special_requests: document.getElementById('special_requests').value || '',
        room_total: params.originalTotal,
        discount: params.discount,
        bonus_used: bonusUsed,
        final_total: finalTotal,
        currency: params.currency
    };

    try {
        Swal.fire({
            title: 'Creating Booking...',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        const result = await apiCall('/agency/api/hotel-bookings/create', bookingData);

        if (result && result.success) {
            Swal.fire({
                icon: 'success',
                title: 'Booking Created!',
                text: `Booking Code: ${result.data.booking_code}`,
                confirmButtonText: 'OK'
            }).then(() => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('roomSelectionModal'));
                modal.hide();
                loadBookingsList();
                loadWalletBalance();
            });
        } else {
            Swal.fire('Error', result?.error || 'Booking creation failed', 'error');
        }
    } catch (error) {
        console.error('Booking error:', error);
        Swal.fire('Error', 'An error occurred while creating booking', 'error');
    }
};

// View booking details
window.viewBookingDetails = async function(bookingId) {
    try {
        Swal.fire({
            title: 'Loading...',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        const result = await apiCall('/agency/api/hotel-bookings/detail', { booking_id: bookingId });
        Swal.close();

        if (result && result.success) {
            showBookingDetailModal(result.data);
        } else {
            Swal.fire('Error', result?.error || 'Failed to load booking details', 'error');
        }
    } catch (error) {
        console.error('Error loading booking details:', error);
        Swal.fire('Error', 'An error occurred', 'error');
    }
};

function showBookingDetailModal(booking) {
    const content = document.getElementById('bookingDetailContent');
    const stateClass = getStateClass(booking.state);
    const stateLabel = getStateLabel(booking.state);

    content.innerHTML = `
        <div class="row mb-3">
            <div class="col-md-6">
                <h6 class="text-muted mb-1">Booking Code</h6>
                <h4>${booking.booking_code}</h4>
            </div>
            <div class="col-md-6 text-end">
                <span class="badge ${stateClass} fs-6">${stateLabel}</span>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header bg-light">
                <i class="fas fa-hotel me-2"></i>Hotel Information
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p class="mb-1"><strong>Hotel:</strong> ${booking.hotel_name || '-'}</p>
                        <p class="mb-1"><strong>Room:</strong> ${booking.room_name || '-'}</p>
                        <p class="mb-0"><strong>Rate:</strong> ${booking.rate_name || '-'}</p>
                    </div>
                    <div class="col-md-6">
                        <p class="mb-1"><strong>Check-in:</strong> ${booking.checkin_date || '-'}</p>
                        <p class="mb-1"><strong>Check-out:</strong> ${booking.checkout_date || '-'}</p>
                        <p class="mb-0"><strong>Guests:</strong> ${booking.adult_count} Adults${booking.child_count > 0 ? ', ' + booking.child_count + ' Children' : ''}</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header bg-light">
                <i class="fas fa-user me-2"></i>Guest Information
            </div>
            <div class="card-body">
                <p class="mb-1"><strong>Name:</strong> ${booking.guest_name} ${booking.guest_surname}</p>
                <p class="mb-1"><strong>Email:</strong> ${booking.guest_email || '-'}</p>
                <p class="mb-0"><strong>Phone:</strong> ${booking.guest_phone || '-'}</p>
            </div>
        </div>

        <div class="card">
            <div class="card-header bg-light">
                <i class="fas fa-calculator me-2"></i>Price Summary
            </div>
            <div class="card-body">
                <div class="d-flex justify-content-between mb-1">
                    <span>Room Total:</span>
                    <span>${(booking.room_total || 0).toFixed(2)} ${booking.currency || 'EUR'}</span>
                </div>
                ${booking.discount_amount > 0 ? `
                <div class="d-flex justify-content-between mb-1 text-success">
                    <span>Discount:</span>
                    <span>-${booking.discount_amount.toFixed(2)} ${booking.currency || 'EUR'}</span>
                </div>
                ` : ''}
                ${booking.bonus_used > 0 ? `
                <div class="d-flex justify-content-between mb-1 text-warning">
                    <span>Bonus Used:</span>
                    <span>-${booking.bonus_used.toFixed(2)} ${booking.currency || 'EUR'}</span>
                </div>
                ` : ''}
                <hr class="my-2"/>
                <div class="d-flex justify-content-between">
                    <strong>Final Total:</strong>
                    <strong class="text-primary">${(booking.final_total || 0).toFixed(2)} ${booking.currency || 'EUR'}</strong>
                </div>
            </div>
        </div>
    `;

    new bootstrap.Modal(document.getElementById('bookingDetailModal')).show();
}

// Delete booking
window.deleteBooking = async function(bookingId) {
    const result = await Swal.fire({
        title: 'Delete Booking?',
        html: 'Are you sure you want to delete this booking?<br><small class="text-muted">If bonus was used, it will be refunded.</small>',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        confirmButtonText: 'Yes, Delete',
        cancelButtonText: 'Cancel'
    });

    if (!result.isConfirmed) return;

    try {
        Swal.fire({
            title: 'Deleting...',
            allowOutsideClick: false,
            didOpen: () => Swal.showLoading()
        });

        const apiResult = await apiCall('/agency/api/hotel-bookings/delete', { booking_id: bookingId });

        if (apiResult && apiResult.success) {
            const bonusMsg = apiResult.bonus_refunded > 0
                ? `\nBonus refunded: ${apiResult.bonus_refunded.toFixed(2)} EUR`
                : '';

            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Booking deleted successfully.' + bonusMsg,
                timer: 2000,
                showConfirmButton: false
            }).then(() => {
                loadBookingsList();
                loadWalletBalance();
            });
        } else {
            Swal.fire('Error', apiResult?.error || 'Failed to delete booking', 'error');
        }
    } catch (error) {
        console.error('Error deleting booking:', error);
        Swal.fire('Error', 'An error occurred', 'error');
    }
};
