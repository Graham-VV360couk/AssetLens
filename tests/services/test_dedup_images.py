"""Tests for image field merging in deduplication service."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


def _make_property(image_url=None, image_urls=None):
    prop = MagicMock()
    prop.id = 1
    prop.address = '1 Test St'
    prop.postcode = 'SW1A 1AA'
    prop.asking_price = 300000
    prop.bedrooms = 2
    prop.bathrooms = 1
    prop.floor_area_sqm = None
    prop.description = 'existing desc'
    prop.town = 'London'
    prop.county = 'Greater London'
    prop.image_url = image_url
    prop.image_urls = image_urls
    prop.updated_at = datetime.utcnow()
    return prop


def _make_deduplicator(db):
    from backend.services.deduplication_service import PropertyDeduplicator
    dedup = PropertyDeduplicator(db)
    return dedup


def test_image_url_merged_when_empty():
    db = MagicMock()
    prop = _make_property(image_url=None)
    dedup = _make_deduplicator(db)
    new_data = {'image_url': 'https://img.example.com/hero.jpg'}
    dedup.merge_property_data(prop, new_data, source_name='searchland')
    assert prop.image_url == 'https://img.example.com/hero.jpg'


def test_image_url_not_overwritten_when_exists():
    db = MagicMock()
    prop = _make_property(image_url='https://img.example.com/existing.jpg')
    dedup = _make_deduplicator(db)
    new_data = {'image_url': 'https://img.example.com/new.jpg'}
    dedup.merge_property_data(prop, new_data, source_name='searchland')
    assert prop.image_url == 'https://img.example.com/existing.jpg'


def test_image_urls_merged_when_empty():
    db = MagicMock()
    prop = _make_property(image_urls=None)
    dedup = _make_deduplicator(db)
    new_data = {'image_urls': '["https://img.example.com/1.jpg"]'}
    dedup.merge_property_data(prop, new_data, source_name='searchland')
    assert prop.image_urls == '["https://img.example.com/1.jpg"]'


def test_image_urls_not_overwritten_when_exists():
    db = MagicMock()
    prop = _make_property(image_urls='["https://img.example.com/old.jpg"]')
    dedup = _make_deduplicator(db)
    new_data = {'image_urls': '["https://img.example.com/new.jpg"]'}
    dedup.merge_property_data(prop, new_data, source_name='searchland')
    assert prop.image_urls == '["https://img.example.com/old.jpg"]'
