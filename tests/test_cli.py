"""Tests for the sodakit CLI."""
from __future__ import annotations

import json

import pytest

from sodakit.cli import main


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

BASE_ARGS = ["--domain", "data.example.com", "--domain-id", "TEST"]


def run_cli(capsys, *args):
    """Run the CLI with given args and return (stdout, stderr, exit_code)."""
    try:
        main(list(args))
        captured = capsys.readouterr()
        return captured.out, captured.err, 0
    except SystemExit as e:
        captured = capsys.readouterr()
        return captured.out, captured.err, e.code


# ---------------------------------------------------------------------------
# Parser validation
# ---------------------------------------------------------------------------

class TestParserValidation:

    def test_missing_domain(self, capsys):
        _, _, code = run_cli(capsys, "--domain-id", "X", "list", "datasets")
        assert code == 2

    def test_missing_domain_id(self, capsys):
        _, _, code = run_cli(capsys, "--domain", "x.com", "list", "datasets")
        assert code == 2

    def test_no_subcommand(self, capsys):
        _, _, code = run_cli(capsys, *BASE_ARGS)
        assert code == 2

    def test_load_missing_dataset_id(self, capsys):
        _, _, code = run_cli(capsys, *BASE_ARGS, "load")
        assert code == 2


# ---------------------------------------------------------------------------
# List subcommands
# ---------------------------------------------------------------------------

class TestListCommand:

    def test_list_datasets(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "datasets")
        assert code == 0
        assert "Greenhouse Gas Inventory" in out
        assert "Housing Data" in out
        assert "Traffic Counts" in out

    def test_list_agencies(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "agencies")
        assert code == 0
        assert "Housing Authority" in out

    def test_list_categories(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "categories")
        assert code == 0
        assert "Housing" in out

    def test_list_tags(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "tags")
        assert code == 0
        assert "housing" in out

    def test_list_types(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "types")
        assert code == 0
        assert "dataset" in out

    def test_list_datasets_limit(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "datasets", "--limit", "2")
        assert code == 0
        # Should have header + separator + exactly 2 data lines
        lines = [l for l in out.strip().split("\n") if l.strip()]
        data_lines = lines[2:]  # skip header and separator
        assert len(data_lines) == 2

    def test_list_datasets_sort(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "datasets", "--sort")
        assert code == 0
        lines = [l for l in out.strip().split("\n") if l.strip()]
        data_lines = lines[2:]  # skip header and separator
        assert data_lines == sorted(data_lines, key=str.casefold)

    def test_list_datasets_sort_and_limit(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "datasets", "--sort", "--limit", "2")
        assert code == 0
        lines = [l for l in out.strip().split("\n") if l.strip()]
        data_lines = lines[2:]
        assert len(data_lines) == 2
        assert data_lines == sorted(data_lines, key=str.casefold)

    def test_list_datasets_limit_json(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "--json", "list", "datasets", "--limit", "1")
        assert code == 0
        data = json.loads(out)
        assert len(data) == 1

    def test_list_datasets_json(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "--json", "list", "datasets")
        assert code == 0
        data = json.loads(out)
        assert isinstance(data, list)
        assert "Housing Data" in data


# ---------------------------------------------------------------------------
# Search subcommands
# ---------------------------------------------------------------------------

class TestSearchCommand:

    def test_search_datasets(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "search", "datasets", "Housing")
        assert code == 0
        assert "Housing Data" in out

    def test_search_tags(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "search", "tags", "housing")
        assert code == 0
        assert "housing" in out

    def test_search_agencies(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "search", "agencies", "Housing")
        assert code == 0
        assert "Housing Authority" in out

    def test_search_datasets_json(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "--json", "search", "datasets", "Housing")
        assert code == 0
        data = json.loads(out)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Get ID
# ---------------------------------------------------------------------------

class TestGetIdCommand:

    def test_get_id(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "get-id", "Housing Data")
        assert code == 0
        assert "abcd-1234" in out

    def test_get_id_json(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "--json", "get-id", "Housing Data")
        assert code == 0
        data = json.loads(out)
        assert "abcd-1234" in str(data)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

class TestLoadCommand:

    def test_load_dataset(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "load", "--dataset-id", "abcd-1234",
        )
        assert code == 0
        assert len(out.strip()) > 0

    def test_load_dataset_with_limit(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "load", "--dataset-id", "abcd-1234", "--limit", "10",
        )
        assert code == 0

    def test_load_dataset_json(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "--json", "load", "--dataset-id", "abcd-1234",
        )
        assert code == 0
        json.loads(out)  # should be valid JSON


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class TestQueryCommand:

    def test_query_dataset(self, sodakit_data_instance, mock_socrata, capsys):
        mock_socrata.get.return_value = [{"col_a": "1", "col_b": "2"}]
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "query", "--dataset-id", "abcd-1234",
            "SELECT * LIMIT 10",
        )
        assert code == 0
        assert len(out.strip()) > 0


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------

class TestColumnsCommand:

    def test_columns(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "columns", "--dataset-id", "abcd-1234",
        )
        assert code == 0
        assert "col_a" in out or "Column A" in out

    def test_columns_json(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "--json", "columns", "--dataset-id", "abcd-1234",
        )
        assert code == 0
        data = json.loads(out)
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

class TestFilterCommand:

    def test_filter_tag(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "filter", "tag", "housing")
        assert code == 0
        assert "Housing Data" in out

    def test_filter_type(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "filter", "type", "dataset")
        assert code == 0

    def test_filter_agency(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "filter", "agency", "Housing Authority",
        )
        assert code == 0
        assert "Housing" in out

    def test_filter_tag_json(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(
            capsys, *BASE_ARGS, "--json", "filter", "tag", "housing",
        )
        assert code == 0
        data = json.loads(out)
        assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

class TestOutputFormatting:

    def test_table_has_separator(self, sodakit_data_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "filter", "tag", "housing")
        assert code == 0
        lines = out.strip().split("\n")
        # Table should have header, separator, and at least one data row
        if len(lines) >= 2:
            assert set(lines[1].replace(" ", "")) <= {"-"}

    def test_list_has_header(self, sodakit_instance, capsys):
        out, _, code = run_cli(capsys, *BASE_ARGS, "list", "datasets")
        assert code == 0
        assert "Datasets" in out
        assert "---" in out
