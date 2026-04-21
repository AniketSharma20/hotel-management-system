// Rooms & Suites Module
window.appRooms = {
    init: () => {
        appRooms.render(hotelData.rooms);
    },

    render: (rooms) => {
        const container = document.getElementById('rooms-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        rooms.forEach(room => {
            const card = document.createElement('div');
            card.className = 'room-card glass-panel';
            
            const amenitiesHtml = room.amenities.join(' ');
            
            card.innerHTML = `
                <div class="room-img-container">
                    <img src="${room.image}" alt="${room.name}">
                    <div class="room-price">$${room.price} <span style="font-size: 0.8rem; font-weight: normal; color: var(--text-main)">/ night</span></div>
                </div>
                <div class="room-details">
                    <h3>${room.name}</h3>
                    <div class="room-amenities">
                        ${amenitiesHtml}
                    </div>
                    <p class="room-desc">${room.description}</p>
                    <div class="room-actions">
                        <button class="btn-outline" onclick="appRooms.viewDetails('${room.id}')">Details</button>
                        <button class="btn-primary" onclick="appRooms.book('${room.id}')">Book Now</button>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
    },

    search: () => {
        const checkIn = document.getElementById('check-in-date').value;
        const checkOut = document.getElementById('check-out-date').value;
        
        if (!checkIn || !checkOut) {
            app.ui.showToast('Please select check-in and check-out dates.', 'error');
            return;
        }

        if (new Date(checkIn) >= new Date(checkOut)) {
            app.ui.showToast('Check-out date must be after check-in date.', 'error');
            return;
        }

        // Simulate searching
        app.ui.showToast('Searching for available rooms...', 'success');
        
        // Just re-render all for demo purposes
        setTimeout(() => {
            appRooms.render(hotelData.rooms);
            app.ui.showToast('Available rooms updated.', 'success');
        }, 800);
    },

    book: (roomId) => {
        if (!app.state.isLoggedIn) {
            app.ui.showToast('Please sign in to book a room.', 'error');
            document.getElementById('auth-modal').classList.add('active');
            return;
        }

        const room = hotelData.rooms.find(r => r.id === roomId);
        const checkIn = document.getElementById('check-in-date').value;
        const checkOut = document.getElementById('check-out-date').value;

        if (!checkIn || !checkOut) {
            app.ui.showToast('Please select check-in and check-out dates.', 'error');
            return;
        }

        if(room) {
            const bookingId = 'bk_' + Math.random().toString(36).substr(2, 9);
            const now = new Date();
            app.state.bookings.push({
                id: bookingId,
                roomId: room.id,
                name: room.name,
                dates: `${checkIn} to ${checkOut}`,
                status: 'Pending',
                timestamp: now.toLocaleString()
            });

            app.ui.showToast(`Request sent for ${room.name}! Awaiting manager approval.`, 'success');
            
            // Re-render UI components 
            if (app.userBookings) app.userBookings.render();
            if (app.admin) app.admin.render();
        }
    },
    
    viewDetails: (roomId) => {
        app.ui.showToast(`Viewing details for room ${roomId}. (Mock action)`, 'success');
    }
};
