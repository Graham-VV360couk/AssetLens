"""Tests for personalised deal score adjustments."""
import pytest
from unittest.mock import MagicMock


def _make_score(investment_score=65, gross_yield_pct=7.5, price_band='good'):
    s = MagicMock()
    s.investment_score = investment_score
    s.gross_yield_pct = gross_yield_pct
    s.price_band = price_band
    s.estimated_value = 200000
    s.pd_avm = 210000
    s.price_score = 30
    s.yield_score = 20
    s.area_trend_score = 10
    s.hmo_opportunity_score = 5
    return s


def _make_profile(strategy='btl', experience='first_time', uk_resident=True,
                  main_residence=False, credit_history='clean', target_location=None,
                  max_deposit=None, readiness='immediate', hmo_experience=False):
    p = MagicMock()
    p.strategy = strategy
    p.investment_experience = experience
    p.uk_resident = uk_resident
    p.main_residence = main_residence
    p.credit_history = credit_history
    p.target_location = target_location
    p.max_deposit = max_deposit
    p.readiness = readiness
    p.hmo_experience = hmo_experience
    return p


def test_btl_strategy_label():
    from backend.services.personalised_score_service import personalise
    result = personalise(_make_score(), _make_profile(strategy='btl'), asking_price=200000, postcode='LS6 1AA')
    assert result['label'] == 'BTL Score'


def test_no_strategy_generic_label():
    from backend.services.personalised_score_service import personalise
    result = personalise(_make_score(), _make_profile(strategy=None), asking_price=200000, postcode='LS6 1AA')
    assert result['label'] == 'Deal Score'


def test_non_uk_resident_sdlt_surcharge_flagged():
    from backend.services.personalised_score_service import personalise
    result = personalise(_make_score(), _make_profile(uk_resident=False), asking_price=200000, postcode='LS6 1AA')
    assert any('non-resident' in n.lower() or 'surcharge' in n.lower() for n in result['notes'])


def test_adverse_credit_flags_bridging():
    from backend.services.personalised_score_service import personalise
    result = personalise(_make_score(), _make_profile(credit_history='adverse'), asking_price=200000, postcode='LS6 1AA')
    assert any('bridging' in n.lower() for n in result['notes'])


def test_location_mismatch_flagged():
    from backend.services.personalised_score_service import personalise
    result = personalise(_make_score(), _make_profile(target_location='Manchester'), asking_price=200000, postcode='LS6 1AA')
    assert result['location_mismatch'] is True


def test_first_time_adds_explanatory_notes():
    from backend.services.personalised_score_service import personalise
    result = personalise(_make_score(), _make_profile(experience='first_time'), asking_price=200000, postcode='LS6 1AA')
    assert len(result['notes']) > 0
