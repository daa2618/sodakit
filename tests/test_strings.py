from __future__ import annotations

import pytest

from sodakit.utils.strings import get_matching_scores_for_string, _get_unique_elements


class TestGetMatchingScores:
    def test_exact_match_returns_1(self):
        scores = get_matching_scores_for_string(["hello"], "hello")
        assert scores == [1.0]

    def test_case_insensitive(self):
        scores = get_matching_scores_for_string(["Hello"], "hello")
        assert scores[0] == 1.0

    def test_no_match_returns_low_score(self):
        scores = get_matching_scores_for_string(["zzzzz"], "aaaaa")
        assert scores[0] < 0.5

    def test_empty_strings_filtered(self):
        scores = get_matching_scores_for_string(["", "hello", ""], "hello")
        assert len(scores) == 1
        assert scores[0] == 1.0

    def test_empty_list(self):
        assert get_matching_scores_for_string([], "hello") == []

    def test_partial_match(self):
        scores = get_matching_scores_for_string(["housing data"], "housing")
        assert scores[0] > 0.5


class TestGetUniqueElements:
    def test_flat_list(self):
        result = _get_unique_elements([3, 1, 2, 1])
        assert result == [1, 2, 3]

    def test_nested_list(self):
        result = _get_unique_elements([[1, 2], [2, 3]])
        assert result == [1, 2, 3]

    def test_deduplication(self):
        result = _get_unique_elements(["a", "b", "a"])
        assert result == ["a", "b"]

    def test_empty_list_raises(self):
        with pytest.raises(ValueError):
            _get_unique_elements([])

    def test_filters_falsy_values(self):
        result = _get_unique_elements(["a", "", "b", None])
        assert result == ["a", "b"]

    def test_sorted_output(self):
        result = _get_unique_elements(["c", "a", "b"])
        assert result == ["a", "b", "c"]
