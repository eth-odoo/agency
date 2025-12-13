/**
 * Bonus Reservation Management JavaScript
 * ETH Agency Portal Module
 */

(function() {
    'use strict';

    // Global variables
    let hotels = [];
    let operators = [];
    let markets = [];
    let roomsByHotel = {};
    let masterDataLoaded = false;
    let isLoadingData = false;
    let defaultMarketId = null;
    let isSingleMarket = false;
    let reservationsData = {};
    let extractedVoucherData = null;

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Initializing Bonus Reservation Module...');

        const mountPoint = document.getElementById('bonus-reservation-app');
        if (mountPoint) {
            // Create the interface
            mountPoint.innerHTML = `
                <div class="bonus-header">
                    <h2><i class="fas fa-star me-2"></i>Bonus Reservation Management</h2>
                    <p class="mb-0">Manage your bonus hotel reservations and commissions</p>
                </div>

                <div class="row mt-4">
                    <div class="col-md-3">
                        <div class="bonus-stats-card">
                            <h5 class="text-muted">Total Reservations</h5>
                            <h2 class="text-primary" id="stat-total">0</h2>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="bonus-stats-card">
                            <h5 class="text-muted">Pending</h5>
                            <h2 class="text-warning" id="stat-pending">0</h2>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="bonus-stats-card">
                            <h5 class="text-muted">Balanced</h5>
                            <h2 class="text-success" id="stat-balanced">0</h2>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="bonus-stats-card">
                            <h5 class="text-muted">Total Bonus</h5>
                            <h2 class="text-info" id="stat-bonus">0</h2>
                        </div>
                    </div>
                </div>

                <div class="mt-4">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4>Reservations</h4>
                        <div>
                            <button class="btn btn-success me-2" onclick="createNewReservationFromVoucher()">
                                <i class="fas fa-file-upload me-2"></i>New Reservation From Voucher File
                            </button>
                            <button class="btn btn-primary" onclick="createNewReservation()">
                                <i class="fas fa-plus me-2"></i>New Reservation
                            </button>
                        </div>
                    </div>

                    <div class="bonus-table">
                        <table class="table table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Reservation Code</th>
                                    <th>Guest Name</th>
                                    <th>Hotel</th>
                                    <th>Operator</th>
                                    <th>Market</th>
                                    <th>Check-in</th>
                                    <th>Check-out</th>
                                    <th>Amount</th>
                                    <th>Bonus</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="reservations-tbody">
                                <tr>
                                    <td colspan="11" class="text-center text-muted py-4">
                                        Loading reservations...
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            // Load initial data
            loadMasterData().then(() => {
                console.log('Master data loaded successfully');
                loadBonusReservations();
            }).catch(err => {
                console.error('Error loading master data:', err);
                loadBonusReservations();
            });
        }
    });

    function setDateConstraints(prefix = '') {
        const today = new Date().toISOString().split('T')[0];

        const bookingDateInput = document.getElementById(prefix + 'booking_date');
        if (bookingDateInput) {
            bookingDateInput.max = today;
            if (!prefix) {
                bookingDateInput.value = today;
            }
        }

        const checkinInput = document.getElementById(prefix + 'checkin_date');
        if (checkinInput) {
            checkinInput.max = today;
        }

        const checkoutInput = document.getElementById(prefix + 'checkout_date');
        if (checkoutInput) {
            checkoutInput.max = today;
        }
    }

    function formatDateTime(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString('tr-TR');
    }

    function loadMasterData() {
        if (isLoadingData) return Promise.resolve();
        isLoadingData = true;

        return Promise.all([
            loadAgencyHotels(),
            loadOperators(),
            loadMarkets()
        ]).then(() => {
            masterDataLoaded = true;
            isLoadingData = false;
        });
    }

    function loadAgencyHotels() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/agency/api/agency-hotels',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}, id: Date.now()}),
                success: function(response) {
                    if (response.result && response.result.success) {
                        hotels = response.result.data.hotels || [];
                        console.log('Agency hotels loaded:', hotels.length);

                        // Load rooms for each hotel
                        hotels.forEach(hotel => loadHotelRooms(hotel.id));

                        populateHotelsDropdown();
                        populateEditHotelsDropdown();
                        resolve();
                    } else {
                        console.error('Failed to load hotels');
                        reject('Failed to load hotels');
                    }
                },
                error: reject
            });
        });
    }

    function loadHotelRooms(hotelId) {
        $.ajax({
            url: '/agency/api/hotel-rooms',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {hotel_id: hotelId}, id: Date.now()}),
            success: function(response) {
                if (response.result && response.result.success) {
                    roomsByHotel[hotelId] = response.result.data.rooms || [];
                    console.log('Rooms loaded for hotel', hotelId, ':', roomsByHotel[hotelId].length);

                    // Update rooms dropdown if this is the currently selected hotel
                    const hotelSelect = document.getElementById('hotel_id');
                    if (hotelSelect && hotelSelect.value == hotelId) {
                        populateRoomsDropdown(hotelId);
                    }

                    const editHotelSelect = document.getElementById('edit_hotel_id');
                    if (editHotelSelect && editHotelSelect.value == hotelId) {
                        populateEditRoomsDropdown(hotelId);
                    }

                    const previewHotelSelect = document.getElementById('preview_hotel_id');
                    if (previewHotelSelect && previewHotelSelect.value == hotelId) {
                        populatePreviewRoomsDropdown(hotelId);
                    }
                }
            }
        });
    }

    function loadOperators() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/agency/api/operators',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}, id: Date.now()}),
                success: function(response) {
                    if (response.result && response.result.success) {
                        operators = response.result.data.operators || [];
                        console.log('Operators loaded:', operators.length);
                        populateOperatorsDropdown();
                        populateEditOperatorsDropdown();
                        resolve();
                    } else {
                        reject('Failed to load operators');
                    }
                },
                error: reject
            });
        });
    }

    function loadMarkets() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: '/agency/api/markets',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}, id: Date.now()}),
                success: function(response) {
                    if (response.result && response.result.success) {
                        markets = response.result.data.markets || [];
                        defaultMarketId = response.result.data.default_market_id || null;
                        isSingleMarket = response.result.data.is_single_market || false;
                        console.log('Markets loaded:', markets.length, 'Default:', defaultMarketId, 'Single:', isSingleMarket);
                        populateMarketsDropdown();
                        populateEditMarketsDropdown();
                        resolve();
                    } else {
                        reject('Failed to load markets');
                    }
                },
                error: reject
            });
        });
    }

    // ==================== Dropdown Population ====================

    function populateHotelsDropdown() {
        const select = document.getElementById('hotel_id');
        if (select) {
            select.innerHTML = '<option value="">Select Hotel</option>';
            hotels.forEach((hotel, index) => {
                const option = document.createElement('option');
                option.value = hotel.id;
                option.textContent = hotel.name;
                if (index === 0) option.selected = true;
                select.appendChild(option);
            });

            if (hotels.length > 0) {
                const firstHotelId = hotels[0].id;
                if (roomsByHotel[firstHotelId]) {
                    populateRoomsDropdown(firstHotelId);
                } else {
                    loadHotelRooms(firstHotelId);
                }
            }
        }
    }

    function populateRoomsDropdown(hotelId) {
        const select = document.getElementById('room_id');
        if (select) {
            select.innerHTML = '<option value="">Select Room Type</option>';
            const rooms = roomsByHotel[hotelId] || [];
            rooms.forEach(room => {
                const option = document.createElement('option');
                option.value = room.id;
                option.textContent = room.name;
                select.appendChild(option);
            });
        }
    }

    function populateOperatorsDropdown() {
        const select = document.getElementById('operator_id');
        if (select) {
            select.innerHTML = '<option value="">Select Operator</option>';
            operators.forEach(op => {
                const option = document.createElement('option');
                option.value = op.id;
                option.textContent = op.name;
                select.appendChild(option);
            });
        }
    }

    function populateMarketsDropdown() {
        const select = document.getElementById('market_id');
        if (select) {
            select.innerHTML = '<option value="">Select Market</option>';
            markets.forEach(market => {
                const option = document.createElement('option');
                option.value = market.id;
                option.textContent = market.name + ' (' + (market.currency || 'USD') + ')';
                if (defaultMarketId && market.id === defaultMarketId) option.selected = true;
                select.appendChild(option);
            });
            select.disabled = isSingleMarket;
        }
    }

    function populateEditHotelsDropdown(selectedId) {
        const select = document.getElementById('edit_hotel_id');
        if (select) {
            select.innerHTML = '<option value="">Select Hotel</option>';
            hotels.forEach(hotel => {
                const option = document.createElement('option');
                option.value = hotel.id;
                option.textContent = hotel.name;
                if (selectedId && hotel.id == selectedId) option.selected = true;
                select.appendChild(option);
            });
        }
    }

    function populateEditRoomsDropdown(hotelId, selectedId) {
        const select = document.getElementById('edit_room_id');
        if (select) {
            select.innerHTML = '<option value="">Select Room Type</option>';
            const rooms = roomsByHotel[hotelId] || [];
            rooms.forEach(room => {
                const option = document.createElement('option');
                option.value = room.id;
                option.textContent = room.name;
                if (selectedId && room.id == selectedId) option.selected = true;
                select.appendChild(option);
            });
        }
    }

    function populateEditOperatorsDropdown(selectedId) {
        const select = document.getElementById('edit_operator_id');
        if (select) {
            select.innerHTML = '<option value="">Select Operator</option>';
            operators.forEach(op => {
                const option = document.createElement('option');
                option.value = op.id;
                option.textContent = op.name;
                if (selectedId && op.id == selectedId) option.selected = true;
                select.appendChild(option);
            });
        }
    }

    function populateEditMarketsDropdown(selectedId) {
        const select = document.getElementById('edit_market_id');
        if (select) {
            select.innerHTML = '<option value="">Select Market</option>';
            markets.forEach(market => {
                const option = document.createElement('option');
                option.value = market.id;
                option.textContent = market.name + ' (' + (market.currency || 'USD') + ')';
                if (selectedId && market.id == selectedId) option.selected = true;
                else if (!selectedId && defaultMarketId && market.id === defaultMarketId) option.selected = true;
                select.appendChild(option);
            });
            select.disabled = isSingleMarket;
        }
    }

    // ==================== Hotel Change Handlers ====================

    window.onHotelChange = function() {
        const hotelSelect = document.getElementById('hotel_id');
        if (hotelSelect) {
            const hotelId = hotelSelect.value;
            if (hotelId) {
                if (roomsByHotel[hotelId]) {
                    populateRoomsDropdown(hotelId);
                } else {
                    const roomSelect = document.getElementById('room_id');
                    if (roomSelect) roomSelect.innerHTML = '<option value="">Loading rooms...</option>';
                    loadHotelRooms(hotelId);
                }
            } else {
                const roomSelect = document.getElementById('room_id');
                if (roomSelect) roomSelect.innerHTML = '<option value="">Select Room Type</option>';
            }
        }
    }

    window.onEditHotelChange = function() {
        const hotelSelect = document.getElementById('edit_hotel_id');
        if (hotelSelect) {
            const hotelId = hotelSelect.value;
            if (hotelId) {
                if (roomsByHotel[hotelId]) {
                    populateEditRoomsDropdown(hotelId);
                } else {
                    const roomSelect = document.getElementById('edit_room_id');
                    if (roomSelect) roomSelect.innerHTML = '<option value="">Loading rooms...</option>';
                    loadHotelRooms(hotelId);
                }
            } else {
                const roomSelect = document.getElementById('edit_room_id');
                if (roomSelect) roomSelect.innerHTML = '<option value="">Select Room Type</option>';
            }
        }
    }

    // ==================== Reservations ====================

    function loadBonusReservations() {
        $.ajax({
            url: '/agency/api/bonus-reservations',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {filters: {}}, id: Date.now()}),
            success: function(response) {
                if (response && response.result && response.result.success) {
                    const reservations = response.result.data.reservations || [];
                    reservations.forEach(res => { reservationsData[res.id] = res; });
                    displayReservations(reservations);
                } else {
                    displayReservations([]);
                }
            },
            error: function() { displayReservations([]); }
        });
    }

    function displayReservations(reservations) {
        const tbody = document.getElementById('reservations-tbody');
        if (!tbody) return;

        if (reservations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted py-4"><i class="fas fa-inbox fa-2x mb-2"></i><div>No reservations found</div></td></tr>';
            return;
        }

        tbody.innerHTML = reservations.map(res => {
            const fullName = ((res.guest_name || '') + ' ' + (res.guest_surname || '')).trim();
            const isBalanced = res.state === 'balanced';
            return `
                <tr>
                    <td>${res.reservation_code || '-'}</td>
                    <td>${fullName || '-'}</td>
                    <td>${res.hotel_name || '-'}</td>
                    <td>${res.operator_name || '-'}</td>
                    <td>${res.market_name || '-'}</td>
                    <td>${res.checkin_date || '-'}</td>
                    <td>${res.checkout_date || '-'}</td>
                    <td>${res.total_amount || 0}</td>
                    <td>${res.bonus_amount || 0}</td>
                    <td><span class="badge bg-${getStatusColor(res.state)}">${res.state || 'pending'}</span></td>
                    <td>
                        ${!isBalanced ? `
                            <button class="btn btn-sm btn-outline-primary" onclick="editReservation(${res.id})"><i class="fas fa-edit"></i></button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteReservation(${res.id})"><i class="fas fa-trash"></i></button>
                        ` : '<span class="text-muted small"><i class="fas fa-lock me-1"></i>Balanced</span>'}
                    </td>
                </tr>
            `;
        }).join('');

        updateStatistics(reservations);
    }

    function getStatusColor(status) {
        switch(status) {
            case 'balanced': return 'success';
            case 'pending': return 'warning';
            case 'rejected': return 'danger';
            default: return 'secondary';
        }
    }

    function updateStatistics(reservations) {
        document.getElementById('stat-total').textContent = reservations.length;
        document.getElementById('stat-pending').textContent = reservations.filter(r => r.state === 'pending').length;
        document.getElementById('stat-balanced').textContent = reservations.filter(r => r.state === 'balanced').length;
        document.getElementById('stat-bonus').textContent = reservations.reduce((sum, r) => sum + (r.bonus_amount || 0), 0).toFixed(2);
    }

    // ==================== Voucher File Upload ====================

    window.createNewReservationFromVoucher = function() {
        showVoucherUploadModal();
    }

    function showVoucherUploadModal() {
        let modalElement = document.getElementById('voucherUploadModal');

        if (!modalElement) {
            const modalHTML = `
                <div class="modal fade" id="voucherUploadModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title"><i class="fas fa-file-upload me-2"></i>Upload Voucher File</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label class="form-label">Select Voucher Image/PDF</label>
                                    <input type="file" class="form-control" id="voucherFile" accept="image/*,application/pdf" required>
                                    <div class="form-text">Supported formats: JPG, PNG, PDF</div>
                                </div>
                                <div id="voucherPreview" class="mt-3" style="display: none;">
                                    <h6>File Preview:</h6>
                                    <img id="voucherPreviewImage" src="" alt="Preview" class="img-fluid border rounded" style="max-height: 400px;">
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" onclick="processVoucherFile()">
                                    <i class="fas fa-arrow-right me-2"></i>Continue
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            modalElement = document.getElementById('voucherUploadModal');
        }

        // Always attach event listener (remove first to avoid duplicates)
        const fileInput = document.getElementById('voucherFile');
        if (fileInput) {
            fileInput.removeEventListener('change', handleVoucherFileSelect);
            fileInput.addEventListener('change', handleVoucherFileSelect);
            // Reset
            fileInput.value = '';
        }

        const previewDiv = document.getElementById('voucherPreview');
        if (previewDiv) {
            previewDiv.style.display = 'none';
        }

        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }

    function handleVoucherFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        const previewDiv = document.getElementById('voucherPreview');
        const previewImage = document.getElementById('voucherPreviewImage');

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                previewDiv.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            previewDiv.style.display = 'none';
        }
    }

    window.processVoucherFile = function() {
        const fileInput = document.getElementById('voucherFile');
        const file = fileInput.files[0];

        if (!file) {
            alert('Please select a voucher file first!');
            return;
        }

        // Store file data for later
        const reader = new FileReader();
        reader.onload = function(e) {
            extractedVoucherData = {
                confirmation_file: e.target.result.split(',')[1],
                confirmation_filename: file.name
            };

            // Close upload modal
            const uploadModal = bootstrap.Modal.getInstance(document.getElementById('voucherUploadModal'));
            uploadModal.hide();

            // Show preview modal
            showVoucherPreviewModal(extractedVoucherData);
        };
        reader.readAsDataURL(file);
    }

    function showVoucherPreviewModal(data) {
        let modalElement = document.getElementById('voucherPreviewModal');

        if (!modalElement) {
            const modalHTML = `
                <div class="modal fade" id="voucherPreviewModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title"><i class="fas fa-edit me-2"></i>Enter Reservation Details</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle me-2"></i>
                                    The voucher file will be attached to this reservation. Please fill in the details below.
                                </div>

                                <form id="voucherPreviewForm">
                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Guest Name *</label>
                                            <input type="text" class="form-control" id="preview_guest_name" required>
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Guest Surname *</label>
                                            <input type="text" class="form-control" id="preview_guest_surname" required>
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Hotel *</label>
                                            <select class="form-select" id="preview_hotel_id" onchange="onPreviewHotelChange()" required>
                                                <option value="">Select Hotel</option>
                                            </select>
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Room Type *</label>
                                            <select class="form-select" id="preview_room_id" required>
                                                <option value="">Select Room Type</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Operator</label>
                                            <select class="form-select" id="preview_operator_id">
                                                <option value="">Select Operator</option>
                                            </select>
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Operator Voucher No</label>
                                            <input type="text" class="form-control" id="preview_operator_voucher_no">
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Check-in Date *</label>
                                            <input type="date" class="form-control" id="preview_checkin_date" required>
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Check-out Date *</label>
                                            <input type="date" class="form-control" id="preview_checkout_date" required>
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Adults *</label>
                                            <input type="number" class="form-control" id="preview_adult_count" min="1" value="2" required>
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Children</label>
                                            <input type="number" class="form-control" id="preview_child_count" min="0" value="0">
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Rooms *</label>
                                            <input type="number" class="form-control" id="preview_room_count" min="1" value="1" required>
                                        </div>
                                        <div class="col-md-3 mb-3">
                                            <label class="form-label">Total Amount *</label>
                                            <input type="number" class="form-control" id="preview_total_amount" step="0.01" min="0" required>
                                        </div>
                                    </div>

                                    <div class="row">
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Market *</label>
                                            <select class="form-select" id="preview_market_id" required>
                                                <option value="">Select Market</option>
                                            </select>
                                        </div>
                                        <div class="col-md-6 mb-3">
                                            <label class="form-label">Notes</label>
                                            <textarea class="form-control" id="preview_notes" rows="2"></textarea>
                                        </div>
                                    </div>

                                    <div class="mb-3">
                                        <label class="form-label">Attached File</label>
                                        <div id="preview_file_info" class="border rounded p-2 bg-light">
                                            <i class="fas fa-file text-success me-2"></i>
                                            <span class="text-success fw-bold" id="preview_filename">voucher.jpg</span>
                                        </div>
                                    </div>
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="button" class="btn btn-primary" onclick="createReservationFromExtractedData()">
                                    <i class="fas fa-save me-2"></i>Create Reservation
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            modalElement = document.getElementById('voucherPreviewModal');
        }

        // Populate form
        populatePreviewForm(data);

        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }

    function populatePreviewForm(data) {
        populatePreviewHotelsDropdown();
        populatePreviewOperatorsDropdown();
        populatePreviewMarketsDropdown();
        setDateConstraints('preview_');

        document.getElementById('preview_guest_name').value = '';
        document.getElementById('preview_guest_surname').value = '';
        document.getElementById('preview_operator_voucher_no').value = '';
        document.getElementById('preview_checkin_date').value = '';
        document.getElementById('preview_checkout_date').value = '';
        document.getElementById('preview_adult_count').value = 2;
        document.getElementById('preview_child_count').value = 0;
        document.getElementById('preview_room_count').value = 1;
        document.getElementById('preview_total_amount').value = '';
        document.getElementById('preview_notes').value = '';

        if (data.confirmation_filename) {
            document.getElementById('preview_filename').textContent = data.confirmation_filename;
        }
    }

    function populatePreviewHotelsDropdown() {
        const select = document.getElementById('preview_hotel_id');
        if (select) {
            select.innerHTML = '<option value="">Select Hotel</option>';
            hotels.forEach(hotel => {
                const option = document.createElement('option');
                option.value = hotel.id;
                option.textContent = hotel.name;
                select.appendChild(option);
            });
        }
    }

    function populatePreviewOperatorsDropdown() {
        const select = document.getElementById('preview_operator_id');
        if (select) {
            select.innerHTML = '<option value="">Select Operator</option>';
            operators.forEach(op => {
                const option = document.createElement('option');
                option.value = op.id;
                option.textContent = op.name;
                select.appendChild(option);
            });
        }
    }

    function populatePreviewMarketsDropdown() {
        const select = document.getElementById('preview_market_id');
        if (select) {
            select.innerHTML = '<option value="">Select Market</option>';
            markets.forEach(market => {
                const option = document.createElement('option');
                option.value = market.id;
                option.textContent = market.name + ' (' + (market.currency || 'USD') + ')';
                if (defaultMarketId && market.id === defaultMarketId) option.selected = true;
                select.appendChild(option);
            });
        }
    }

    function populatePreviewRoomsDropdown(hotelId) {
        const select = document.getElementById('preview_room_id');
        if (select) {
            select.innerHTML = '<option value="">Select Room Type</option>';
            const rooms = roomsByHotel[hotelId] || [];
            rooms.forEach(room => {
                const option = document.createElement('option');
                option.value = room.id;
                option.textContent = room.name;
                select.appendChild(option);
            });
        }
    }

    window.onPreviewHotelChange = function() {
        const hotelSelect = document.getElementById('preview_hotel_id');
        if (hotelSelect) {
            const hotelId = hotelSelect.value;
            if (hotelId) {
                if (roomsByHotel[hotelId]) {
                    populatePreviewRoomsDropdown(hotelId);
                } else {
                    const roomSelect = document.getElementById('preview_room_id');
                    if (roomSelect) roomSelect.innerHTML = '<option value="">Loading rooms...</option>';
                    loadHotelRooms(hotelId);
                }
            } else {
                const roomSelect = document.getElementById('preview_room_id');
                if (roomSelect) roomSelect.innerHTML = '<option value="">Select Room Type</option>';
            }
        }
    }

    window.createReservationFromExtractedData = function() {
        const form = document.getElementById('voucherPreviewForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const checkinDate = document.getElementById('preview_checkin_date').value;
        const checkoutDate = document.getElementById('preview_checkout_date').value;
        const today = new Date().toISOString().split('T')[0];

        if (checkinDate > today) { alert('Check-in date cannot be in the future!'); return; }
        if (checkoutDate > today) { alert('Check-out date cannot be in the future!'); return; }
        if (checkoutDate <= checkinDate) { alert('Check-out date must be after check-in date!'); return; }

        const marketId = document.getElementById('preview_market_id').value;
        if (!marketId) { alert('Please select a market!'); return; }

        const reservationData = {
            booking_date: new Date().toISOString(),
            guest_name: document.getElementById('preview_guest_name').value,
            guest_surname: document.getElementById('preview_guest_surname').value,
            operator_id: parseInt(document.getElementById('preview_operator_id').value) || null,
            operator_voucher_no: document.getElementById('preview_operator_voucher_no').value,
            market_id: parseInt(marketId),
            hotel_id: parseInt(document.getElementById('preview_hotel_id').value) || null,
            room_id: parseInt(document.getElementById('preview_room_id').value) || null,
            checkin_date: checkinDate,
            checkout_date: checkoutDate,
            adult_count: parseInt(document.getElementById('preview_adult_count').value) || 1,
            child_count: parseInt(document.getElementById('preview_child_count').value) || 0,
            room_count: parseInt(document.getElementById('preview_room_count').value) || 1,
            total_amount: parseFloat(document.getElementById('preview_total_amount').value) || 0,
            notes: document.getElementById('preview_notes').value,
            state: 'pending'
        };

        if (extractedVoucherData && extractedVoucherData.confirmation_file) {
            reservationData.confirmation_file = extractedVoucherData.confirmation_file;
            reservationData.confirmation_filename = extractedVoucherData.confirmation_filename;
        }

        sendReservationData(reservationData);

        const previewModal = bootstrap.Modal.getInstance(document.getElementById('voucherPreviewModal'));
        previewModal.hide();
    }

    // ==================== Create/Edit Reservation ====================

    window.createNewReservation = function() {
        const form = document.getElementById('reservationForm');
        if (form) form.reset();

        const today = new Date().toISOString().split('T')[0];
        const bookingDateInput = document.getElementById('booking_date');
        if (bookingDateInput) bookingDateInput.value = today;

        if (!masterDataLoaded) {
            loadMasterData().then(() => {
                populateHotelsDropdown();
                populateOperatorsDropdown();
                populateMarketsDropdown();
                setDateConstraints();
                showModal();
            });
        } else {
            populateHotelsDropdown();
            populateOperatorsDropdown();
            populateMarketsDropdown();
            setDateConstraints();
            showModal();
        }
    }

    function showModal() {
        setTimeout(() => {
            const modalElement = document.getElementById('createReservationModal');
            if (modalElement) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            }
        }, 100);
    }

    window.editReservation = function(id) {
        const reservation = reservationsData[id];
        if (!reservation) {
            alert('Reservation data not found!');
            return;
        }

        if (!masterDataLoaded) {
            loadMasterData().then(() => showEditModal(reservation));
        } else {
            showEditModal(reservation);
        }
    }

    function showEditModal(reservation) {
        document.getElementById('edit_reservation_id').value = reservation.id;
        document.getElementById('edit_reservation_code').value = reservation.reservation_code || ('BR-' + reservation.id);
        document.getElementById('edit_booking_date').value = formatDateTime(reservation.booking_date);
        document.getElementById('edit_guest_name').value = reservation.guest_name || '';
        document.getElementById('edit_guest_surname').value = reservation.guest_surname || '';
        document.getElementById('edit_operator_voucher_no').value = reservation.operator_voucher_no || '';
        document.getElementById('edit_checkin_date').value = reservation.checkin_date || '';
        document.getElementById('edit_checkout_date').value = reservation.checkout_date || '';
        document.getElementById('edit_adult_count').value = reservation.adult_count || 1;
        document.getElementById('edit_child_count').value = reservation.child_count || 0;
        document.getElementById('edit_room_count').value = reservation.room_count || 1;
        document.getElementById('edit_total_amount').value = reservation.total_amount || 0;
        document.getElementById('edit_bonus_amount').value = reservation.bonus_amount || 0;
        document.getElementById('edit_state').value = reservation.state || 'pending';
        document.getElementById('edit_state_display').value = (reservation.state || 'pending').charAt(0).toUpperCase() + (reservation.state || 'pending').slice(1);
        document.getElementById('edit_notes').value = reservation.notes || '';

        const confirmationFileDiv = document.getElementById('current_confirmation_file');
        if (confirmationFileDiv) {
            const filename = reservation.confirmation_filename || reservation.confirmation_file_name;
            if (filename) {
                confirmationFileDiv.innerHTML = `<i class="fas fa-file-pdf me-2"></i><a href="/agency/api/bonus-reservations/download-file/${reservation.id}" class="file-download-link" target="_blank">${filename}</a>`;
            } else {
                confirmationFileDiv.innerHTML = '<span class="text-muted">No file uploaded</span>';
            }
        }

        populateEditHotelsDropdown(reservation.hotel_id);
        populateEditOperatorsDropdown(reservation.operator_id);
        populateEditMarketsDropdown(reservation.market_id);

        if (reservation.hotel_id) {
            if (roomsByHotel[reservation.hotel_id]) {
                populateEditRoomsDropdown(reservation.hotel_id, reservation.room_id);
            } else {
                $.ajax({
                    url: '/agency/api/hotel-rooms',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {hotel_id: reservation.hotel_id}, id: Date.now()}),
                    success: function(response) {
                        if (response.result && response.result.success) {
                            roomsByHotel[reservation.hotel_id] = response.result.data.rooms || [];
                            populateEditRoomsDropdown(reservation.hotel_id, reservation.room_id);
                        }
                    }
                });
            }
        }

        setDateConstraints('edit_');

        const modalElement = document.getElementById('editReservationModal');
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        }
    }

    window.saveReservation = function() {
        const form = document.getElementById('reservationForm');
        if (!form.checkValidity()) { form.reportValidity(); return; }

        const marketSelect = document.getElementById('market_id');
        marketSelect.disabled = false;
        const marketId = marketSelect.value;
        if (isSingleMarket) marketSelect.disabled = true;

        if (!marketId) { alert('Please select a market!'); return; }

        const checkinDate = document.getElementById('checkin_date').value;
        const checkoutDate = document.getElementById('checkout_date').value;
        const today = new Date().toISOString().split('T')[0];

        if (checkinDate > today || checkoutDate > today) { alert('Dates cannot be in the future!'); return; }
        if (checkoutDate <= checkinDate) { alert('Check-out must be after check-in!'); return; }

        const reservationData = {
            booking_date: document.getElementById('booking_date').value || new Date().toISOString(),
            guest_name: document.getElementById('guest_name').value,
            guest_surname: document.getElementById('guest_surname').value,
            operator_id: parseInt(document.getElementById('operator_id').value) || null,
            operator_voucher_no: document.getElementById('operator_voucher_no').value,
            market_id: parseInt(marketId),
            hotel_id: parseInt(document.getElementById('hotel_id').value) || null,
            room_id: parseInt(document.getElementById('room_id').value) || null,
            checkin_date: checkinDate,
            checkout_date: checkoutDate,
            adult_count: parseInt(document.getElementById('adult_count').value) || 1,
            child_count: parseInt(document.getElementById('child_count').value) || 0,
            room_count: parseInt(document.getElementById('room_count').value) || 1,
            total_amount: parseFloat(document.getElementById('total_amount').value) || 0,
            notes: document.getElementById('notes').value,
            state: 'pending'
        };

        const fileInput = document.getElementById('confirmation_file');
        if (fileInput && fileInput.files && fileInput.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                reservationData.confirmation_file = e.target.result.split(',')[1];
                reservationData.confirmation_filename = fileInput.files[0].name;
                sendReservationData(reservationData);
            };
            reader.readAsDataURL(fileInput.files[0]);
        } else {
            sendReservationData(reservationData);
        }
    }

    function sendReservationData(reservationData) {
        $.ajax({
            url: '/agency/api/bonus-reservations/create',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {reservation_data: reservationData}, id: Date.now()}),
            success: function(response) {
                if (response && response.result && response.result.success) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('createReservationModal'));
                    if (modal) modal.hide();
                    alert('Reservation created successfully!');
                    loadBonusReservations();
                } else {
                    alert('Error: ' + (response.result ? response.result.error : 'Unknown error'));
                }
            },
            error: function(xhr, status, error) { alert('Error creating reservation: ' + error); }
        });
    }

    window.updateReservation = function() {
        const form = document.getElementById('editReservationForm');
        if (!form.checkValidity()) { form.reportValidity(); return; }

        const marketSelect = document.getElementById('edit_market_id');
        marketSelect.disabled = false;
        const marketId = marketSelect.value;
        if (isSingleMarket) marketSelect.disabled = true;

        if (!marketId) { alert('Please select a market!'); return; }

        const checkinDate = document.getElementById('edit_checkin_date').value;
        const checkoutDate = document.getElementById('edit_checkout_date').value;

        if (checkoutDate <= checkinDate) { alert('Check-out must be after check-in!'); return; }

        const reservationData = {
            id: parseInt(document.getElementById('edit_reservation_id').value),
            reservation_code: document.getElementById('edit_reservation_code').value,
            guest_name: document.getElementById('edit_guest_name').value,
            guest_surname: document.getElementById('edit_guest_surname').value,
            operator_id: parseInt(document.getElementById('edit_operator_id').value) || null,
            operator_voucher_no: document.getElementById('edit_operator_voucher_no').value,
            market_id: parseInt(marketId),
            hotel_id: parseInt(document.getElementById('edit_hotel_id').value) || null,
            room_id: parseInt(document.getElementById('edit_room_id').value) || null,
            checkin_date: checkinDate,
            checkout_date: checkoutDate,
            adult_count: parseInt(document.getElementById('edit_adult_count').value) || 1,
            child_count: parseInt(document.getElementById('edit_child_count').value) || 0,
            room_count: parseInt(document.getElementById('edit_room_count').value) || 1,
            total_amount: parseFloat(document.getElementById('edit_total_amount').value) || 0,
            state: document.getElementById('edit_state').value,
            notes: document.getElementById('edit_notes').value
        };

        const fileInput = document.getElementById('edit_confirmation_file');
        if (fileInput && fileInput.files && fileInput.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                reservationData.confirmation_file = e.target.result.split(',')[1];
                reservationData.confirmation_filename = fileInput.files[0].name;
                sendUpdateData(reservationData);
            };
            reader.readAsDataURL(fileInput.files[0]);
        } else {
            sendUpdateData(reservationData);
        }
    }

    function sendUpdateData(reservationData) {
        $.ajax({
            url: '/agency/api/bonus-reservations/update',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {reservation_data: reservationData}, id: Date.now()}),
            success: function(response) {
                if (response && response.result && response.result.success) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editReservationModal'));
                    if (modal) modal.hide();
                    alert('Reservation updated successfully!');
                    loadBonusReservations();
                } else {
                    alert('Error: ' + (response.result ? response.result.error : 'Unknown error'));
                }
            },
            error: function(xhr, status, error) { alert('Error updating reservation: ' + error); }
        });
    }

    window.deleteReservation = function(id) {
        const reservation = reservationsData[id];
        if (reservation && reservation.state === 'balanced') {
            alert('Cannot delete a balanced reservation!');
            return;
        }

        if (confirm('Are you sure you want to delete this reservation?')) {
            $.ajax({
                url: '/agency/api/bonus-reservations/delete',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {reservation_id: id}, id: Date.now()}),
                success: function(response) {
                    if (response && response.result && response.result.success) {
                        alert('Reservation deleted successfully!');
                        loadBonusReservations();
                    } else {
                        alert('Error: ' + (response.result ? response.result.error : 'Unknown error'));
                    }
                },
                error: function(xhr, status, error) { alert('Error deleting reservation: ' + error); }
            });
        }
    }

})();
