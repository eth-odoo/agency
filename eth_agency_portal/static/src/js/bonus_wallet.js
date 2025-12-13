/**
 * Bonus Wallet Management JavaScript
 * ETH Agency Portal
 */

(function() {
    'use strict';

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Bonus Wallet JS - DOMContentLoaded');

        // Check if we're on the bonus wallet page
        const walletDashboard = document.getElementById('wallet-dashboard');
        if (!walletDashboard) {
            console.log('Not on bonus wallet page, skipping initialization');
            return;
        }

        console.log('Initializing Bonus Wallet Module...');

        // Initialize the wallet manager
        BonusWalletManager.init();
    });

    // Bonus Wallet Manager Object
    const BonusWalletManager = {
        currentWalletType: 'user',
        walletData: {},
        bonusOwnerType: '',
        isMaster: false,

        init: function() {
            console.log('BonusWalletManager.init() called');
            this.loadWalletInfo();
            this.bindEvents();
        },

        bindEvents: function() {
            const self = this;
            console.log('Binding events...');

            // Wallet selector buttons
            document.addEventListener('click', function(e) {
                if (e.target.classList.contains('wallet-select-btn') || e.target.parentElement?.classList.contains('wallet-select-btn')) {
                    const btn = e.target.classList.contains('wallet-select-btn') ? e.target : e.target.parentElement;
                    const selectedType = btn.getAttribute('data-wallet');

                    console.log('Wallet selector clicked:', selectedType);

                    if (selectedType === self.currentWalletType) return;

                    // Update button states
                    document.querySelectorAll('.wallet-select-btn').forEach(function(button) {
                        button.classList.remove('active', 'btn-primary');
                        button.classList.add('btn-outline-primary');
                    });
                    btn.classList.remove('btn-outline-primary');
                    btn.classList.add('active', 'btn-primary');

                    // Find selected wallet data
                    const selectedWallet = self.walletData.wallets?.find(function(w) {
                        return w.type === selectedType;
                    });

                    if (selectedWallet) {
                        self.currentWalletType = selectedType;
                        self.updateWalletDisplay(selectedWallet);
                        self.loadWalletSummary('month');
                        self.loadEntries();
                        self.loadSpends();
                    }
                }

                // Period filter buttons
                if (e.target.classList.contains('period-filter')) {
                    console.log('Period filter clicked');

                    document.querySelectorAll('.period-filter').forEach(function(button) {
                        button.classList.remove('active', 'btn-primary');
                        button.classList.add('btn-outline-primary');
                    });
                    e.target.classList.remove('btn-outline-primary');
                    e.target.classList.add('active', 'btn-primary');

                    const period = e.target.getAttribute('data-period');
                    self.loadWalletSummary(period);
                }
            });

            // Filter entries button
            const filterEntriesBtn = document.getElementById('filter-entries');
            if (filterEntriesBtn) {
                filterEntriesBtn.addEventListener('click', function() {
                    console.log('Filter entries clicked');
                    const filters = {
                        dateFrom: document.getElementById('entries-date-from')?.value,
                        dateTo: document.getElementById('entries-date-to')?.value
                    };
                    self.loadEntries(filters);
                });
            }

            // Filter spends button
            const filterSpendsBtn = document.getElementById('filter-spends');
            if (filterSpendsBtn) {
                filterSpendsBtn.addEventListener('click', function() {
                    console.log('Filter spends clicked');
                    const filters = {
                        dateFrom: document.getElementById('spends-date-from')?.value,
                        dateTo: document.getElementById('spends-date-to')?.value
                    };
                    self.loadSpends(filters);
                });
            }
        },

        loadWalletInfo: function() {
            const self = this;
            console.log('Loading wallet info...');

            // Use jQuery Ajax if available
            if (typeof $ !== 'undefined' && $.ajax) {
                $.ajax({
                    url: '/agency/api/bonus-wallet/info',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({}),
                    success: function(response) {
                        console.log('Raw wallet info response:', response);

                        // Odoo JSON-RPC format - data is in 'result' not directly in response
                        if (response.result) {
                            console.log('Found result in response:', response.result);
                            self.handleWalletInfoResponse(response.result);
                        } else if (response.data) {
                            console.log('Found data in response:', response.data);
                            self.handleWalletInfoResponse(response);
                        } else {
                            console.error('Unexpected response format:', response);
                        }
                    },
                    error: function(xhr) {
                        console.error('Error loading wallet info:', xhr);
                        self.showError('Failed to load wallet information');
                    }
                });
            }
        },

        handleWalletInfoResponse: function(response) {
            console.log('handleWalletInfoResponse called with:', response);

            // Check for success flag and data
            if (response.success && response.data) {
                this.walletData = response.data;
                this.bonusOwnerType = response.data.bonus_owner_type;
                this.isMaster = response.data.is_master;

                console.log('Wallet data loaded:', {
                    bonusOwnerType: this.bonusOwnerType,
                    isMaster: this.isMaster,
                    walletsCount: response.data.wallets?.length,
                    wallets: response.data.wallets
                });

                // Show split info if applicable
                if (this.bonusOwnerType === 'percentage_split' && response.data.split_info) {
                    const splitAlert = document.getElementById('split-info-alert');
                    const splitMessage = document.getElementById('split-info-message');

                    if (splitAlert && splitMessage) {
                        splitAlert.classList.remove('d-none');
                        splitMessage.textContent = 'Bonuses are split: Agency gets ' +
                            response.data.split_info.agency_percentage +
                            '%, Users get ' + response.data.split_info.user_percentage + '%';
                    }
                }

                // Setup wallet selector if needed
                if (response.data.wallets && response.data.wallets.length > 1) {
                    const walletSelector = document.getElementById('wallet-selector');
                    if (walletSelector) {
                        walletSelector.classList.remove('d-none');

                        // Update wallet selector buttons
                        document.querySelectorAll('.wallet-select-btn').forEach(function(btn) {
                            const walletType = btn.getAttribute('data-wallet');
                            const hasWallet = response.data.wallets.find(function(w) {
                                return w.type === walletType;
                            });
                            if (!hasWallet) {
                                btn.classList.add('d-none');
                            }
                        });
                    }
                }

                // Load first available wallet
                if (response.data.wallets && response.data.wallets.length > 0) {
                    const firstWallet = response.data.wallets[0];
                    console.log('Loading first wallet:', firstWallet);
                    this.currentWalletType = firstWallet.type;
                    this.updateWalletDisplay(firstWallet);
                    this.loadWalletSummary('month');
                    this.loadEntries();
                    this.loadSpends();
                } else {
                    console.warn('No wallets found in response');
                }
            } else if (response.error) {
                console.error('Error in response:', response.error);
                this.showError(response.error);
            } else {
                console.error('Invalid response format or no data:', response);
            }
        },

        updateWalletDisplay: function(walletInfo) {
            console.log('updateWalletDisplay called with:', walletInfo);

            const wallet = walletInfo.wallet;
            if (!wallet) {
                console.error('No wallet data in walletInfo:', walletInfo);
                return;
            }

            console.log('Updating display with wallet data:', wallet);

            // Update wallet name
            const nameElement = document.getElementById('wallet-owner-name');
            if (nameElement) {
                nameElement.textContent = wallet.display_name || 'Bonus Wallet';
                console.log('Updated wallet name to:', wallet.display_name);
            } else {
                console.error('wallet-owner-name element not found');
            }

            // Update current balance
            const balanceElement = document.getElementById('current-balance');
            if (balanceElement) {
                balanceElement.textContent = this.formatCurrency(wallet.total_balance);
                console.log('Updated balance to:', wallet.total_balance, '->', this.formatCurrency(wallet.total_balance));
            } else {
                console.error('current-balance element not found');
            }

            // Update total earned
            const earnedElement = document.getElementById('total-earned');
            if (earnedElement) {
                earnedElement.textContent = this.formatCurrency(wallet.total_earned);
                console.log('Updated earned to:', wallet.total_earned, '->', this.formatCurrency(wallet.total_earned));
            } else {
                console.error('total-earned element not found');
            }

            // Update total spent
            const spentElement = document.getElementById('total-spent');
            if (spentElement) {
                spentElement.textContent = this.formatCurrency(wallet.total_spent);
                console.log('Updated spent to:', wallet.total_spent, '->', this.formatCurrency(wallet.total_spent));
            } else {
                console.error('total-spent element not found');
            }

            // Update total expired
            const expiredElement = document.getElementById('total-expired');
            if (expiredElement) {
                expiredElement.textContent = this.formatCurrency(wallet.total_expired);
                console.log('Updated expired to:', wallet.total_expired, '->', this.formatCurrency(wallet.total_expired));
            } else {
                console.error('total-expired element not found');
            }
        },

        loadWalletSummary: function(period) {
            const self = this;
            console.log('Loading wallet summary for period:', period);

            const data = {
                wallet_type: this.currentWalletType,
                period: period
            };

            if (typeof $ !== 'undefined' && $.ajax) {
                $.ajax({
                    url: '/agency/api/bonus-wallet/summary',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(data),
                    success: function(response) {
                        console.log('Raw summary response:', response);

                        // Handle Odoo JSON-RPC format
                        const result = response.result || response;

                        if (result.success && result.data) {
                            self.updateSummaryDisplay(result.data);
                        } else {
                            console.error('Invalid summary response:', result);
                        }
                    },
                    error: function(xhr) {
                        console.error('Error loading summary:', xhr);
                    }
                });
            }
        },

        updateSummaryDisplay: function(data) {
            console.log('Updating summary display:', data);

            this.setElementText('period-earned', this.formatCurrency(data.period_earned));
            this.setElementText('period-spent', this.formatCurrency(data.period_spent));
            this.setElementText('expiring-soon', this.formatCurrency(data.expiring_soon));

            const expiringSoon = document.getElementById('expiring-soon');
            if (expiringSoon && data.expiring_entries_count > 0) {
                expiringSoon.parentElement.classList.add('text-warning');
            } else if (expiringSoon) {
                expiringSoon.parentElement.classList.remove('text-warning');
            }
        },

        loadEntries: function(filters) {
            const self = this;
            console.log('Loading entries with filters:', filters);

            const data = {
                wallet_type: this.currentWalletType,
                filters: filters || {}
            };

            if (typeof $ !== 'undefined' && $.ajax) {
                $.ajax({
                    url: '/agency/api/bonus-wallet/entries',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(data),
                    success: function(response) {
                        console.log('Raw entries response:', response);

                        // Handle Odoo JSON-RPC format
                        const result = response.result || response;

                        if (result.success && result.data) {
                            self.displayEntries(result.data.entries);
                        } else {
                            console.error('Invalid entries response:', result);
                            self.showEntriesError();
                        }
                    },
                    error: function(xhr) {
                        console.error('Error loading entries:', xhr);
                        self.showEntriesError();
                    }
                });
            }
        },

        loadSpends: function(filters) {
            const self = this;
            console.log('Loading spends with filters:', filters);

            const data = {
                wallet_type: this.currentWalletType,
                filters: filters || {}
            };

            if (typeof $ !== 'undefined' && $.ajax) {
                $.ajax({
                    url: '/agency/api/bonus-wallet/spends',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(data),
                    success: function(response) {
                        console.log('Raw spends response:', response);

                        // Handle Odoo JSON-RPC format
                        const result = response.result || response;

                        if (result.success && result.data) {
                            self.displaySpends(result.data.spends);
                        } else {
                            console.error('Invalid spends response:', result);
                            self.showSpendsError();
                        }
                    },
                    error: function(xhr) {
                        console.error('Error loading spends:', xhr);
                        self.showSpendsError();
                    }
                });
            }
        },

        displayEntries: function(entries) {
            console.log('Displaying entries:', entries);
            const tbody = document.getElementById('entries-tbody');
            if (!tbody) {
                console.error('entries-tbody element not found');
                return;
            }

            tbody.innerHTML = '';

            if (!entries || entries.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No bonus entries found</td></tr>';
                return;
            }

            const self = this;
            entries.forEach(function(entry) {
                const row = document.createElement('tr');

                let statusBadge = '';
                if (entry.status === 'expired') {
                    statusBadge = '<span class="badge bg-danger">Expired</span>';
                } else if (entry.status === 'fully_used') {
                    statusBadge = '<span class="badge bg-secondary">Used</span>';
                } else {
                    statusBadge = '<span class="badge bg-success">Active</span>';
                }

                row.innerHTML = `
                    <td>${self.formatDate(entry.earned_date)}</td>
                    <td>${entry.description || '-'}</td>
                    <td>${self.formatCurrency(entry.bonus_amount)}</td>
                    <td>${self.formatCurrency(entry.used_amount)}</td>
                    <td>${self.formatCurrency(entry.available_amount)}</td>
                    <td>${entry.expire_date ? self.formatDate(entry.expire_date) : 'No expiry'}</td>
                    <td>${statusBadge}</td>
                `;

                tbody.appendChild(row);
            });
        },

        displaySpends: function(spends) {
            console.log('Displaying spends:', spends);
            const tbody = document.getElementById('spends-tbody');
            if (!tbody) {
                console.error('spends-tbody element not found');
                return;
            }

            tbody.innerHTML = '';

            if (!spends || spends.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">No spending records found</td></tr>';
                return;
            }

            const self = this;
            spends.forEach(function(spend, index) {
                const row = document.createElement('tr');

                row.innerHTML = `
                    <td>${self.formatDate(spend.spend_date)}</td>
                    <td>${spend.description || '-'}</td>
                    <td>${self.formatCurrency(spend.amount)}</td>
                    <td>${spend.reference || '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="BonusWalletManager.showSpendDetails(${index})">
                            Details
                        </button>
                    </td>
                `;

                tbody.appendChild(row);

                // Store spend data for details
                row.spendData = spend;
            });

            // Store spends array for details
            this.currentSpends = spends;
        },

        showSpendDetails: function(index) {
            const spend = this.currentSpends[index];
            if (!spend) return;

            let detailsHtml = '<ul>';
            const self = this;

            if (spend.details && spend.details.length > 0) {
                spend.details.forEach(function(detail) {
                    detailsHtml += '<li>Amount: ' + self.formatCurrency(detail.amount) +
                                  ' from entry dated ' + self.formatDate(detail.entry_date) + '</li>';
                });
            } else {
                detailsHtml += '<li>No detail information available</li>';
            }

            detailsHtml += '</ul>';

            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Spend Details',
                    html: detailsHtml,
                    icon: 'info'
                });
            } else {
                alert('Spend Details:\n' + detailsHtml.replace(/<[^>]*>/g, ''));
            }
        },

        // Helper functions
        formatCurrency: function(amount) {
            const formatted = new Intl.NumberFormat('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount || 0);
            return formatted;
        },

        formatDate: function(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        },

        setElementText: function(elementId, text) {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = text;
                console.log('Set element', elementId, 'to:', text);
            } else {
                console.error('Element not found:', elementId);
            }
        },

        showError: function(message) {
            if (typeof Swal !== 'undefined') {
                Swal.fire('Error', message, 'error');
            } else {
                alert('Error: ' + message);
            }
        },

        showEntriesError: function() {
            const tbody = document.getElementById('entries-tbody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger">Error loading entries</td></tr>';
            }
        },

        showSpendsError: function() {
            const tbody = document.getElementById('spends-tbody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">Error loading spends</td></tr>';
            }
        }
    };

    // Make BonusWalletManager available globally for onclick handlers
    window.BonusWalletManager = BonusWalletManager;

})();
