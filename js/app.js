// Main Application Logic
window.app = {
    state: {
        isLoggedIn: false,
        user: null,
        cart: [],
        bookings: [] // Global Array: {id, roomId, name, dates, status, timestamp}
    },

    init: () => {
        app.nav.init();
        app.auth.init();
        app.cart.init();
        
        // Init other modules
        if(window.appRooms) appRooms.init();
        if(window.appServices) appServices.init();
        
        // Set default dates for booking
        const today = new Date().toISOString().split('T')[0];
        const tmr = new Date(new Date().setDate(new Date().getDate() + 1)).toISOString().split('T')[0];
        if(document.getElementById('check-in-date')) document.getElementById('check-in-date').value = today;
        if(document.getElementById('check-out-date')) document.getElementById('check-out-date').value = tmr;

        app.ui.showToast('Welcome to The Grand Aurelia', 'success');
        app.slider.init();
        
        // Initialize dynamic views
        if(app.userBookings) app.userBookings.render();
        if(app.admin) app.admin.render();
    },

    slider: {
        images: ['assets/hotel_hero.png', 'assets/hotel_room.png', 'assets/gourmet_food.png'],
        currentIndex: 0,
        init: () => {
            const slider = document.getElementById('hero-slider');
            if(slider) {
                setInterval(() => {
                    app.slider.currentIndex = (app.slider.currentIndex + 1) % app.slider.images.length;
                    slider.style.backgroundImage = `linear-gradient(to top, rgba(15,17,21,0.8), transparent), url('${app.slider.images[app.slider.currentIndex]}')`;
                }, 4000);
            }
            
            // Animate stats
            const statRooms = document.getElementById('stat-rooms');
            if(statRooms) {
                let count = 0;
                const interval = setInterval(() => {
                    count += 25;
                    statRooms.innerText = count + '+';
                    if(count >= 500) clearInterval(interval);
                }, 50);
            }
        }
    },

    nav: {
        init: () => {
            const links = document.querySelectorAll('.nav-links a');
            links.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const target = e.currentTarget.getAttribute('data-target');
                    app.nav.switchTo(target);
                });
            });

            // Mobile menu toggle
            const mobileToggle = document.querySelector('.mobile-menu-toggle');
            const navLinks = document.querySelector('.nav-links');
            if(mobileToggle && navLinks) {
                mobileToggle.addEventListener('click', () => {
                    navLinks.classList.toggle('active');
                });
                
                // Close mobile menu on link click
                navLinks.querySelectorAll('a').forEach(link => {
                    link.addEventListener('click', () => navLinks.classList.remove('active'));
                });
            }
        },
        switchTo: (viewId) => {
            // Update active link
            document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
            const activeLink = document.querySelector(`.nav-links a[data-target="${viewId}"]`);
            if(activeLink) activeLink.classList.add('active');

            // Switch view
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active-view'));
            const view = document.getElementById(viewId);
            if(view) {
                view.classList.add('active-view');
                window.scrollTo(0, 0);
            }
        }
    },

    auth: {
        isSignUpMode: false,
        init: () => {
            const loginBtn = document.getElementById('login-btn');
            const modal = document.getElementById('auth-modal');
            const closeBtn = document.querySelector('.modal-close');
            const form = document.getElementById('auth-form');
            const switchBtn = document.getElementById('switch-signup');

            loginBtn.addEventListener('click', () => {
                if (app.state.isLoggedIn) {
                    app.auth.logout();
                } else {
                    modal.classList.add('active');
                }
            });

            closeBtn.addEventListener('click', () => modal.classList.remove('active'));
            
            // Close on outside click
            modal.addEventListener('click', (e) => {
                if(e.target === modal) modal.classList.remove('active');
            });

            switchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                app.auth.isSignUpMode = !app.auth.isSignUpMode;
                const title = document.getElementById('auth-title');
                const submitBtn = document.getElementById('auth-submit-btn');
                const nameGroup = document.getElementById('auth-name-group');
                const switchText = document.getElementById('auth-switch-text');
                
                if (app.auth.isSignUpMode) {
                    title.innerText = 'Create Account';
                    submitBtn.innerText = 'Sign Up';
                    nameGroup.style.display = 'flex';
                    switchText.innerText = 'Already have an account?';
                    switchBtn.innerText = 'Sign In';
                } else {
                    title.innerText = 'Sign In';
                    submitBtn.innerText = 'Sign In';
                    nameGroup.style.display = 'none';
                    switchText.innerText = 'Don\'t have an account?';
                    switchBtn.innerText = 'Create one';
                }
            });

            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const welcomeMsg = app.auth.isSignUpMode ? 'Account created successfully!' : 'Successfully signed in.';
                app.auth.login(welcomeMsg);
                modal.classList.remove('active');
            });
        },
        login: (msg = 'Successfully signed in.') => {
            app.state.isLoggedIn = true;
            document.getElementById('login-btn').innerText = 'Sign Out';
            app.ui.showToast(msg, 'success');
        },
        logout: () => {
            app.state.isLoggedIn = false;
            document.getElementById('login-btn').innerText = 'Sign In';
            app.ui.showToast('Successfully signed out.', 'success');
        }
    },

    cart: {
        init: () => {
            const cartBtn = document.getElementById('cart-btn');
            const cartDrawer = document.getElementById('cart-drawer');
            const closeCart = document.getElementById('close-cart');
            const overlay = document.getElementById('overlay');
            const checkoutBtn = document.getElementById('checkout-btn');

            cartBtn.addEventListener('click', () => {
                cartDrawer.classList.add('active');
                overlay.classList.add('active');
            });

            const close = () => {
                cartDrawer.classList.remove('active');
                overlay.classList.remove('active');
            };

            closeCart.addEventListener('click', close);
            overlay.addEventListener('click', close);

            checkoutBtn.addEventListener('click', () => {
                const roomNum = document.getElementById('order-room-number').value;
                if(!roomNum) {
                    app.ui.showToast('Please enter your room number.', 'error');
                    return;
                }
                app.ui.showToast('Order placed successfully! It will be delivered shortly.', 'success');
                app.state.cart = [];
                app.cart.updateUI();
                close();
            });
        },
        addItem: (item) => {
            const existingItem = app.state.cart.find(i => i.id === item.id);
            if (existingItem) {
                existingItem.qty++;
            } else {
                app.state.cart.push({...item, qty: 1});
            }
            app.cart.updateUI();
            app.ui.showToast(`${item.name} added to order.`, 'success');
        },
        removeItem: (id) => {
            app.state.cart = app.state.cart.filter(i => i.id !== id);
            app.cart.updateUI();
        },
        updateQty: (id, change) => {
            const item = app.state.cart.find(i => i.id === id);
            if(item) {
                item.qty += change;
                if(item.qty <= 0) app.cart.removeItem(id);
                else app.cart.updateUI();
            }
        },
        updateUI: () => {
            const container = document.getElementById('cart-items-container');
            const badge = document.getElementById('cart-badge');
            const totalEl = document.getElementById('cart-total-price');
            const checkoutBtn = document.getElementById('checkout-btn');
            
            // Total Items & Price
            let totalItems = 0;
            let totalPrice = 0;
            
            container.innerHTML = '';

            if (app.state.cart.length === 0) {
                container.innerHTML = '<p class="empty-cart">Your order is empty.</p>';
                checkoutBtn.disabled = true;
            } else {
                checkoutBtn.disabled = false;
                app.state.cart.forEach(item => {
                    totalItems += item.qty;
                    totalPrice += item.price * item.qty;

                    const div = document.createElement('div');
                    div.className = 'cart-item';
                    div.innerHTML = `
                        <div class="item-info">
                            <h4>${item.name}</h4>
                            <p>$${item.price.toFixed(2)}</p>
                        </div>
                        <div class="item-qty">
                            <button class="qty-btn" onclick="app.cart.updateQty('${item.id}', -1)"><i class="fa-solid fa-minus"></i></button>
                            <span>${item.qty}</span>
                            <button class="qty-btn" onclick="app.cart.updateQty('${item.id}', 1)"><i class="fa-solid fa-plus"></i></button>
                        </div>
                    `;
                    container.appendChild(div);
                });
            }

            badge.innerText = totalItems;
            if(totalItems > 0) {
                badge.style.transform = 'scale(1.2)';
                setTimeout(() => badge.style.transform = 'scale(1)', 200);
            }
            totalEl.innerText = `$${totalPrice.toFixed(2)}`;
        }
    },

    ui: {
        showToast: (message, type = 'success') => {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
            container.appendChild(toast);

            setTimeout(() => {
                if(container.contains(toast)) container.removeChild(toast);
            }, 3000);
        }
    },

    userBookings: {
        render: () => {
            const container = document.getElementById('active-bookings-list');
            const empty = document.getElementById('empty-bookings-state');
            if(!container) return;
            
            if(app.state.bookings.length === 0) {
                container.style.display = 'none';
                empty.style.display = 'block';
                return;
            }
            
            empty.style.display = 'none';
            container.style.display = 'grid';
            container.style.gap = '1rem';
            
            container.innerHTML = app.state.bookings.map(b => {
                let color = '#f1c40f'; // Pending
                if(b.status === 'Approved') color = '#2ecc71';
                if(b.status === 'Declined') color = '#e74c3c';
                
                return `
                <div style="background: rgba(0,0,0,0.3); padding: 1.5rem; border-radius: 8px; border-left: 4px solid ${color}; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="color: var(--gold); margin-bottom: 0.3rem;">${b.name}</h4>
                        <p style="color: var(--text-muted); font-size: 0.9rem;">Dates: ${b.dates}</p>
                        <p style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.5rem;">Requested on: ${b.timestamp}</p>
                    </div>
                    <div style="text-align: right;">
                        <span style="display: inline-block; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: bold; background: ${color}22; color: ${color}; border: 1px solid ${color}">${b.status}</span>
                    </div>
                </div>`;
            }).join('');
        }
    },

    admin: {
        render: () => {
            const container = document.getElementById('admin-requests-container');
            if(!container) return;
            
            const pending = app.state.bookings.filter(b => b.status === 'Pending');
            
            if(pending.length === 0) {
                container.innerHTML = '<p style="color: var(--text-muted);">No pending booking requests.</p>';
                return;
            }
            
            container.innerHTML = pending.map(b => `
                <div style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center;" id="admin-req-${b.id}">
                    <div>
                        <h4 style="color: var(--gold)">Guest: ${app.state.user || 'Unknown'}</h4>
                        <p style="color: var(--text-muted); font-size: 0.9rem;">${b.name} (${b.dates})</p>
                    </div>
                    <div>
                        <button class="btn-primary" style="padding: 0.4rem 1rem;" onclick="app.admin.action('${b.id}', 'Approved')">Approve</button>
                        <button class="btn-outline" style="border-color: #ff4757; color: #ff4757; padding: 0.4rem 1rem;" onclick="app.admin.action('${b.id}', 'Declined')">Decline</button>
                    </div>
                </div>
            `).join('');
        },
        action: (bookingId, status) => {
            const booking = app.state.bookings.find(b => b.id === bookingId);
            if(booking) {
                booking.status = status;
                app.ui.showToast(`Booking ${status} successfully.`, 'success');
                app.admin.render(); // Refresh admin list
                app.userBookings.render(); // Sync with user's tab
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', app.init);
