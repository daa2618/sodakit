from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from sodakit.api import MoreSocrata, MoreSocrataData
from sodakit.exceptions import DatasetNotFound, OrganizationNotFound


# =========================================================================
# MoreSocrata
# =========================================================================

class TestMoreSocrataInit:
    def test_stores_domain(self, sodakit_instance):
        assert sodakit_instance.domain == "data.example.com"
        assert sodakit_instance.domain_id == "TEST"
        assert sodakit_instance.domain_url == "https://data.example.com/"


class TestAllDatasetNames:
    def test_returns_sorted_names(self, sodakit_instance, sample_datasets):
        sodakit_instance._ALL_DATASETS = sample_datasets
        names = sodakit_instance.ALL_DATASET_NAMES
        assert names == sorted(names)
        assert len(names) == 3

    def test_empty_when_no_datasets(self, sodakit_instance):
        sodakit_instance._ALL_DATASETS = []
        # ALL_DATASET_NAMES checks truthiness, empty list → empty result
        assert sodakit_instance.ALL_DATASET_NAMES == []


class TestAllCategories:
    def test_returns_unique_categories(self, sodakit_instance, sample_datasets):
        sodakit_instance._ALL_DATASETS = sample_datasets
        cats = sodakit_instance.ALL_CATEGORIES
        assert isinstance(cats, list)
        assert "Housing" in cats


class TestAllAgencies:
    def test_returns_unique_agencies(self, sodakit_instance, sample_datasets):
        sodakit_instance._ALL_DATASETS = sample_datasets
        agencies = sodakit_instance.ALL_AGENCIES
        assert "Housing Authority" in agencies
        assert "Dept of Transportation" in agencies


class TestAllDomainTags:
    def test_returns_unique_tags(self, sodakit_instance, sample_datasets):
        sodakit_instance._ALL_DATASETS = sample_datasets
        tags = sodakit_instance.ALL_DOMAIN_TAGS
        assert "housing" in tags
        assert "traffic" in tags


class TestAllDomainCategories:
    def test_returns_unique(self, sodakit_instance, sample_datasets):
        sodakit_instance._ALL_DATASETS = sample_datasets
        result = sodakit_instance.ALL_DOMAIN_CATEGORIES
        assert "Social Services" in result


class TestAllDataTypes:
    def test_returns_unique_types(self, sodakit_instance, sample_datasets):
        sodakit_instance._ALL_DATASETS = sample_datasets
        types = sodakit_instance.ALL_DATA_TYPES
        assert "dataset" in types


class TestDatasetsCaching:
    def test_caches_after_first_call(self, sodakit_instance, sample_datasets):
        sodakit_instance._ALL_DATASETS = sample_datasets
        first = sodakit_instance._ALL_DATASETS_IN_DOMAIN
        second = sodakit_instance._ALL_DATASETS_IN_DOMAIN
        assert first is second


# =========================================================================
# MoreSocrataData
# =========================================================================

class TestGetResourceForDataset:
    def test_finds_resource(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance._get_resource_for_dataset()
        assert len(result) == 1
        assert result[0]["id"] == "abcd-1234"

    def test_raises_when_not_found(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        sodakit_data_instance.dataset_id = "zzzz-0000"
        with pytest.raises(DatasetNotFound):
            sodakit_data_instance._get_resource_for_dataset()

    def test_warns_when_no_id(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        sodakit_data_instance.dataset_id = None
        result = sodakit_data_instance._get_resource_for_dataset()
        assert result is None


class TestGetMetadataForDataset:
    def test_returns_metadata(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        meta = sodakit_data_instance._get_metadata_for_dataset()
        assert "columns" in meta


class TestGetColumnDescription:
    def test_returns_dict(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance.get_column_description_for_dataset()
        assert isinstance(result, dict)
        assert "col_a" in result


class TestSearchAvailableDatasets:
    def test_finds_matching(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance.search_available_datasets("Housing")
        assert any("Housing" in name for name in result)

    def test_raises_when_none_found(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        with pytest.raises(DatasetNotFound):
            sodakit_data_instance.search_available_datasets("zzzznonexistent")


class TestGetDatasetIdForName:
    def test_exact_match(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance.get_dataset_id_for_dataset_name("Housing Data")
        assert result == "abcd-1234"

    def test_raises_when_not_found(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        with pytest.raises(DatasetNotFound):
            sodakit_data_instance.get_dataset_id_for_dataset_name("Nonexistent")


class TestSearchAgencies:
    def test_finds_agency(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance.search_agencies("Housing")
        assert "Housing Authority" in result

    def test_raises_when_not_found(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        with pytest.raises(OrganizationNotFound):
            sodakit_data_instance.search_agencies("zzzznonexistent")


class TestFilterDatasetsForDataType:
    def test_filters_by_type(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance.filter_datasets_for_data_type("dataset")
        assert len(result) == 3

    def test_raises_for_invalid_type(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        with pytest.raises(DatasetNotFound, match="Data type mismatch"):
            sodakit_data_instance.filter_datasets_for_data_type("invalid_type")


class TestFilterDataForDomainTags:
    def test_filters_by_tag(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance.filter_data_for_domain_tags("housing")
        assert len(result) >= 1
        assert any(r["dataset_name"] == "Housing Data" for r in result)


class TestQueryDataset:
    def test_returns_json(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        with patch("sodakit.api.Response") as MockResponse:
            mock_resp = MagicMock()
            mock_resp.get_json_from_response.return_value = [{"col_a": "1"}]
            MockResponse.return_value = mock_resp
            result = sodakit_data_instance.query_dataset("SELECT * LIMIT 10")
        assert result == [{"col_a": "1"}]

    def test_returns_none_without_dataset_id(self, sodakit_data_instance):
        sodakit_data_instance.dataset_id = None
        result = sodakit_data_instance.query_dataset("SELECT *")
        assert result is None


class TestTryLoadingDataset:
    def test_returns_data_for_standard_type(self, sodakit_data_instance, sample_datasets):
        sodakit_data_instance._ALL_DATASETS = sample_datasets
        result = sodakit_data_instance.try_loading_dataset()
        assert isinstance(result, list)

    def test_returns_none_without_dataset_id(self, sodakit_data_instance):
        sodakit_data_instance.dataset_id = None
        result = sodakit_data_instance.try_loading_dataset()
        assert result is None
