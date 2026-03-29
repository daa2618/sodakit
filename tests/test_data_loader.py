from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import responses as responses_mock

from sodakit.utils.data_loader import (
    Dataset,
    FilePathError,
    PostProcess,
    UnsupportedExtension,
)


# =========================================================================
# Dataset
# =========================================================================

class TestDatasetInit:
    def test_requires_doc_url_or_file_path(self):
        with pytest.raises(ValueError, match="No doc_url or file_path"):
            Dataset()

    def test_accepts_doc_url(self):
        ds = Dataset(doc_url="https://example.com/data.csv")
        assert ds.doc_url == "https://example.com/data.csv"
        assert ds.file_path is None

    def test_accepts_file_path(self, tmp_path):
        fp = tmp_path / "data.csv"
        fp.write_text("a,b\n1,2\n")
        ds = Dataset(file_path=str(fp))
        assert ds.file_path == str(fp)
        assert ds.doc_url is None


class TestExtensionProperty:
    def test_returns_extension_from_url(self):
        ds = Dataset(doc_url="https://example.com/data.csv")
        assert ds._extension == ".csv"

    def test_returns_extension_from_file_path(self, tmp_path):
        fp = tmp_path / "file.json"
        fp.write_text("{}")
        ds = Dataset(file_path=str(fp))
        assert ds._extension == ".json"

    def test_returns_none_for_no_extension(self):
        ds = Dataset(doc_url="https://example.com/data")
        assert ds._extension is None

    def test_setter_override(self):
        ds = Dataset(doc_url="https://example.com/data")
        ds._extension = "text/csv"
        assert ds._extension == "text/csv"


class TestCheckExtension:
    def test_valid_extension(self):
        ds = Dataset(doc_url="https://example.com/data.csv")
        ds._check_extension(".csv")  # should not raise

    def test_unsupported_extension(self):
        ds = Dataset(doc_url="https://example.com/data.csv")
        with pytest.raises(UnsupportedExtension):
            ds._check_extension(".xyz")


class TestGithubDocUrl:
    def test_github_url_transformed(self):
        ds = Dataset(doc_url="https://github.com/user/repo/blob/main/data.csv")
        assert "raw" in ds._github_doc_url
        assert "blob" not in ds._github_doc_url

    def test_non_github_url_returns_none(self):
        ds = Dataset(doc_url="https://example.com/data.csv")
        assert ds._github_doc_url is None


class TestAssertFilePath:
    def test_raises_for_missing_file(self, tmp_path):
        ds = Dataset(file_path=str(tmp_path / "nonexistent.csv"))
        with pytest.raises(FileNotFoundError):
            ds._assert_file_path()

    def test_passes_for_existing_file(self, tmp_path):
        fp = tmp_path / "exists.csv"
        fp.write_text("a,b\n1,2\n")
        ds = Dataset(file_path=str(fp))
        ds._assert_file_path()  # should not raise


class TestLoadCsv:
    def test_load_csv_from_file(self, tmp_path):
        fp = tmp_path / "data.csv"
        fp.write_text("Name,Value\nAlice,10\nBob,20\n")
        ds = Dataset(file_path=str(fp))
        result = ds._load_csv()
        assert len(result) == 2
        assert "name" in result[0]
        assert "value" in result[0]

    @responses_mock.activate
    def test_load_csv_from_url(self):
        csv_text = "Col A,Col B\n1,2\n3,4\n"
        responses_mock.add(responses_mock.GET, "https://example.com/data.csv",
                          body=csv_text, status=200,
                          headers={"Content-Type": "text/csv"})
        ds = Dataset(doc_url="https://example.com/data.csv")
        result = ds._load_csv()
        assert len(result) == 2
        assert "col_a" in result[0]


class TestLoadJson:
    def test_load_json_from_file(self, tmp_path):
        fp = tmp_path / "data.json"
        fp.write_text(json.dumps([{"a": 1}]))
        ds = Dataset(file_path=str(fp))
        result = ds._load_json()
        assert result == [{"a": 1}]

    @responses_mock.activate
    def test_load_json_from_url(self):
        payload = [{"key": "val"}]
        responses_mock.add(responses_mock.GET, "https://example.com/data.json",
                          json=payload, status=200)
        ds = Dataset(doc_url="https://example.com/data.json")
        result = ds._load_json()
        assert result == payload


class TestLoadText:
    def test_load_text_from_file(self, tmp_path):
        fp = tmp_path / "readme.txt"
        fp.write_text("hello world")
        ds = Dataset(file_path=str(fp))
        result = ds._load_text()
        assert result == "hello world"

    @responses_mock.activate
    def test_load_text_from_url(self):
        responses_mock.add(responses_mock.GET, "https://example.com/readme.txt",
                          body="hello", status=200)
        ds = Dataset(doc_url="https://example.com/readme.txt")
        result = ds._load_text()
        assert result == "hello"


class TestLoadData:
    def test_load_csv_via_load_data(self, tmp_path):
        fp = tmp_path / "data.csv"
        fp.write_text("x,y\n1,2\n")
        ds = Dataset(file_path=str(fp))
        result = ds.load_data()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_load_json_via_load_data(self, tmp_path):
        fp = tmp_path / "data.json"
        fp.write_text(json.dumps({"a": 1}))
        ds = Dataset(file_path=str(fp))
        result = ds.load_data()
        assert result == {"a": 1}

    def test_unsupported_extension_returns_none(self, tmp_path):
        fp = tmp_path / "data.xyz"
        fp.write_text("stuff")
        ds = Dataset(file_path=str(fp))
        result = ds.load_data()
        assert result is None


# =========================================================================
# PostProcess
# =========================================================================

class TestFindYearFromYearStr:
    @pytest.mark.parametrize("input_val,expected", [
        ("2021-22", "2022"),
        ("1998-1999", "1999"),
        ("2024", "2024"),
        ("2021-22", "2022"),
        ("", ""),
        (None, ""),
    ])
    def test_various_inputs(self, input_val, expected):
        assert PostProcess.find_year_from_year_str(input_val) == expected

    def test_non_string_returns_str(self):
        assert PostProcess.find_year_from_year_str(2024) == "2024"


class TestSetColumnsFromIndexAndDropRows:
    def test_single_index(self):
        df = pd.DataFrame([
            ["Name", "Age"],
            ["Alice", "30"],
            ["Bob", "25"],
        ])
        result = PostProcess.set_columns_from_index_and_drop_rows(df, 0)
        assert list(result.columns) == ["Name", "Age"]
        assert len(result) == 2

    def test_invalid_type_raises(self):
        df = pd.DataFrame([[1, 2]])
        with pytest.raises(TypeError):
            PostProcess.set_columns_from_index_and_drop_rows(df, 3.5)


class TestSetColumnsFromIndexSimple:
    def test_basic(self):
        df = pd.DataFrame([
            ["header_a", "header_b"],
            ["1", "2"],
            ["3", "4"],
        ])
        result = PostProcess._set_columns_from_index_and_drop_rows(df, 0)
        assert len(result) == 2
        assert all(c.islower() or c == "_" for c in "".join(result.columns))


class TestConvertDataTypes:
    def test_float_conversion(self):
        df = pd.DataFrame({"a": ["1", "2"], "b": ["3.0", "4.0"]})
        result = PostProcess.convert_data_types_of_cols(df, "float")
        assert result["a"].dtype == float

    def test_invalid_type_raises(self):
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(TypeError):
            PostProcess.convert_data_types_of_cols(df, "datetime")

    def test_unconvertible_column_retained(self):
        df = pd.DataFrame({"a": ["hello", "world"]})
        result = PostProcess.convert_data_types_of_cols(df, "int")
        assert result["a"].dtype == object
