from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Sample Socrata API data
# ---------------------------------------------------------------------------

def _make_dataset(name, dataset_id, dtype="dataset", agency="Test Agency",
                  category="Test Category", domain_tag="test-tag",
                  domain_category="Test Domain Category",
                  columns_field_name=None, columns_description=None,
                  parent_fxf=None, blob_mime_type=None):
    """Helper to build a single dataset dict matching the Socrata API shape."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "resource": {
            "name": name,
            "id": dataset_id,
            "type": dtype,
            "createdAt": now_iso,
            "data_updated_at": now_iso,
            "updated_at": now_iso,
            "columns_field_name": columns_field_name or ["col_a", "col_b"],
            "columns_description": columns_description or ["Column A desc", "Column B desc"],
            "description": f"Description for {name}",
            "parent_fxf": parent_fxf or [],
            "blob_mime_type": blob_mime_type,
        },
        "classification": {
            "categories": [category],
            "domain_metadata": [
                {"key": "Dataset-Information_Agency", "value": agency},
            ],
            "domain_category": domain_category,
            "domain_tags": [domain_tag],
        },
        "permalink": f"https://data.example.com/d/{dataset_id}",
    }


@pytest.fixture
def sample_datasets():
    """Three sample datasets mimicking the Socrata discovery API response."""
    return [
        _make_dataset("Housing Data", "abcd-1234", agency="Housing Authority",
                       category="Housing", domain_tag="housing",
                       domain_category="Social Services"),
        _make_dataset("Traffic Counts", "efgh-5678", agency="Dept of Transportation",
                       category="Transportation", domain_tag="traffic",
                       domain_category="Infrastructure"),
        _make_dataset("Greenhouse Gas Inventory", "ijkl-9012", agency="Dept of Environment",
                       category="Environment", domain_tag="emissions",
                       domain_category="Environment"),
    ]


@pytest.fixture
def sample_metadata():
    """Sample metadata dict matching Socrata get_metadata() response."""
    return {
        "columns": [
            {
                "fieldName": "col_a",
                "name": "Column A",
                "cachedContents": {"count": "500"},
            },
            {
                "fieldName": "col_b",
                "name": "Column B",
                "cachedContents": {"count": "500"},
            },
        ],
    }


# ---------------------------------------------------------------------------
# Mock Socrata client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_socrata(sample_datasets, sample_metadata):
    """Patches sodapy.Socrata so no real API calls are made.

    Returns the mock client instance for further assertion / configuration.
    """
    mock_client = MagicMock()
    mock_client.datasets.return_value = sample_datasets
    mock_client.get_metadata.return_value = sample_metadata
    mock_client.get.return_value = [{"col_a": "1", "col_b": "2"}]
    mock_client.get_all.return_value = iter([{"col_a": "1", "col_b": "2"}])

    with patch("sodakit.api.Socrata", return_value=mock_client) as cls_mock:
        yield mock_client


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Sets Socrata credential env vars for the duration of the test."""
    monkeypatch.setenv("APP_TOKEN", "test-token")
    monkeypatch.setenv("USERNAME", "test-user")
    monkeypatch.setenv("PASSWORD", "test-pass")


# ---------------------------------------------------------------------------
# Convenience: ready-to-use client instances
# ---------------------------------------------------------------------------

@pytest.fixture
def sodakit_instance(mock_socrata, mock_env_vars, tmp_path, monkeypatch):
    """A MoreSocrata instance backed by mocked Socrata client and tmp data dir."""
    from sodakit import MoreSocrata

    obj = MoreSocrata(domain="data.example.com", domain_id="TEST")
    obj.data_path = tmp_path
    obj._domain_dataset_dir = tmp_path / "TEST"
    return obj


@pytest.fixture
def sodakit_data_instance(mock_socrata, mock_env_vars, tmp_path):
    """A MoreSocrataData instance with dataset_id pre-set."""
    from sodakit import MoreSocrataData

    obj = MoreSocrataData(domain="data.example.com", domain_id="TEST",
                          dataset_id="abcd-1234")
    obj.data_path = tmp_path
    obj._domain_dataset_dir = tmp_path / "TEST"
    return obj
