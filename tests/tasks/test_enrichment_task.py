"""Tests for Celery enrichment task."""
import pytest
from unittest.mock import patch, MagicMock


def test_enrich_property_calls_services():
    with patch('backend.tasks.enrichment.SessionLocal') as MockSession, \
         patch('backend.tasks.enrichment.PropertyDataService') as MockPD, \
         patch('backend.tasks.enrichment.analyse_property') as mock_ai:

        db = MagicMock()
        MockSession.return_value = db

        prop = MagicMock()
        prop.id = 1
        score = MagicMock()
        db.query.return_value.get.return_value = prop
        db.query.return_value.filter.return_value.first.return_value = score

        from backend.tasks.enrichment import enrich_property_task
        # Call the function directly (not via Celery)
        enrich_property_task(1)

        MockPD.return_value.enrich.assert_called_once()
        mock_ai.assert_called_once_with(1, db)
