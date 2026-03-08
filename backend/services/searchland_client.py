"""
Searchland/PropertyData API Client
Handles licensed property feed integration for Rightmove, Zoopla, OnTheMarket data
"""

import os
import requests
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger
import json

load_dotenv()


class SearchlandClient:
    """
    Client for Searchland API - licensed property data feeds
    Provides nationwide UK property listings from major portals
    """

    def __init__(self):
        self.api_key = os.getenv('SEARCHLAND_API_KEY')
        self.base_url = os.getenv('SEARCHLAND_BASE_URL', 'https://api.searchland.co.uk')
        self.api_version = os.getenv('SEARCHLAND_API_VERSION', 'v1')
        self.rate_limit_requests = int(os.getenv('FEED_RATE_LIMIT_REQUESTS', 100))
        self.rate_limit_period = int(os.getenv('FEED_RATE_LIMIT_PERIOD', 60))
        self.batch_size = int(os.getenv('FEED_BATCH_SIZE', 1000))

        if not self.api_key:
            raise ValueError("SEARCHLAND_API_KEY not set in environment")

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'AssetLens/1.0'
        })

        # Rate limiting tracking
        self.request_count = 0
        self.rate_limit_start = time.time()

    def _handle_rate_limit(self):
        """
        Implement rate limiting to respect API limits
        """
        self.request_count += 1

        # Check if we've exceeded rate limit
        elapsed = time.time() - self.rate_limit_start
        if self.request_count >= self.rate_limit_requests:
            if elapsed < self.rate_limit_period:
                sleep_time = self.rate_limit_period - elapsed
                logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)

            # Reset counter
            self.request_count = 0
            self.rate_limit_start = time.time()

    def _make_request(
        self,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Searchland API with retry logic
        """
        url = f"{self.base_url}/{self.api_version}/{endpoint}"

        for attempt in range(retries):
            try:
                self._handle_rate_limit()

                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=30)
                elif method == 'POST':
                    response = self.session.post(url, json=data, timeout=30)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                elif response.status_code >= 500:  # Server error
                    if attempt < retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Server error. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                logger.error(f"HTTP error: {e}")
                raise

            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed: {e}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"Request failed after {retries} attempts: {e}")
                raise

        raise Exception(f"Failed to make request after {retries} attempts")

    def get_properties(
        self,
        postcode: Optional[str] = None,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_bedrooms: Optional[int] = None,
        updated_since: Optional[datetime] = None,
        page: int = 1,
        limit: int = None
    ) -> Dict[str, Any]:
        """
        Fetch property listings from Searchland API

        Args:
            postcode: UK postcode or area (e.g., "SW1A", "SW1A 1AA")
            property_type: detached, semi-detached, terraced, flat
            min_price: Minimum asking price
            max_price: Maximum asking price
            min_bedrooms: Minimum number of bedrooms
            updated_since: Only fetch properties updated since this datetime (for incremental sync)
            page: Page number for pagination
            limit: Results per page (default: batch_size from config)

        Returns:
            Dictionary with properties and pagination metadata
        """
        params = {
            'page': page,
            'limit': limit or self.batch_size
        }

        if postcode:
            params['postcode'] = postcode
        if property_type:
            params['property_type'] = property_type
        if min_price:
            params['min_price'] = min_price
        if max_price:
            params['max_price'] = max_price
        if min_bedrooms:
            params['min_bedrooms'] = min_bedrooms
        if updated_since:
            params['updated_since'] = updated_since.isoformat()

        logger.info(f"Fetching properties (page {page}, limit {params['limit']})")
        return self._make_request('properties', params=params)

    def get_property_by_id(self, property_id: str) -> Dict[str, Any]:
        """
        Fetch single property by Searchland ID

        Args:
            property_id: Searchland property identifier

        Returns:
            Property details dictionary
        """
        logger.info(f"Fetching property {property_id}")
        return self._make_request(f'properties/{property_id}')

    def fetch_all_properties(
        self,
        updated_since: Optional[datetime] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all properties with automatic pagination
        Used for full sync of nationwide dataset

        Args:
            updated_since: Only fetch properties updated since this datetime (for incremental sync)
            max_pages: Maximum number of pages to fetch (None = all pages)

        Returns:
            List of all property dictionaries
        """
        all_properties = []
        page = 1
        total_fetched = 0

        logger.info(f"Starting full property fetch (incremental: {updated_since is not None})")

        while True:
            if max_pages and page > max_pages:
                logger.info(f"Reached max_pages limit ({max_pages})")
                break

            try:
                response = self.get_properties(
                    updated_since=updated_since,
                    page=page,
                    limit=self.batch_size
                )

                properties = response.get('data', [])
                pagination = response.get('pagination', {})

                if not properties:
                    logger.info("No more properties to fetch")
                    break

                all_properties.extend(properties)
                total_fetched += len(properties)

                current_page = pagination.get('current_page', page)
                total_pages = pagination.get('total_pages', 0)
                total_count = pagination.get('total_count', 0)

                logger.info(
                    f"Fetched page {current_page}/{total_pages} "
                    f"({len(properties)} properties, {total_fetched}/{total_count} total)"
                )

                # Check if we've reached the last page
                if current_page >= total_pages:
                    logger.info("Reached last page")
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break

        logger.info(f"Fetch complete. Total properties: {total_fetched}")
        return all_properties

    def get_hmo_register(
        self,
        council: Optional[str] = None,
        postcode: Optional[str] = None,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Fetch HMO register data

        Args:
            council: Local authority name
            postcode: Filter by postcode
            page: Page number

        Returns:
            HMO register entries
        """
        params = {'page': page, 'limit': self.batch_size}

        if council:
            params['council'] = council
        if postcode:
            params['postcode'] = postcode

        logger.info(f"Fetching HMO register (council={council}, postcode={postcode})")
        return self._make_request('hmo-register', params=params)

    def normalize_property_data(self, raw_property: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize property data from Searchland API to AssetLens schema

        Args:
            raw_property: Raw property dictionary from Searchland API

        Returns:
            Normalized property dictionary matching our database schema
        """
        return {
            'source_id': raw_property.get('id'),
            'source_name': raw_property.get('source', 'searchland'),  # rightmove, zoopla, etc.
            'source_url': raw_property.get('url'),
            'address': raw_property.get('address', {}).get('display_address'),
            'postcode': raw_property.get('address', {}).get('postcode'),
            'town': raw_property.get('address', {}).get('town'),
            'county': raw_property.get('address', {}).get('county'),
            'property_type': raw_property.get('property_type', '').lower(),
            'bedrooms': raw_property.get('bedrooms'),
            'bathrooms': raw_property.get('bathrooms'),
            'reception_rooms': raw_property.get('receptions'),
            'floor_area_sqm': raw_property.get('floor_area'),
            'asking_price': raw_property.get('price'),
            'price_qualifier': raw_property.get('price_qualifier'),
            'description': raw_property.get('description'),
            'date_found': datetime.utcnow().date(),
            'status': 'active',
            'imported_at': datetime.utcnow()
        }


class PropertyDataClient(SearchlandClient):
    """
    Alternative client for PropertyData API
    Inherits from SearchlandClient with endpoint adjustments
    """

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('PROPERTYDATA_API_KEY') or self.api_key
        self.base_url = os.getenv('PROPERTYDATA_BASE_URL', 'https://api.propertydata.co.uk')
        self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})

    # PropertyData-specific methods can be added here if API differs
