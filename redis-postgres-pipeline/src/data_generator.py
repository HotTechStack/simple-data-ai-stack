"""Generate realistic order data for testing the pipeline."""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
from faker import Faker
import uuid

fake = Faker()

# Product IDs from our seed data
PRODUCT_IDS = [
    'PROD-001', 'PROD-002', 'PROD-003', 'PROD-004', 'PROD-005',
    'PROD-006', 'PROD-007', 'PROD-008', 'PROD-009', 'PROD-010',
    'PROD-011', 'PROD-012', 'PROD-013', 'PROD-014', 'PROD-015'
]

# Currency codes from our seed data
CURRENCIES = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'INR']

# Zip codes from our seed data
ZIP_CODES = [
    '10001', '94102', '60601', '02101', '98101',
    '33101', '75201', '80201', 'M5H2N2', 'V6B1A1'
]

# Base prices for products (matching seed data)
PRODUCT_PRICES = {
    'PROD-001': 1299.99,
    'PROD-002': 29.99,
    'PROD-003': 49.99,
    'PROD-004': 149.99,
    'PROD-005': 299.99,
    'PROD-006': 599.99,
    'PROD-007': 399.99,
    'PROD-008': 79.99,
    'PROD-009': 39.99,
    'PROD-010': 19.99,
    'PROD-011': 199.99,
    'PROD-012': 24.99,
    'PROD-013': 9.99,
    'PROD-014': 14.99,
    'PROD-015': 79.99,
}


class OrderGenerator:
    """Generate realistic order data."""

    def __init__(self, duplicate_rate: float = 0.05):
        """Initialize generator.

        Args:
            duplicate_rate: Probability of generating duplicate orders (0.0-1.0)
        """
        self.duplicate_rate = duplicate_rate
        self.seen_order_ids: List[str] = []

    def generate_order(self, timestamp: datetime = None) -> Dict[str, Any]:
        """Generate a single order.

        Args:
            timestamp: Order timestamp (defaults to now)

        Returns:
            Order dictionary matching our staging table schema
        """
        # Generate duplicate with specified probability
        if self.seen_order_ids and random.random() < self.duplicate_rate:
            order_id = random.choice(self.seen_order_ids)
        else:
            order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"
            self.seen_order_ids.append(order_id)

        customer_id = f"CUST-{fake.uuid4()[:12].upper()}"
        product_id = random.choice(PRODUCT_IDS)
        quantity = random.randint(1, 5)
        currency = random.choice(CURRENCIES)

        # Add some price variation (+/- 10%)
        base_price = PRODUCT_PRICES[product_id]
        price_variation = random.uniform(0.9, 1.1)
        unit_price = round(base_price * price_variation, 2)

        zip_code = random.choice(ZIP_CODES)

        if timestamp is None:
            timestamp = datetime.now()

        return {
            'order_id': order_id,
            'customer_id': customer_id,
            'product_id': product_id,
            'quantity': quantity,
            'unit_price': unit_price,
            'currency': currency,
            'zip_code': zip_code,
            'order_timestamp': timestamp.isoformat(),
            'raw_data': {
                'user_agent': fake.user_agent(),
                'ip_address': fake.ipv4(),
                'session_id': fake.uuid4()
            }
        }

    def generate_batch(
        self,
        count: int,
        start_time: datetime = None,
        time_spread_seconds: int = 3600
    ) -> List[Dict[str, Any]]:
        """Generate a batch of orders with timestamps spread over time.

        Args:
            count: Number of orders to generate
            start_time: Starting timestamp (defaults to now)
            time_spread_seconds: Spread orders over this time window

        Returns:
            List of order dictionaries
        """
        if start_time is None:
            start_time = datetime.now()

        orders = []
        for i in range(count):
            # Spread timestamps across the time window
            offset_seconds = (time_spread_seconds / count) * i
            timestamp = start_time + timedelta(seconds=offset_seconds)
            orders.append(self.generate_order(timestamp))

        return orders

    def generate_burst(
        self,
        count: int,
        timestamp: datetime = None
    ) -> List[Dict[str, Any]]:
        """Generate a burst of orders at the same timestamp.

        Useful for testing high-concurrency scenarios.

        Args:
            count: Number of orders to generate
            timestamp: Order timestamp (defaults to now)

        Returns:
            List of order dictionaries
        """
        if timestamp is None:
            timestamp = datetime.now()

        return [self.generate_order(timestamp) for _ in range(count)]

    def generate_historical_data(
        self,
        total_orders: int,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Generate historical orders spread over past days.

        Args:
            total_orders: Total number of orders to generate
            days_back: Number of days to spread data over

        Returns:
            List of order dictionaries
        """
        start_time = datetime.now() - timedelta(days=days_back)
        time_spread_seconds = days_back * 24 * 3600

        return self.generate_batch(
            count=total_orders,
            start_time=start_time,
            time_spread_seconds=time_spread_seconds
        )

    def reset_seen_orders(self) -> None:
        """Clear the seen orders list."""
        self.seen_order_ids.clear()


def generate_sample_orders(count: int = 1000) -> List[Dict[str, Any]]:
    """Convenience function to generate sample orders.

    Args:
        count: Number of orders to generate

    Returns:
        List of order dictionaries
    """
    generator = OrderGenerator(duplicate_rate=0.05)
    return generator.generate_batch(count)
