window.hotelData = {
    rooms: [
        {
            id: 'r1',
            name: 'Deluxe King Room',
            type: 'Deluxe',
            price: 250,
            image: 'assets/room1.jpg',
            amenities: ['<i class="fa-solid fa-wifi"></i>', '<i class="fa-solid fa-tv"></i>', '<i class="fa-solid fa-mug-hot"></i>'],
            description: 'Spacious room with a king-size bed, city view, and luxurious marble bathroom.'
        },
        {
            id: 'r2',
            name: 'Ocean View Suite',
            type: 'Suite',
            price: 450,
            image: 'assets/room2.jpg',
            amenities: ['<i class="fa-solid fa-wifi"></i>', '<i class="fa-solid fa-water"></i>', '<i class="fa-solid fa-wine-glass"></i>'],
            description: 'Breathtaking ocean views with a separate living area and premium minibar.'
        },
        {
            id: 'r3',
            name: 'Presidential Penthouse',
            type: 'Penthouse',
            price: 1200,
            image: 'assets/room3.jpg',
            amenities: ['<i class="fa-solid fa-star"></i>', '<i class="fa-solid fa-hot-tub-person"></i>', '<i class="fa-solid fa-bell-concierge"></i>'],
            description: 'The ultimate luxury experience. Private terrace, jacuzzi, and 24/7 personal butler.'
        },
        {
            id: 'r4',
            name: 'Executive Twin Room',
            type: 'Standard',
            price: 200,
            image: 'assets/hotel_room.png',
            amenities: ['<i class="fa-solid fa-wifi"></i>', '<i class="fa-solid fa-tv"></i>'],
            description: 'Perfect for business travelers. Two twin beds and a dedicated workspace.'
        },
        {
            id: 'r5',
            name: 'Royal Heritage Villa',
            type: 'Villa',
            price: 1500,
            image: 'assets/room5.jpg',
            amenities: ['<i class="fa-solid fa-house"></i>', '<i class="fa-solid fa-person-swimming"></i>', '<i class="fa-solid fa-tree"></i>'],
            description: 'A private detached villa with its own garden, private pool, and chef on call.'
        },
        {
            id: 'r6',
            name: 'Honeymoon Suite',
            type: 'Suite',
            price: 550,
            image: 'assets/hotel_room.png',
            amenities: ['<i class="fa-solid fa-heart"></i>', '<i class="fa-solid fa-wine-bottle"></i>', '<i class="fa-solid fa-spa"></i>'],
            description: 'Romantic suite featuring rose petal decor, couples spa access, and complimentary champagne.'
        },
        {
            id: 'r7',
            name: 'Urban Loft',
            type: 'Standard',
            price: 300,
            image: 'assets/room7.jpg',
            amenities: ['<i class="fa-solid fa-wifi"></i>', '<i class="fa-solid fa-city"></i>', '<i class="fa-solid fa-couch"></i>'],
            description: 'Modern, industrial-chic loft perfect for extended stays with a small kitchenette.'
        },
        {
            id: 'r8',
            name: 'Family Connecting Rooms',
            type: 'Family',
            price: 400,
            image: 'assets/room8.jpg',
            amenities: ['<i class="fa-solid fa-children"></i>', '<i class="fa-solid fa-gamepad"></i>', '<i class="fa-brands fa-playstation"></i>'],
            description: 'Two connecting rooms equipped with a gaming console and child-friendly amenities.'
        }
    ],
    menu: [
        {
            id: 'm1',
            name: 'Truffle Scrambled Eggs',
            category: 'breakfast',
            price: 24,
            image: 'assets/gourmet_food.png',
            description: 'Organic eggs folded with black truffle shavings, served with artisanal sourdough.'
        },
        {
            id: 'm1b',
            name: 'Avocado Toast & Poached Eggs',
            category: 'breakfast',
            price: 18,
            image: 'assets/food2.jpg',
            description: 'Smashed avocado, heirloom tomatoes, and perfect poached eggs on rustic bread.'
        },
        {
            id: 'm1c',
            name: 'Belgian Waffles',
            category: 'breakfast',
            price: 16,
            image: 'assets/gourmet_food.png',
            description: 'Golden waffles served with mixed berries, whipped cream, and real maple syrup.'
        },
        {
            id: 'm2',
            name: 'Wagyu Beef Burger',
            category: 'mains',
            price: 35,
            image: 'assets/food4.jpg',
            description: 'Premium Wagyu beef, aged cheddar, caramelized onions, truffle fries.'
        },
        {
            id: 'm3',
            name: 'Grilled Salmon Quinoa',
            category: 'mains',
            price: 32,
            image: 'assets/food5.jpg',
            description: 'Atlantic salmon perfectly grilled, served over warm quinoa salad and lemon butter.'
        },
        {
            id: 'm3b',
            name: 'Ribeye Steak Frites',
            category: 'mains',
            price: 55,
            image: 'assets/gourmet_food.png',
            description: '12oz prime ribeye grilled to perfection, served with garlic herb butter and french fries.'
        },
        {
            id: 'm3c',
            name: 'Truffle Mushroom Risotto',
            category: 'mains',
            price: 28,
            image: 'assets/food7.jpg',
            description: 'Creamy Arborio rice with wild mushrooms, parmesan, and white truffle oil.'
        },
        {
            id: 'm4',
            name: 'Molten Chocolate Lava Cake',
            category: 'desserts',
            price: 18,
            image: 'assets/food8.jpg',
            description: 'Warm French valrhona chocolate center with vanilla bean gelato.'
        },
        {
            id: 'm4b',
            name: 'Classic New York Cheesecake',
            category: 'desserts',
            price: 14,
            image: 'assets/food9.jpg',
            description: 'Rich and creamy cheesecake with a graham cracker crust and fresh strawberry compote.'
        },
        {
            id: 'm4c',
            name: 'Tiramisu',
            category: 'desserts',
            price: 16,
            image: 'assets/food10.jpg',
            description: 'Traditional Italian dessert with espresso-soaked ladyfingers and mascarpone cream.'
        },
        {
            id: 'm5',
            name: 'Signature Gold Martini',
            category: 'drinks',
            price: 22,
            image: 'assets/food11.jpg',
            description: 'Premium vodka, dry vermouth, garnished with 24k edible gold flakes.'
        },
        {
            id: 'm6',
            name: 'Fresh Pressed Juice',
            category: 'drinks',
            price: 12,
            image: 'assets/food12.jpg',
            description: 'Choice of Orange, Apple, or our signature Detox Greens blend.'
        },
        {
            id: 'm7',
            name: 'Aged Cabernet Sauvignon',
            category: 'drinks',
            price: 25,
            image: 'assets/food13.jpg',
            description: 'A glass of our finest house red, featuring dark fruit notes and a smooth finish.'
        }
    ]
};
