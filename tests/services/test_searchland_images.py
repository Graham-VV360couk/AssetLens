"""Tests for image extraction in Searchland normalizer."""
import pytest


def make_client():
    from backend.services.searchland_client import SearchlandClient
    client = SearchlandClient.__new__(SearchlandClient)
    return client


def _raw(images=None, image_url=None):
    return {
        'id': '123',
        'url': 'http://example.com',
        'address': {'display_address': '1 Test St', 'postcode': 'SW1A 1AA',
                    'town': 'London', 'county': 'Greater London'},
        'property_type': 'flat',
        'bedrooms': 2,
        'bathrooms': 1,
        'price': 300000,
        'description': 'A nice flat',
        'status': 'for_sale',
        'sold_price': None,
        'images': images,
        'image_url': image_url,
    }


def test_images_array_extracted():
    client = make_client()
    result = client.normalize_property_data(_raw(images=[
        'https://img.example.com/1.jpg',
        'https://img.example.com/2.jpg',
    ]))
    assert result['image_urls'] == '["https://img.example.com/1.jpg", "https://img.example.com/2.jpg"]'
    assert result['image_url'] == 'https://img.example.com/1.jpg'


def test_single_image_url_extracted():
    client = make_client()
    result = client.normalize_property_data(_raw(image_url='https://img.example.com/hero.jpg'))
    assert result['image_url'] == 'https://img.example.com/hero.jpg'
    assert result['image_urls'] is None


def test_no_images_returns_none():
    client = make_client()
    result = client.normalize_property_data(_raw())
    assert result['image_url'] is None
    assert result['image_urls'] is None
