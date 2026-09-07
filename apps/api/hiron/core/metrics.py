"""OpenTelemetry metrics initialization for the FastAPI application."""

import logging
import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

logger = logging.getLogger(__name__)

try:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    if not endpoint:
        logger.info("OTLP metrics export disabled (OTEL_EXPORTER_OTLP_METRICS_ENDPOINT not set).")
    else:
        # Initialize the OTLP exporter. This inherently reads standard OTEL environment variables
        # such as OTEL_EXPORTER_OTLP_METRICS_ENDPOINT and OTEL_EXPORTER_OTLP_HEADERS.
        exporter = OTLPMetricExporter()
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=30000,
            export_timeout_millis=2000,
        )
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)
except Exception as e:
    logger.warning("Failed to initialize OpenTelemetry metrics exporter: %s", e)
    # OpenTelemetry automatically provides a NoOp provider as a fallback if initialization fails.

meter = metrics.get_meter("hiron.api")

api_requests_counter = meter.create_counter(
    "hiron.api.requests",
    description="Every completed API request",
)

api_request_duration_histogram = meter.create_histogram(
    "hiron.api.request.duration",
    description="Duration of API requests in milliseconds",
)

ai_requests_counter = meter.create_counter(
    "hiron.ai.requests",
    description="Every AI attempt, successful OR failed",
)

ai_errors_counter = meter.create_counter(
    "hiron.ai.errors",
    description="Only failed AI attempts",
)
