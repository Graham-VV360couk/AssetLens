"""
Property Deduplication Service
Fuzzy matching to identify and merge duplicate properties across multiple data sources
(licensed feeds, auctions, manual scraping)
"""

import os
import sys
from typing import Optional, List, Tuple, Dict
from rapidfuzz import fuzz
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.models.property import Property, PropertySource


class PropertyDeduplicator:
    """
    Identifies and merges duplicate properties using fuzzy address matching
    """

    def __init__(self, db_session: Session, similarity_threshold: int = 85):
        """
        Initialize deduplicator

        Args:
            db_session: SQLAlchemy database session
            similarity_threshold: Minimum similarity percentage (0-100) to consider a match (default: 85)
        """
        self.session = db_session
        self.similarity_threshold = similarity_threshold

    def normalize_address(self, address: str) -> str:
        """
        Normalize address string for consistent comparison

        Args:
            address: Raw address string

        Returns:
            Normalized address string
        """
        if not address:
            return ""

        # Convert to uppercase
        normalized = address.upper()

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        # Remove punctuation
        chars_to_remove = [',', '.', '-', '/']
        for char in chars_to_remove:
            normalized = normalized.replace(char, ' ')

        # Expand common abbreviations using word-boundary regex so trailing
        # abbreviations (e.g. "123 High St" with no trailing space) are also
        # expanded and fuzzy matching scores remain accurate.
        import re as _re
        abbreviations = {
            r'\bST\b': 'STREET',
            r'\bRD\b': 'ROAD',
            r'\bAVE\b': 'AVENUE',
            r'\bDR\b': 'DRIVE',
            r'\bCT\b': 'COURT',
            r'\bLN\b': 'LANE',
            r'\bPL\b': 'PLACE',
            r'\bSQ\b': 'SQUARE',
            r'\bTER\b': 'TERRACE',
            r'\bCL\b': 'CLOSE',
            r'\bAPT\b': 'APARTMENT',
            r'\bFLT\b': 'FLAT',
        }

        for pattern, full in abbreviations.items():
            normalized = _re.sub(pattern, full, normalized)

        # Remove "FLAT", "APARTMENT", "UNIT" followed by number (inconsistent across sources)
        normalized = _re.sub(r'\b(FLAT|APARTMENT|UNIT)\s+\d+[A-Z]?\b', '', normalized)

        # Clean up whitespace again
        normalized = ' '.join(normalized.split())

        return normalized.strip()

    def calculate_similarity(self, address1: str, address2: str) -> float:
        """
        Calculate similarity score between two addresses

        Args:
            address1: First address string
            address2: Second address string

        Returns:
            Similarity score (0-100)
        """
        norm_addr1 = self.normalize_address(address1)
        norm_addr2 = self.normalize_address(address2)

        # Use token sort ratio (handles word order variations)
        similarity = fuzz.token_sort_ratio(norm_addr1, norm_addr2)

        return similarity

    def find_duplicate(
        self,
        address: str,
        postcode: str,
        exclude_property_id: Optional[int] = None
    ) -> Optional[Property]:
        """
        Find duplicate property in database using fuzzy matching

        Args:
            address: Property address
            postcode: Property postcode (exact match required)
            exclude_property_id: Property ID to exclude from search (for updates)

        Returns:
            Duplicate Property object if found, None otherwise
        """
        # First, find all properties with matching postcode
        query = self.session.query(Property).filter(
            Property.postcode == postcode,
            Property.status != 'archived'  # Don't match archived properties
        )

        if exclude_property_id:
            query = query.filter(Property.id != exclude_property_id)

        candidates = query.all()

        if not candidates:
            return None

        # Calculate similarity for each candidate
        best_match = None
        best_similarity = 0

        for candidate in candidates:
            similarity = self.calculate_similarity(address, candidate.address)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = candidate

        # Return match if similarity exceeds threshold
        if best_similarity >= self.similarity_threshold:
            logger.info(
                f"Found duplicate: '{address}' matches '{best_match.address}' "
                f"(similarity: {best_similarity:.1f}%)"
            )
            return best_match

        return None

    def merge_property_data(
        self,
        existing_property: Property,
        new_data: Dict,
        source_name: str,
        source_id: str = None,
        source_url: str = None
    ) -> Property:
        """
        Merge new property data into existing property record
        Keeps most complete/recent data

        Args:
            existing_property: Existing Property object
            new_data: Dictionary of new property data
            source_name: Name of data source (e.g., 'searchland', 'auction')
            source_id: External ID from source system
            source_url: URL to source listing

        Returns:
            Updated Property object
        """
        # Update fields if new data is more complete or recent
        if new_data.get('asking_price') and not existing_property.asking_price:
            existing_property.asking_price = new_data['asking_price']

        if new_data.get('bedrooms') and not existing_property.bedrooms:
            existing_property.bedrooms = new_data['bedrooms']

        if new_data.get('bathrooms') and not existing_property.bathrooms:
            existing_property.bathrooms = new_data['bathrooms']

        if new_data.get('floor_area_sqm') and not existing_property.floor_area_sqm:
            existing_property.floor_area_sqm = new_data['floor_area_sqm']

        if new_data.get('description') and not existing_property.description:
            existing_property.description = new_data['description']

        # Always use most complete address
        if new_data.get('address') and len(new_data['address']) > len(existing_property.address):
            existing_property.address = new_data['address']

        if new_data.get('town') and not existing_property.town:
            existing_property.town = new_data['town']

        if new_data.get('county') and not existing_property.county:
            existing_property.county = new_data['county']

        if new_data.get('image_url') and not existing_property.image_url:
            existing_property.image_url = new_data['image_url']

        if new_data.get('image_urls') and not existing_property.image_urls:
            existing_property.image_urls = new_data['image_urls']

        # Update timestamp
        existing_property.updated_at = datetime.utcnow()

        # Add new source to PropertySource table
        self.add_property_source(
            existing_property.id,
            source_name,
            source_id,
            source_url
        )

        self.session.commit()

        logger.info(f"Merged property data from {source_name} into property {existing_property.id}")
        return existing_property

    def add_property_source(
        self,
        property_id: int,
        source_name: str,
        source_id: str = None,
        source_url: str = None
    ) -> PropertySource:
        """
        Add or update property source record

        Args:
            property_id: Property ID
            source_name: Name of data source
            source_id: External ID from source system
            source_url: URL to source listing

        Returns:
            PropertySource object
        """
        # Check if source already exists
        existing_source = self.session.query(PropertySource).filter(
            and_(
                PropertySource.property_id == property_id,
                PropertySource.source_name == source_name,
                PropertySource.source_id == source_id
            )
        ).first()

        if existing_source:
            # Update last_seen_at
            existing_source.last_seen_at = datetime.utcnow()
            existing_source.is_active = True
            self.session.commit()
            return existing_source

        # Create new source record
        new_source = PropertySource(
            property_id=property_id,
            source_name=source_name,
            source_id=source_id,
            source_url=source_url,
            imported_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            is_active=True
        )

        self.session.add(new_source)
        self.session.commit()

        return new_source

    def deduplicate_batch(
        self,
        properties: List[Dict],
        source_name: str,
        dry_run: bool = False
    ) -> Tuple[int, int, int]:
        """
        Process a batch of properties for deduplication

        Args:
            properties: List of property dictionaries
            source_name: Name of data source
            dry_run: If True, only report matches without merging

        Returns:
            Tuple of (new_properties, duplicates_found, duplicates_merged)
        """
        new_properties = 0
        duplicates_found = 0
        duplicates_merged = 0

        for prop_data in properties:
            address = prop_data.get('address')
            postcode = prop_data.get('postcode')

            if not address or not postcode:
                logger.warning(f"Skipping property with missing address/postcode: {prop_data}")
                continue

            # Look for duplicate
            duplicate = self.find_duplicate(address, postcode)

            if duplicate:
                duplicates_found += 1

                if not dry_run:
                    # Merge data into existing property
                    self.merge_property_data(
                        duplicate,
                        prop_data,
                        source_name,
                        prop_data.get('source_id'),
                        prop_data.get('source_url')
                    )
                    duplicates_merged += 1
            else:
                # Create new property
                if not dry_run:
                    new_property = Property(**{
                        k: v for k, v in prop_data.items()
                        if k not in ['source_id', 'source_url', 'source_name', 'imported_at']
                    })
                    self.session.add(new_property)
                    self.session.flush()  # Get property ID

                    # Add source
                    self.add_property_source(
                        new_property.id,
                        source_name,
                        prop_data.get('source_id'),
                        prop_data.get('source_url')
                    )

                new_properties += 1

        if not dry_run:
            self.session.commit()

        logger.info(
            f"Batch deduplication complete: {new_properties} new, "
            f"{duplicates_found} duplicates found, {duplicates_merged} merged"
        )

        return new_properties, duplicates_found, duplicates_merged

    def mark_inactive_sources(self, days_threshold: int = 7) -> int:
        """
        Mark property sources as inactive if not seen in recent imports
        Helps identify properties that may have been sold/removed

        Args:
            days_threshold: Number of days since last_seen_at to mark as inactive

        Returns:
            Number of sources marked inactive
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)

        inactive_count = self.session.query(PropertySource).filter(
            and_(
                PropertySource.last_seen_at < cutoff_date,
                PropertySource.is_active == True
            )
        ).update({'is_active': False})

        self.session.commit()

        logger.info(f"Marked {inactive_count} sources as inactive (not seen in {days_threshold} days)")
        return inactive_count


if __name__ == '__main__':
    """
    Command-line interface for testing deduplication
    """
    import click
    from backend.models.base import SessionLocal

    @click.command()
    @click.option('--dry-run', is_flag=True, help='Report matches without merging')
    @click.option('--threshold', default=85, help='Similarity threshold (0-100)')
    @click.option('--batch', is_flag=True, help='Run batch deduplication on existing properties')
    def cli(dry_run: bool, threshold: int, batch: bool):
        """Property deduplication utility"""
        logger.add("logs/deduplication.log", rotation="100 MB")

        db_session = SessionLocal()
        deduplicator = PropertyDeduplicator(db_session, threshold)

        if batch:
            # Mark inactive sources
            inactive_count = deduplicator.mark_inactive_sources(days_threshold=7)
            print(f"✅ Marked {inactive_count} sources as inactive")

        print("Deduplication service ready")

    cli()
