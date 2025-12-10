/** @odoo-module **/

/**
 * Agency Portal JavaScript
 */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('#agency_portal .alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Date validation for reservation form
    const checkinDate = document.getElementById('checkin_date');
    const checkoutDate = document.getElementById('checkout_date');
    const roomNights = document.getElementById('room_nights');

    if (checkinDate && checkoutDate) {
        // Set minimum date to today
        const today = new Date().toISOString().split('T')[0];
        checkinDate.setAttribute('min', today);
        checkoutDate.setAttribute('min', today);

        // Update checkout min date when checkin changes
        checkinDate.addEventListener('change', function () {
            checkoutDate.setAttribute('min', this.value);
            if (checkoutDate.value && checkoutDate.value < this.value) {
                checkoutDate.value = this.value;
            }
            calculateRoomNights();
        });

        checkoutDate.addEventListener('change', calculateRoomNights);
    }

    function calculateRoomNights() {
        if (checkinDate && checkoutDate && roomNights && checkinDate.value && checkoutDate.value) {
            const start = new Date(checkinDate.value);
            const end = new Date(checkoutDate.value);
            const diff = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
            if (diff > 0) {
                roomNights.value = diff;
            }
        }
    }

    // Form validation
    const forms = document.querySelectorAll('#agency_portal form');
    forms.forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Password confirmation validation
    const newPassword = document.getElementById('new_password');
    const confirmPassword = document.getElementById('confirm_password');

    if (newPassword && confirmPassword) {
        confirmPassword.addEventListener('input', function () {
            if (this.value !== newPassword.value) {
                this.setCustomValidity('Passwords do not match');
            } else {
                this.setCustomValidity('');
            }
        });
    }
});
