from __future__ import annotations

import json

import pytest
import responses as responses_mock

from sodakit.utils.response import Response, GET_RESPONSE, POST_RESPONSE, MethodError


class TestResponseInit:
    def test_stores_attributes(self):
        r = Response("https://example.com", method="POST")
        assert r.url == "https://example.com"
        assert r.method == "POST"


class TestMethodValidation:
    def test_valid_get(self):
        r = Response("https://example.com", method="GET")
        assert r._method == "GET"

    def test_valid_post(self):
        r = Response("https://example.com", method="POST")
        assert r._method == "POST"

    def test_invalid_method_raises(self):
        r = Response("https://example.com", method="DELETE")
        with pytest.raises(MethodError):
            _ = r._method


class TestResponse:
    @responses_mock.activate
    def test_get_request(self):
        responses_mock.add(responses_mock.GET, "https://example.com/data",
                          json={"key": "value"}, status=200)
        r = Response("https://example.com/data")
        resp = r.response
        assert resp.status_code == 200

    @responses_mock.activate
    def test_response_cached(self):
        responses_mock.add(responses_mock.GET, "https://example.com/data",
                          json={"key": "value"}, status=200)
        r = Response("https://example.com/data")
        resp1 = r.response
        resp2 = r.response
        assert resp1 is resp2

    @responses_mock.activate
    def test_post_request(self):
        responses_mock.add(responses_mock.POST, "https://example.com/data",
                          json={"ok": True}, status=200)
        r = Response("https://example.com/data", method="POST")
        resp = r.response
        assert resp.status_code == 200


class TestAssertResponse:
    @responses_mock.activate
    def test_success(self):
        responses_mock.add(responses_mock.GET, "https://example.com/ok",
                          json={}, status=200)
        r = Response("https://example.com/ok")
        result = r.assert_response()
        assert result.status_code == 200

    @responses_mock.activate
    def test_non_200_raises(self):
        responses_mock.add(responses_mock.GET, "https://example.com/fail",
                          json={}, status=404)
        r = Response("https://example.com/fail")
        with pytest.raises(Exception):
            r.assert_response()


class TestGetJsonFromResponse:
    @responses_mock.activate
    def test_valid_json(self):
        payload = {"items": [1, 2, 3]}
        responses_mock.add(responses_mock.GET, "https://example.com/json",
                          json=payload, status=200)
        r = Response("https://example.com/json")
        result = r.get_json_from_response()
        assert result == payload

    @responses_mock.activate
    def test_invalid_json_returns_none(self):
        responses_mock.add(responses_mock.GET, "https://example.com/bad",
                          body="not json", status=200)
        r = Response("https://example.com/bad")
        result = r.get_json_from_response()
        assert result is None


class TestGetBaseUrl:
    def test_extracts_base(self):
        r = Response("https://data.example.com/api/v1/resource")
        assert r.get_base_url() == "https://data.example.com"


class TestConvenienceClasses:
    def test_get_response_method(self):
        r = GET_RESPONSE("https://example.com")
        assert r.method == "GET"

    def test_post_response_method(self):
        r = POST_RESPONSE("https://example.com")
        assert r.method == "POST"
