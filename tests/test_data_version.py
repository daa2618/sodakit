from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from sodakit.utils.data_version import FileVersion, DatesNotFound


class TestFileVersionInit:
    def test_normalizes_file_name(self):
        fv = FileVersion(base_path="/tmp", file_name="test", extension="json")
        assert fv.file_name == "test_"

    def test_already_suffixed_file_name(self):
        fv = FileVersion(base_path="/tmp", file_name="test_", extension="json")
        assert fv.file_name == "test_"

    def test_normalizes_extension_dot(self):
        fv = FileVersion(base_path="/tmp", file_name="f", extension="csv")
        assert fv.extension == ".csv"

    def test_already_dotted_extension(self):
        fv = FileVersion(base_path="/tmp", file_name="f", extension=".csv")
        assert fv.extension == ".csv"

    def test_default_date_fmt(self):
        fv = FileVersion(base_path="/tmp", file_name="f", extension="csv")
        assert fv.date_fmt == "%m%d%Y"


class TestFolderExists:
    def test_creates_directory(self, tmp_path):
        target = tmp_path / "subdir" / "deep"
        fv = FileVersion(base_path=target, file_name="f", extension="csv")
        assert fv.folder_exists() is True
        assert target.is_dir()


class TestMakeFileName:
    def test_contains_date(self):
        fv = FileVersion(base_path="/tmp", file_name="data", extension="json")
        name = fv.make_file_name()
        today = datetime.datetime.now().strftime("%m%d%Y")
        assert today in name
        assert name.startswith("data_")
        assert name.endswith(".json")


class TestGetAllFiles:
    def test_finds_matching_files(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="report", extension="csv")
        (tmp_path / "report_01012026.csv").write_text("")
        (tmp_path / "report_01022026.csv").write_text("")
        (tmp_path / "other_01012026.csv").write_text("")
        files = fv.get_all_files()
        assert len(files) == 2

    def test_empty_when_no_match(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="nope", extension="csv")
        (tmp_path / "other.csv").write_text("")
        assert fv.get_all_files() == []


class TestFileExists:
    def test_true_when_files_present(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="f", extension="csv")
        (tmp_path / "f_01012026.csv").write_text("")
        assert fv.file_exists() is True

    def test_false_when_empty(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="f", extension="csv")
        assert fv.file_exists() is False


class TestFetchDatesFromFileNames:
    def test_extracts_dates(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="d", extension="json",
                         date_fmt="%m%d%Y")
        (tmp_path / "d_01152026.json").write_text("")
        (tmp_path / "d_02152026.json").write_text("")
        dates = fv._fetch_dates_from_file_names()
        assert len(dates) == 2
        assert dates[0] < dates[1]  # ascending by default

    def test_raises_when_no_files(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="x", extension="csv")
        with pytest.raises(DatesNotFound):
            fv._fetch_dates_from_file_names()


class TestSortFilesByDate:
    def test_ascending(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="r", extension="csv",
                         date_fmt="%m%d%Y")
        (tmp_path / "r_01012026.csv").write_text("")
        (tmp_path / "r_03012026.csv").write_text("")
        result = fv.sort_files_by_date("ascending")
        assert result[0].name < result[-1].name

    def test_invalid_order_raises(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="r", extension="csv")
        with pytest.raises(TypeError):
            fv.sort_files_by_date("random")


class TestCheckVersion:
    def test_returns_false_for_today(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="d", extension="json",
                         date_fmt="%m%d%Y")
        today_str = datetime.datetime.now().strftime("%m%d%Y")
        (tmp_path / f"d_{today_str}.json").write_text("")
        assert fv.check_version() is False

    def test_returns_true_for_old_file(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="d", extension="json",
                         date_fmt="%m%d%Y")
        (tmp_path / "d_01012020.json").write_text("")
        assert fv.check_version() is True


class TestLatestFilePath:
    def test_returns_latest(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="d", extension="csv",
                         date_fmt="%m%d%Y")
        (tmp_path / "d_01012026.csv").write_text("")
        (tmp_path / "d_03282026.csv").write_text("")
        result = fv.latest_file_path
        assert result is not None
        assert "03282026" in result.name

    def test_returns_none_when_empty(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="d", extension="csv")
        assert fv.latest_file_path is None


class TestGetLatestNFiles:
    def test_returns_n_files(self, tmp_path):
        fv = FileVersion(base_path=tmp_path, file_name="d", extension="csv",
                         date_fmt="%m%d%Y")
        (tmp_path / "d_01012026.csv").write_text("")
        (tmp_path / "d_02012026.csv").write_text("")
        (tmp_path / "d_03012026.csv").write_text("")
        result = fv.get_latest_n_files(2)
        assert len(result) == 2
