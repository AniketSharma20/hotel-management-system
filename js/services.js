// Dining and Services Module
window.appServices = {
    init: () => {
        appServices.renderMenu('all');
        
        // Filter logic
        const filterBtns = document.querySelectorAll('.filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                filterBtns.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                const category = e.target.getAttribute('data-category');
                appServices.renderMenu(category);
            });
        });
        
        // Guest service requests logic
        const serviceBtns = document.querySelectorAll('.service-info .btn-outline');
        serviceBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const serviceName = e.target.parentElement.querySelector('h3').innerText;
                app.ui.showToast(`Request for ${serviceName} sent. Our staff will contact you shortly.`, 'success');
            });
        });
    },

    renderMenu: (category) => {
        const container = document.getElementById('menu-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        let items = hotelData.menu;
        if (category !== 'all') {
            items = items.filter(item => item.category === category);
        }

        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'menu-item glass-panel';
            
            // Pass item object simply bypassing via JSON parse approach from attribute or simple global var lookup
            card.innerHTML = `
                <img src="${item.image}" alt="${item.name}" class="menu-img">
                <h3>${item.name}</h3>
                <p class="menu-desc">${item.description}</p>
                <span class="menu-price">$${item.price}</span>
                <button class="btn-secondary add-cart-btn" onclick="appServices.addToCart('${item.id}')">Add to Order</button>
            `;
            container.appendChild(card);
        });
    },

    addToCart: (itemId) => {
        const item = hotelData.menu.find(m => m.id === itemId);
        if(item) {
            app.cart.addItem(item);
        } else {
            app.ui.showToast('Item not found', 'error');
        }
    }
};
