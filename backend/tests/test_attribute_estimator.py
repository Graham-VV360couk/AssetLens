"""
Unit tests for PropertyAttributeEstimator.

Run with:  pytest backend/tests/test_attribute_estimator.py -v
"""
from unittest.mock import MagicMock, patch
import pytest

from backend.services.attribute_estimator import (
    PropertyAttributeEstimator,
    AttributeField,
    confidence_label,
    BEDROOM_RULES,
    BATHROOM_RULES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_prop(**kwargs):
    """Create a mock Property object with the given attributes."""
    prop = MagicMock()
    prop.id = kwargs.get('id', 1)
    prop.address = kwargs.get('address', '1 Test Street')
    prop.postcode = kwargs.get('postcode', 'WD18 0AB')
    prop.property_type = kwargs.get('property_type', None)
    prop.bedrooms = kwargs.get('bedrooms', None)
    prop.bathrooms = kwargs.get('bathrooms', None)
    prop.reception_rooms = kwargs.get('reception_rooms', None)
    prop.floor_area_sqm = kwargs.get('floor_area_sqm', None)
    prop.plot_size_sqm = kwargs.get('plot_size_sqm', None)
    prop.description = kwargs.get('description', None)
    prop.asking_price = kwargs.get('asking_price', 300000)
    return prop


def make_estimator():
    """Create an estimator with a mock DB session."""
    db = MagicMock()
    # Mock LR query to return nothing by default
    db.query.return_value.filter.return_value.limit.return_value.all.return_value = []
    estimator = PropertyAttributeEstimator(db)
    return estimator


# ---------------------------------------------------------------------------
# confidence_label
# ---------------------------------------------------------------------------

class TestConfidenceLabel:
    def test_very_high(self):
        assert confidence_label(0.95) == 'very_high'
        assert confidence_label(1.00) == 'very_high'

    def test_high(self):
        assert confidence_label(0.75) == 'high'
        assert confidence_label(0.89) == 'high'

    def test_moderate(self):
        assert confidence_label(0.55) == 'moderate'
        assert confidence_label(0.74) == 'moderate'

    def test_low(self):
        assert confidence_label(0.35) == 'low'
        assert confidence_label(0.54) == 'low'

    def test_very_low(self):
        assert confidence_label(0.00) == 'very_low'
        assert confidence_label(0.34) == 'very_low'


# ---------------------------------------------------------------------------
# AttributeField
# ---------------------------------------------------------------------------

class TestAttributeField:
    def test_unknown_factory(self):
        f = AttributeField.unknown('test reason')
        assert f.status == 'unknown'
        assert f.value is None
        assert f.confidence == 0.0
        assert f.explanation == 'test reason'

    def test_to_dict_excludes_none(self):
        f = AttributeField(status='known', value=3, confidence=0.9,
                           confidence_label='very_high', source='listing',
                           explanation='test')
        d = f.to_dict()
        assert 'last_updated' not in d  # None field excluded
        assert d['value'] == 3
        assert d['status'] == 'known'


# ---------------------------------------------------------------------------
# Property type resolution
# ---------------------------------------------------------------------------

class TestPropertyTypeResolution:
    def test_from_listing(self):
        est = make_estimator()
        prop = make_prop(property_type='semi-detached')
        result = est.estimate(prop)
        pt = result['profile']['property_type']
        assert pt['status'] == 'known'
        assert pt['value'] == 'semi-detached'
        assert pt['source'] == 'listing'
        assert pt['confidence'] >= 0.90

    def test_from_description_text(self):
        est = make_estimator()
        prop = make_prop(description='Beautiful detached house with garage.')
        result = est.estimate(prop)
        pt = result['profile']['property_type']
        assert pt['status'] == 'inferred'
        assert pt['value'] == 'detached'
        assert pt['source'] == 'listing_text'

    def test_unknown_when_no_data(self):
        est = make_estimator()
        prop = make_prop()
        result = est.estimate(prop)
        pt = result['profile']['property_type']
        assert pt['status'] == 'unknown'

    def test_user_override_wins_over_listing(self):
        est = make_estimator()
        prop = make_prop(property_type='terraced')
        result = est.estimate(prop, overrides={'property_type': 'detached'})
        pt = result['profile']['property_type']
        assert pt['value'] == 'detached'
        assert pt['source'] == 'user_override'
        assert pt['confidence'] == 1.0


# ---------------------------------------------------------------------------
# Floor area resolution
# ---------------------------------------------------------------------------

class TestFloorAreaResolution:
    def test_from_listing(self):
        est = make_estimator()
        prop = make_prop(floor_area_sqm=95.0)
        result = est.estimate(prop)
        fa = result['profile']['floor_area']
        assert fa['status'] == 'known'
        assert fa['value']['sqm'] == 95.0
        assert 'sqft' in fa['value']

    def test_sqft_conversion_from_description(self):
        est = make_estimator()
        # 1,020 sq ft ≈ 94.8 sqm
        prop = make_prop(description='Spacious home of 1,020 sq ft.')
        result = est.estimate(prop)
        fa = result['profile']['floor_area']
        assert fa['status'] == 'inferred'
        assert fa['source'] == 'listing_text'
        assert 90 < fa['value']['sqm'] < 100

    def test_unknown_when_no_data(self):
        est = make_estimator()
        prop = make_prop()
        result = est.estimate(prop)
        assert result['profile']['floor_area']['status'] == 'unknown'


# ---------------------------------------------------------------------------
# Bedroom estimation
# ---------------------------------------------------------------------------

class TestBedroomEstimation:
    def test_from_listing(self):
        est = make_estimator()
        prop = make_prop(bedrooms=4)
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        assert beds['status'] == 'known'
        assert beds['value'] == 4
        assert beds['confidence'] >= 0.90

    def test_heuristic_semi_detached_95sqm(self):
        est = make_estimator()
        prop = make_prop(property_type='semi-detached', floor_area_sqm=95.0)
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        assert beds['status'] == 'estimated'
        assert beds['value'] == 3
        assert beds['source'] == 'floor_area_heuristic'

    def test_heuristic_flat_55sqm(self):
        est = make_estimator()
        prop = make_prop(property_type='flat', floor_area_sqm=55.0)
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        assert beds['status'] == 'estimated'
        assert beds['value'] == 1

    def test_heuristic_detached_large(self):
        est = make_estimator()
        prop = make_prop(property_type='detached', floor_area_sqm=200.0)
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        assert beds['value'] == 5

    def test_description_extraction(self):
        est = make_estimator()
        prop = make_prop(description='This lovely 3 bedroom semi-detached property...')
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        assert beds['status'] == 'inferred'
        assert beds['value'] == 3

    def test_user_override(self):
        est = make_estimator()
        prop = make_prop(bedrooms=3)
        result = est.estimate(prop, overrides={'bedrooms': 4})
        beds = result['profile']['bedrooms']
        assert beds['value'] == 4
        assert beds['source'] == 'user_override'

    def test_unknown_without_area_or_type(self):
        est = make_estimator()
        prop = make_prop()
        result = est.estimate(prop)
        assert result['profile']['bedrooms']['status'] == 'unknown'


# ---------------------------------------------------------------------------
# Bathroom estimation
# ---------------------------------------------------------------------------

class TestBathroomEstimation:
    def test_from_listing(self):
        est = make_estimator()
        prop = make_prop(bathrooms=2)
        result = est.estimate(prop)
        baths = result['profile']['bathrooms']
        assert baths['status'] == 'known'
        assert baths['value'] == 2

    def test_heuristic_3_beds(self):
        est = make_estimator()
        prop = make_prop(bedrooms=3)
        result = est.estimate(prop)
        baths = result['profile']['bathrooms']
        assert baths['status'] == 'estimated'
        # 3 beds → 1–2 range
        assert isinstance(baths['value'], dict)
        assert baths['value']['min'] == 1
        assert baths['value']['max'] == 2

    def test_heuristic_1_bed(self):
        est = make_estimator()
        prop = make_prop(bedrooms=1)
        result = est.estimate(prop)
        baths = result['profile']['bathrooms']
        assert baths['value'] == 1

    def test_reduced_confidence_when_beds_estimated(self):
        """Bathroom confidence should be lower when bedrooms were themselves estimated."""
        est = make_estimator()
        prop = make_prop(property_type='semi-detached', floor_area_sqm=95.0)
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        baths = result['profile']['bathrooms']
        assert beds['status'] == 'estimated'
        # Bathroom confidence should be ≤ base rule confidence minus penalty
        assert baths['confidence'] < 0.60


# ---------------------------------------------------------------------------
# Reception room estimation
# ---------------------------------------------------------------------------

class TestReceptionEstimation:
    def test_from_listing(self):
        est = make_estimator()
        prop = make_prop(reception_rooms=2)
        result = est.estimate(prop)
        recep = result['profile']['reception_rooms']
        assert recep['status'] == 'known'
        assert recep['value'] == 2

    def test_flat_2_beds(self):
        est = make_estimator()
        prop = make_prop(property_type='flat', bedrooms=2)
        result = est.estimate(prop)
        recep = result['profile']['reception_rooms']
        assert recep['status'] == 'estimated'
        assert recep['value'] == 1

    def test_detached_4_beds(self):
        est = make_estimator()
        prop = make_prop(property_type='detached', bedrooms=4)
        result = est.estimate(prop)
        recep = result['profile']['reception_rooms']
        assert recep['value'] == 2

    def test_description_extraction(self):
        est = make_estimator()
        prop = make_prop(description='The property offers two reception rooms and a study.')
        result = est.estimate(prop)
        recep = result['profile']['reception_rooms']
        assert recep['status'] == 'inferred'
        assert recep['value'] == 2


# ---------------------------------------------------------------------------
# Source priority
# ---------------------------------------------------------------------------

class TestSourcePriority:
    def test_listing_beats_heuristic_for_bedrooms(self):
        est = make_estimator()
        # Listing says 5 beds, floor area heuristic would say 3
        prop = make_prop(bedrooms=5, property_type='semi-detached', floor_area_sqm=90.0)
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        assert beds['value'] == 5
        assert beds['source'] == 'listing'

    def test_override_beats_listing(self):
        est = make_estimator()
        prop = make_prop(bedrooms=3, property_type='detached')
        result = est.estimate(prop, overrides={'bedrooms': 5})
        assert result['profile']['bedrooms']['value'] == 5
        assert result['profile']['bedrooms']['source'] == 'user_override'


# ---------------------------------------------------------------------------
# Contradiction detection
# ---------------------------------------------------------------------------

class TestContradictionDetection:
    def test_too_many_beds_for_small_area(self):
        est = make_estimator()
        prop = make_prop(bedrooms=6, floor_area_sqm=70.0)
        result = est.estimate(prop)
        warnings = result['debug']['warnings']
        assert len(warnings) > 0
        assert '6 bedrooms' in warnings[0]

    def test_1_bed_massive_area(self):
        est = make_estimator()
        prop = make_prop(bedrooms=1, floor_area_sqm=250.0)
        result = est.estimate(prop)
        warnings = result['debug']['warnings']
        assert len(warnings) > 0

    def test_no_false_positive_normal_property(self):
        est = make_estimator()
        prop = make_prop(bedrooms=3, floor_area_sqm=90.0)
        result = est.estimate(prop)
        assert result['debug']['warnings'] == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_flat_vs_maisonette_listing(self):
        est = make_estimator()
        prop = make_prop(property_type='maisonette', floor_area_sqm=85.0)
        result = est.estimate(prop)
        beds = result['profile']['bedrooms']
        assert beds['status'] == 'estimated'
        assert beds['value'] == 2  # maisonette 65–90 sqm → 2 beds

    def test_property_with_no_data_at_all(self):
        est = make_estimator()
        prop = make_prop()
        result = est.estimate(prop)
        profile = result['profile']
        # Most fields should be unknown
        unknown_count = sum(1 for f in profile.values() if f['status'] == 'unknown')
        assert unknown_count >= 4

    def test_description_with_sqft_area(self):
        est = make_estimator()
        prop = make_prop(description='A spacious 850 sq ft apartment in central location.')
        result = est.estimate(prop)
        fa = result['profile']['floor_area']
        assert fa['status'] == 'inferred'
        assert 75 < fa['value']['sqm'] < 85

    def test_override_propagates_to_dependents(self):
        """Overriding bedrooms should update bathroom estimate."""
        est = make_estimator()
        # Start with 2 beds (bathrooms = 1)
        prop = make_prop(bedrooms=2)
        result_base = est.estimate(prop)
        assert result_base['profile']['bathrooms']['value'] == 1

        # Override to 5 beds → bathrooms should become 2–3
        result_override = est.estimate(prop, overrides={'bedrooms': 5})
        baths = result_override['profile']['bathrooms']
        assert isinstance(baths['value'], dict)
        assert baths['value']['min'] == 2

    def test_incomplete_source_data(self):
        """Property with description but no structured fields — should still estimate."""
        est = make_estimator()
        prop = make_prop(description='A lovely 4 bedroom detached home with 2 bathrooms.')
        result = est.estimate(prop)
        assert result['profile']['bedrooms']['value'] == 4
        assert result['profile']['bedrooms']['source'] == 'listing_text'
        assert result['profile']['bathrooms']['value'] == 2
        assert result['profile']['bathrooms']['source'] == 'listing_text'

    def test_full_pipeline_authoritative_data(self):
        """All fields known from listing — every field should be 'known' status."""
        est = make_estimator()
        prop = make_prop(
            property_type='detached',
            bedrooms=4,
            bathrooms=2,
            reception_rooms=2,
            floor_area_sqm=165.0,
            plot_size_sqm=420.0,
        )
        result = est.estimate(prop)
        profile = result['profile']
        for key in ['property_type', 'floor_area', 'bedrooms', 'bathrooms', 'reception_rooms', 'plot_size']:
            assert profile[key]['status'] == 'known', f"{key} should be 'known'"

    def test_full_pipeline_no_data(self):
        """No input data — all fields unknown (no crash)."""
        est = make_estimator()
        prop = make_prop()
        result = est.estimate(prop)
        assert isinstance(result['profile'], dict)
        assert 'generated_at' in result
