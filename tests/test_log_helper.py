from __future__ import annotations

import logging
import unittest.mock

from sodakit.utils.log_helper import BasicLogger, get_logger


class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)

    def test_respects_level(self):
        logger = get_logger("level_test", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_no_duplicate_handlers(self):
        name = "dup_handler_test"
        get_logger(name)
        get_logger(name)
        logger = logging.getLogger(name)
        assert len(logger.handlers) == 1

    def test_propagate_disabled(self):
        logger = get_logger("prop_test")
        assert logger.propagate is False


class TestBasicLogger:
    def test_all_methods_exist(self):
        bl = BasicLogger(logger_name="method_check")
        for method in ("debug", "info", "warning", "error", "critical", "exception"):
            assert callable(getattr(bl, method))

    def test_log_level_respected(self):
        bl = BasicLogger(logger_name="level_check", log_level=logging.DEBUG)
        assert bl.logger.level == logging.DEBUG

    def test_default_level_is_info(self):
        bl = BasicLogger(logger_name="default_level")
        assert bl.logger.level == logging.INFO

    def test_info_delegates(self):
        bl = BasicLogger(logger_name="delegate_test")
        with unittest.mock.patch.object(bl.logger, "info") as mock_info:
            bl.info("hello from test")
        mock_info.assert_called_once_with("hello from test")

    def test_exception_delegates(self):
        bl = BasicLogger(logger_name="exc_test")
        with unittest.mock.patch.object(bl.logger, "exception") as mock_exc:
            bl.exception("exception message")
        mock_exc.assert_called_once_with("exception message")
