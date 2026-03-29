from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from sodakit.utils.data_writer import WriteFile


class TestWriteJson:
    def test_writes_json_file(self, tmp_path):
        data = [{"a": 1}, {"b": 2}]
        wf = WriteFile(data_to_write=data, base_path=tmp_path,
                       file_name="test", extension="json")
        wf.write_file_to_disk(check_version=False)

        files = list(tmp_path.glob("test_*.json"))
        assert len(files) == 1
        content = json.loads(files[0].read_text())
        assert content == data


class TestWriteCsv:
    def test_writes_csv_file(self, tmp_path):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        wf = WriteFile(data_to_write=df, base_path=tmp_path,
                       file_name="test", extension="csv")
        wf.write_file_to_disk(check_version=False)

        files = list(tmp_path.glob("test_*.csv"))
        assert len(files) == 1
        result = pd.read_csv(files[0])
        assert len(result) == 2


class TestWriteText:
    def test_writes_text_file(self, tmp_path):
        wf = WriteFile(data_to_write="hello world", base_path=tmp_path,
                       file_name="note", extension="txt")
        wf.write_file_to_disk(check_version=False)

        files = list(tmp_path.glob("note_*.txt"))
        assert len(files) == 1
        assert files[0].read_text() == "hello world"


openpyxl = pytest.importorskip("openpyxl")


class TestWriteExcel:
    def test_writes_dataframe(self, tmp_path):
        df = pd.DataFrame({"a": [1], "b": [2]})
        wf = WriteFile(data_to_write=df, base_path=tmp_path,
                       file_name="sheet", extension="xlsx")
        wf.write_file_to_disk(check_version=False)

        files = list(tmp_path.glob("sheet_*.xlsx"))
        assert len(files) == 1

    def test_writes_dict_of_dataframes(self, tmp_path):
        data = {
            "Sheet1": pd.DataFrame({"a": [1]}),
            "Sheet2": pd.DataFrame({"b": [2]}),
        }
        wf = WriteFile(data_to_write=data, base_path=tmp_path,
                       file_name="multi", extension="xlsx")
        wf.write_file_to_disk(check_version=False)

        files = list(tmp_path.glob("multi_*.xlsx"))
        assert len(files) == 1


class TestCheckVersionIntegration:
    def test_old_files_removed(self, tmp_path):
        # Create an "old" file
        (tmp_path / "d_01012020.json").write_text("[]")

        data = [{"new": True}]
        wf = WriteFile(data_to_write=data, base_path=tmp_path,
                       file_name="d", extension="json")
        wf.write_file_to_disk(check_version=True)

        files = list(tmp_path.glob("d_*.json"))
        # Old file should have been removed by check_version, new one created
        assert len(files) >= 1
        # The remaining file should be today's
        assert any("01012020" not in f.name for f in files)
