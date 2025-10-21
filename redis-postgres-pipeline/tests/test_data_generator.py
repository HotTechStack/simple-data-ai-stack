"""Tests for data generator."""

import pytest
from datetime import datetime
from src.data_generator import OrderGenerator, generate_sample_orders


def test_generate_single_order():
    """Test generating a single order."""
    generator = OrderGenerator()
    order = generator.generate_order()

    # Check all required fields exist
    assert 'order_id' in order
    assert 'customer_id' in order
    assert 'product_id' in order
    assert 'quantity' in order
    assert 'unit_price' in order
    assert 'currency' in order
    assert 'zip_code' in order
    assert 'order_timestamp' in order
    assert 'raw_data' in order

    # Check field types
    assert isinstance(order['order_id'], str)
    assert isinstance(order['quantity'], int)
    assert isinstance(order['unit_price'], float)
    assert order['quantity'] >= 1


def test_generate_batch():
    """Test generating a batch of orders."""
    generator = OrderGenerator()
    orders = generator.generate_batch(count=100)

    assert len(orders) == 100
    assert all('order_id' in o for o in orders)

    # Check timestamps are spread
    timestamps = [o['order_timestamp'] for o in orders]
    assert len(set(timestamps)) > 1  # Should have different timestamps


def test_generate_burst():
    """Test generating burst orders."""
    generator = OrderGenerator()
    timestamp = datetime.now()
    orders = generator.generate_burst(count=50, timestamp=timestamp)

    assert len(orders) == 50

    # All should have same timestamp
    timestamps = [o['order_timestamp'] for o in orders]
    assert len(set(timestamps)) == 1


def test_duplicate_generation():
    """Test duplicate order generation."""
    generator = OrderGenerator(duplicate_rate=0.5)  # 50% duplicates
    orders = generator.generate_batch(count=100)

    order_ids = [o['order_id'] for o in orders]
    unique_ids = set(order_ids)

    # With 50% duplicate rate, should have some duplicates
    assert len(unique_ids) < len(order_ids)


def test_convenience_function():
    """Test convenience function."""
    orders = generate_sample_orders(count=50)

    assert len(orders) == 50
    assert all('order_id' in o for o in orders)
