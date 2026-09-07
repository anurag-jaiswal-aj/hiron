"""Tests for Phase 18 OTLP Metrics integration."""

import pytest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hiron.core.middleware import RequestTracingMiddleware
from hiron.core.metrics import (
    api_requests_counter,
    api_request_duration_histogram,
)

# Mock application to test middleware
app = FastAPI()
app.add_middleware(RequestTracingMiddleware)

@app.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    return {"id": candidate_id}

@app.get("/error_route")
async def error_route():
    raise ValueError("Business Logic Error")

client = TestClient(app)


def test_route_template_validation():
    """Verify that dynamic IDs are normalized to the route template in metrics."""
    with patch.object(api_request_duration_histogram, "record") as mock_record, \
         patch.object(api_requests_counter, "add") as mock_add:
        
        response = client.get("/candidates/12345-uuid")
        assert response.status_code == 200
        
        args, kwargs = mock_record.call_args
        labels = args[1] if len(args) > 1 else kwargs.get("attributes", {})
        
        assert labels["path"] == "/candidates/{candidate_id}"
        assert labels["method"] == "GET"
        assert labels["status_code"] == "200"

        add_args, add_kwargs = mock_add.call_args
        add_labels = add_args[1] if len(add_args) > 1 else add_kwargs.get("attributes", {})
        
        assert add_labels["path"] == "/candidates/{candidate_id}"
        assert add_labels["method"] == "GET"
        assert add_labels["status_code"] == "200"


def test_exporter_failure_is_harmless():
    """Verify that metric recording failures do not block the API or raise exceptions."""
    with patch.object(api_requests_counter, "add", side_effect=Exception("Mock OTLP Exception")), \
         patch("hiron.core.middleware.structlog.get_logger") as mock_logger:
        
        response = client.get("/candidates/harmless-test")
        
        assert response.status_code == 200
        assert response.json() == {"id": "harmless-test"}
        
        mock_logger_instance = mock_logger.return_value
        mock_logger_instance.warning.assert_any_call(
            "metric_recording_failed", error="Mock OTLP Exception"
        )


def test_exporter_lifecycle_disabled(caplog):
    """Verify exporter is not initialized when endpoint is absent."""
    import importlib
    import logging
    import os
    import hiron.core.metrics
    
    caplog.set_level(logging.INFO)
    
    with patch.dict(os.environ, clear=True), \
         patch("hiron.core.metrics.OTLPMetricExporter") as mock_exporter, \
         patch("hiron.core.metrics.PeriodicExportingMetricReader") as mock_reader:
        
        importlib.reload(hiron.core.metrics)
        
        mock_exporter.assert_not_called()
        mock_reader.assert_not_called()
        
        assert "OTLP metrics export disabled (OTEL_EXPORTER_OTLP_METRICS_ENDPOINT not set)." in caplog.text
        
        try:
            hiron.core.metrics.api_requests_counter.add(1, {"method": "GET"})
        except Exception:
            pytest.fail("Metric calls raised exception when disabled")
