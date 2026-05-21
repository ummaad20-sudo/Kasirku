// Kasirku Web Application - Vue 3 Frontend
const { createApp } = Vue;

const app = createApp({
    data() {
        return {
            // Auth
            authenticated: false,
            username: '',
            role: '',
            loginForm: {
                username: '',
                password: ''
            },
            loginError: '',

            // Tabs
            currentTab: 'KASIR',
            tabs: ['KASIR', 'STOK', 'PENGATURAN', 'OMZET'],

            // Products
            allProducts: [],
            filteredProducts: [],
            searchQuery: '',
            newProduct: {
                nama: '',
                harga: '',
                stok: '',
                barcode: ''
            },

            // Cart
            cart: [],
            cartTotal: 0,

            // Payment
            showPaymentModal: false,
            paymentMethod: '',
            cashInput: '',

            // Transactions
            transactions: [],
            filteredTransactions: [],
            currentTransactionFilter: 'semua',
            stats: {
                grand_total: 0,
                grand_count: 0,
                hari_total: 0,
                hari_count: 0,
                minggu_total: 0,
                minggu_count: 0,
                bulan_total: 0,
                bulan_count: 0,
                cash_total: 0,
                qris_total: 0,
                lain_total: 0
            },

            // Settings
            changePassForm: {
                old_password: '',
                new_password: '',
                confirm_password: ''
            }
        };
    },

    methods: {
        // ─────────────────────────────────────────────────────────────────────
        // AUTHENTICATION
        // ─────────────────────────────────────────────────────────────────────

        async checkAuth() {
            try {
                const response = await axios.get('/api/auth/check');
                if (response.data.authenticated) {
                    this.authenticated = true;
                    this.username = response.data.username;
                    this.role = response.data.role;
                    this.loadInitialData();
                }
            } catch (error) {
                console.error('Auth check failed:', error);
            }
        },

        async doLogin() {
            this.loginError = '';
            try {
                const response = await axios.post('/api/auth/login', {
                    username: this.loginForm.username,
                    password: this.loginForm.password
                });

                this.authenticated = true;
                this.username = response.data.username;
                this.role = response.data.role;
                this.loginForm = { username: '', password: '' };
                this.loadInitialData();
            } catch (error) {
                this.loginError = error.response?.data?.error || 'Login gagal';
            }
        },

        async doLogout() {
            try {
                await axios.post('/api/auth/logout');
                this.authenticated = false;
                this.username = '';
                this.role = '';
                this.cart = [];
                this.cartTotal = 0;
                this.loginForm = { username: '', password: '' };
            } catch (error) {
                console.error('Logout failed:', error);
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // INITIALIZATION
        // ─────────────────────────────────────────────────────────────────────

        async loadInitialData() {
            this.loadProducts();
            this.loadTransactions();
            this.loadStats();
        },

        // ─────────────────────────────────────────────────────────────────────
        // PRODUCTS
        // ─────────────────────────────────────────────────────────────────────

        async loadProducts() {
            try {
                const response = await axios.get('/api/products');
                this.allProducts = response.data;
                this.filteredProducts = response.data;
            } catch (error) {
                console.error('Failed to load products:', error);
            }
        },

        filterProducts() {
            const query = this.searchQuery.toLowerCase();
            this.filteredProducts = this.allProducts.filter(product =>
                product.nama.toLowerCase().includes(query) ||
                (product.barcode && product.barcode.includes(query))
            );
        },

        async addNewProduct() {
            if (!this.newProduct.nama || !this.newProduct.harga || !this.newProduct.stok) {
                alert('Data tidak lengkap');
                return;
            }

            try {
                await axios.post('/api/products', {
                    nama: this.newProduct.nama,
                    harga: parseInt(this.newProduct.harga),
                    stok: parseInt(this.newProduct.stok),
                    barcode: this.newProduct.barcode
                });

                this.newProduct = { nama: '', harga: '', stok: '', barcode: '' };
                this.loadProducts();
            } catch (error) {
                alert('Gagal menambah produk: ' + (error.response?.data?.error || error.message));
            }
        },

        async editProduct(product) {
            const newPrice = prompt('Harga baru:', product.harga);
            if (newPrice === null) return;

            const newStock = prompt('Stok baru:', product.stok);
            if (newStock === null) return;

            try {
                await axios.put(`/api/products/${product.id}`, {
                    nama: product.nama,
                    harga: parseInt(newPrice),
                    stok: parseInt(newStock),
                    barcode: product.barcode
                });

                this.loadProducts();
            } catch (error) {
                alert('Gagal update produk: ' + error.message);
            }
        },

        async deleteProduct(productId) {
            if (!confirm('Yakin hapus produk ini?')) return;

            try {
                await axios.delete(`/api/products/${productId}`);
                this.loadProducts();
            } catch (error) {
                alert('Gagal hapus produk: ' + error.message);
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // CART MANAGEMENT
        // ─────────────────────────────────────────────────────────────────────

        addToCart(product) {
            if (product.stok <= 0) return;

            // Check if product already in cart
            const existingItem = this.cart.find(item => item.id === product.id);
            if (existingItem) {
                existingItem.quantity += 1;
            } else {
                this.cart.push({
                    id: product.id,
                    nama: product.nama,
                    harga: product.harga,
                    quantity: 1
                });
            }

            product.stok -= 1;
            this.updateCartTotal();
        },

        removeFromCart(index) {
            const item = this.cart[index];
            const product = this.allProducts.find(p => p.id === item.id);
            if (product) {
                product.stok += 1;
            }
            this.cart.splice(index, 1);
            this.updateCartTotal();
        },

        updateCartTotal() {
            this.cartTotal = this.cart.reduce((total, item) => total + (item.harga * item.quantity), 0);
        },

        // ─────────────────────────────────────────────────────────────────────
        // PAYMENT
        // ─────────────────────────────────────────────────────────────────────

        showPaymentOptions() {
            if (this.cart.length === 0) return;
            this.showPaymentModal = true;
            this.paymentMethod = '';
            this.cashInput = '';
        },

        processPayment(method) {
            this.paymentMethod = method;
            if (method === 'Cash') {
                this.cashInput = '';
            }
        },

        async finalizePayment() {
            if (this.paymentMethod === 'Cash') {
                if (!this.cashInput || parseInt(this.cashInput) < this.cartTotal) {
                    alert('Uang tidak cukup');
                    return;
                }
            }

            try {
                const items = this.cart.map(item => ({
                    id: item.id,
                    harga: item.harga,
                    quantity: item.quantity
                }));

                await axios.post('/api/transactions', {
                    items: items,
                    metode: this.paymentMethod,
                    info: ''
                });

                this.cart = [];
                this.cartTotal = 0;
                this.showPaymentModal = false;
                this.loadProducts();
                this.loadTransactions();
                this.loadStats();
                alert('Pembayaran berhasil!');
            } catch (error) {
                alert('Gagal memproses pembayaran: ' + (error.response?.data?.error || error.message));
            }
        },

        openBarcodeScanner() {
            const barcode = prompt('Scan atau ketik barcode:');
            if (barcode) {
                this.searchQuery = barcode;
                this.filterProducts();

                const product = this.filteredProducts[0];
                if (product && product.stok > 0) {
                    this.addToCart(product);
                } else {
                    alert('Produk tidak ditemukan atau stok habis');
                }
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // TRANSACTIONS & REPORTS
        // ─────────────────────────────────────────────────────────────────────

        async loadTransactions() {
            try {
                const response = await axios.get('/api/transactions', {
                    params: { filter: this.currentTransactionFilter }
                });
                this.transactions = response.data;
                this.filterTransactions(this.currentTransactionFilter);
            } catch (error) {
                console.error('Failed to load transactions:', error);
            }
        },

        filterTransactions(filter) {
            this.currentTransactionFilter = filter;
            this.loadTransactions();
        },

        async loadStats() {
            try {
                const response = await axios.get('/api/transactions/stats');
                this.stats = response.data;
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // ACCOUNT MANAGEMENT
        // ─────────────────────────────────────────────────────────────────────

        async changePassword() {
            if (this.changePassForm.new_password !== this.changePassForm.confirm_password) {
                alert('Password tidak cocok');
                return;
            }

            if (this.changePassForm.new_password.length < 6) {
                alert('Password minimal 6 karakter');
                return;
            }

            try {
                await axios.post('/api/account/change-password', {
                    old_password: this.changePassForm.old_password,
                    new_password: this.changePassForm.new_password,
                    confirm_password: this.changePassForm.confirm_password
                });

                alert('Password berhasil diubah');
                this.changePassForm = {
                    old_password: '',
                    new_password: '',
                    confirm_password: ''
                };
            } catch (error) {
                alert(error.response?.data?.error || 'Gagal mengubah password');
            }
        }
    },

    watch: {
        currentTab(newTab) {
            if (newTab === 'OMZET') {
                this.loadStats();
                this.loadTransactions();
            }
        }
    },

    mounted() {
        this.checkAuth();
    }
});

app.mount('#app');
