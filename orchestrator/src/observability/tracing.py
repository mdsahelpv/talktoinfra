"""OpenTelemetry tracing setup for observability."""

import logging
from functools import wraps

logger = logging.getLogger(__name__)

_tracer = None


def setup_tracing(service_name: str, exporter_endpoint: str) -> None:
    global _tracer
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        logger.info("OpenTelemetry tracing configured for %s -> %s", service_name, exporter_endpoint)
    except ImportError:
        logger.warning("OpenTelemetry packages not installed; tracing disabled")
    except Exception as exc:
        logger.warning("Failed to initialize OpenTelemetry: %s", exc)


def trace_tool_call(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if _tracer is None:
            return await func(*args, **kwargs)
        with _tracer.start_as_current_span(func.__name__):
            return await func(*args, **kwargs)
    return wrapper


def get_tracer():
    return _tracer
