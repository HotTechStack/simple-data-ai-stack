#!/usr/bin/env python3
"""
Generate sample product data for demonstrating Elasticsearch vs Vector Search.

This script creates realistic product data that demonstrates when to use:
- Keyword search (exact SKUs, error codes, IDs)
- Semantic search (fuzzy descriptions, conceptual queries)
- Hybrid search (filtered semantic search)
"""

import random
import json
from typing import List, Dict

# Product categories with realistic descriptions
CATEGORIES = {
    "electronics": {
        "products": [
            ("Wireless Gaming Mouse", "High-precision wireless mouse with RGB lighting, 16000 DPI sensor, and programmable buttons"),
            ("USB-C Hub Adapter", "7-in-1 USB-C hub with HDMI, USB 3.0 ports, SD card reader, and power delivery"),
            ("Mechanical Keyboard", "RGB mechanical gaming keyboard with hot-swappable switches and aluminum frame"),
            ("Laptop Stand", "Ergonomic aluminum laptop stand with adjustable height and ventilation design"),
            ("Bluetooth Speaker", "Portable waterproof Bluetooth speaker with 360-degree sound and 24-hour battery"),
            ("Webcam 1080P", "Full HD webcam with auto-focus, built-in microphone, and low-light correction"),
            ("Phone Charging Cable", "Braided nylon USB-C fast charging cable 6ft with data sync"),
            ("Wireless Earbuds", "True wireless earbuds with active noise cancellation and 30-hour battery life"),
        ]
    },
    "office_supplies": {
        "products": [
            ("Ergonomic Office Chair", "Adjustable lumbar support office chair with breathable mesh back and armrests"),
            ("Standing Desk Converter", "Height-adjustable standing desk converter with dual monitor support"),
            ("Desk Organizer Set", "Bamboo desk organizer with compartments for pens, papers, and accessories"),
            ("Whiteboard Markers", "Dry erase markers 12-pack in assorted colors with low-odor ink"),
            ("Filing Cabinet", "3-drawer steel filing cabinet with lock for letter-size documents"),
            ("Paper Shredder", "Cross-cut paper shredder with 12-sheet capacity and anti-jam technology"),
            ("Desk Lamp LED", "Adjustable LED desk lamp with touch control and multiple brightness levels"),
            ("Printer Paper", "Premium white printer paper 500 sheets, 20lb weight, letter size"),
        ]
    },
    "home_goods": {
        "products": [
            ("Coffee Maker", "Programmable drip coffee maker with thermal carafe and 24-hour timer"),
            ("Air Purifier", "HEPA filter air purifier with 3-stage filtration and quiet operation"),
            ("Vacuum Cleaner", "Cordless stick vacuum with powerful suction and long-lasting battery"),
            ("Blender", "High-speed blender with 1200W motor for smoothies and food processing"),
            ("Kitchen Knife Set", "Professional stainless steel knife set with wooden block holder"),
            ("Non-Stick Cookware", "10-piece non-stick cookware set with glass lids and stay-cool handles"),
            ("Storage Containers", "Glass food storage containers set with airtight locking lids"),
            ("Bath Towel Set", "Luxury cotton bath towels 6-piece set, ultra-soft and highly absorbent"),
        ]
    },
    "sports_fitness": {
        "products": [
            ("Yoga Mat", "Extra thick yoga mat with non-slip surface and carrying strap"),
            ("Dumbbell Set", "Adjustable dumbbell set with weight plates and secure locking mechanism"),
            ("Resistance Bands", "Exercise resistance bands set with 5 different resistance levels"),
            ("Treadmill", "Folding treadmill with LCD display, heart rate monitor, and preset programs"),
            ("Exercise Bike", "Stationary exercise bike with adjustable seat and magnetic resistance"),
            ("Fitness Tracker", "Waterproof fitness tracker with heart rate monitor and sleep tracking"),
            ("Jump Rope", "Speed jump rope with ball bearings and adjustable length"),
            ("Protein Powder", "Whey protein powder 2lb, vanilla flavor, 25g protein per serving"),
        ]
    }
}

# Common error codes (for demonstrating exact match searches)
ERROR_CODES = [
    "ERR-1001", "ERR-1002", "ERR-2003", "ERR-2004",
    "ERR-3005", "ERR-4001", "ERR-4002", "WARN-3005"
]


def generate_sku(category: str, index: int) -> str:
    """Generate realistic SKU codes."""
    category_code = {
        "electronics": "ELEC",
        "office_supplies": "OFFC",
        "home_goods": "HOME",
        "sports_fitness": "SPRT"
    }
    return f"{category_code[category]}-{str(index).zfill(6)}"


def generate_products(num_products: int = 1000) -> List[Dict]:
    """Generate sample products with realistic data."""
    products = []
    product_id = 1

    categories = list(CATEGORIES.keys())

    for i in range(num_products):
        category = random.choice(categories)
        product_name, base_description = random.choice(CATEGORIES[category]["products"])

        # Add some variation to product names and descriptions
        variations = [
            f"{product_name}",
            f"Premium {product_name}",
            f"{product_name} Pro",
            f"Deluxe {product_name}",
        ]

        name = random.choice(variations)

        # Randomly add error codes to some products (10% chance)
        # This simulates products that might have issues or recalls
        error_code = random.choice(ERROR_CODES) if random.random() < 0.1 else None

        product = {
            "id": product_id,
            "sku": generate_sku(category, product_id),
            "name": name,
            "description": base_description,
            "category": category,
            "price": round(random.uniform(9.99, 999.99), 2),
            "stock_quantity": random.randint(0, 500),
            "error_code": error_code
        }

        products.append(product)
        product_id += 1

    return products


def save_products_to_json(products: List[Dict], filename: str = "products.json"):
    """Save products to JSON file."""
    with open(filename, 'w') as f:
        json.dump(products, f, indent=2)
    print(f"✓ Saved {len(products)} products to {filename}")


if __name__ == "__main__":
    print("Generating sample product data...")
    products = generate_products(1000)
    save_products_to_json(products, "/app/data/products.json")

    # Print some statistics
    print(f"\nStatistics:")
    print(f"  Total products: {len(products)}")

    categories_count = {}
    for p in products:
        cat = p['category']
        categories_count[cat] = categories_count.get(cat, 0) + 1

    print(f"  Products by category:")
    for cat, count in categories_count.items():
        print(f"    {cat}: {count}")

    products_with_errors = sum(1 for p in products if p['error_code'])
    print(f"  Products with error codes: {products_with_errors}")

    print(f"\nSample products:")
    for product in products[:3]:
        print(f"  SKU: {product['sku']}")
        print(f"  Name: {product['name']}")
        print(f"  Category: {product['category']}")
        print(f"  Price: ${product['price']}")
        if product['error_code']:
            print(f"  Error Code: {product['error_code']}")
        print()
