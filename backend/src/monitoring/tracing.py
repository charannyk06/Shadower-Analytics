"""OpenTelemetry distributed tracing configuration."""

import os
import logging
from typing import Optional
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.trace import Status, StatusCode, Tracer
from functools import wraps

logger = logging.getLogger(__name__)


def setup_tracing(app, enable_console_export: bool = False) -> Optional[Tracer]:
    """Configure OpenTelemetry distributed tracing.

    Args:
        app: FastAPI application instance
        enable_console_export: Whether to export traces to console (for debugging)

    Returns:
        Tracer instance if successful, None otherwise
    """
    try:
        # Create resource with service information
        resource = Resource.create({
            "service.name": "analytics-backend",
            "service.version": os.getenv("APP_VERSION", "unknown"),
            "deployment.environment": os.getenv("APP_ENV", "development"),
            "service.namespace": "shadower",
        })

        # Setup tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter (for Jaeger/Tempo/etc.)
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=os.getenv("OTEL_EXPORTER_INSECURE", "true").lower() == "true"
            )
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)
            logger.info(f"OTLP trace exporter configured: {otlp_endpoint}")
        else:
            logger.warning("OTEL_EXPORTER_OTLP_ENDPOINT not set, OTLP export disabled")

        # Optionally add console exporter for debugging
        if enable_console_export or os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true":
            console_exporter = ConsoleSpanExporter()
            console_processor = BatchSpanProcessor(console_exporter)
            provider.add_span_processor(console_processor)
            logger.info("Console trace exporter enabled")

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented for tracing")

        # Instrument SQLAlchemy
        try:
            SQLAlchemyInstrumentor().instrument()
            logger.info("SQLAlchemy instrumented for tracing")
        except Exception as e:
            logger.warning(f"Failed to instrument SQLAlchemy: {e}")

        # Instrument Redis
        try:
            RedisInstrumentor().instrument()
            logger.info("Redis instrumented for tracing")
        except Exception as e:
            logger.warning(f"Failed to instrument Redis: {e}")

        # Instrument HTTP clients
        try:
            RequestsInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()
            logger.info("HTTP clients instrumented for tracing")
        except Exception as e:
            logger.warning(f"Failed to instrument HTTP clients: {e}")

        # Get tracer
        tracer = trace.get_tracer(__name__)

        logger.info("OpenTelemetry tracing configured successfully")
        return tracer

    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}", exc_info=True)
        return None


def trace_operation(name: str, attributes: Optional[dict] = None):
    """Decorator to trace function execution with OpenTelemetry.

    Args:
        name: Span name
        attributes: Optional span attributes

    Example:
        @trace_operation("calculate_analytics")
        async def calculate_analytics(workspace_id: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)

            with tracer.start_as_current_span(name) as span:
                try:
                    # Add default attributes
                    span.set_attribute("function", func.__name__)
                    span.set_attribute("module", func.__module__)

                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    # Add function arguments as attributes (if simple types)
                    for i, arg in enumerate(args):
                        if isinstance(arg, (str, int, float, bool)):
                            span.set_attribute(f"arg.{i}", arg)

                    for key, value in kwargs.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"kwarg.{key}", value)

                    # Execute function
                    result = await func(*args, **kwargs)

                    # Mark as successful
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)

            with tracer.start_as_current_span(name) as span:
                try:
                    # Add default attributes
                    span.set_attribute("function", func.__name__)
                    span.set_attribute("module", func.__module__)

                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)

                    # Execute function
                    result = func(*args, **kwargs)

                    # Mark as successful
                    span.set_status(Status(StatusCode.OK))

                    return result

                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def add_span_attributes(attributes: dict) -> None:
    """Add attributes to the current span.

    Args:
        attributes: Dictionary of attributes to add

    Example:
        add_span_attributes({
            "workspace_id": workspace_id,
            "user_id": user_id
        })
    """
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            if isinstance(value, (str, int, float, bool)):
                span.set_attribute(key, value)
            else:
                span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[dict] = None) -> None:
    """Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes

    Example:
        add_span_event("cache_miss", {"key": cache_key})
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes or {})


def get_trace_context() -> dict:
    """Get current trace context (trace_id and span_id).

    Returns:
        Dictionary with trace_id and span_id

    Example:
        context = get_trace_context()
        logger.info("Processing request", extra=context)
    """
    span = trace.get_current_span()
    context = span.get_span_context()

    return {
        "trace_id": format(context.trace_id, '032x') if context.trace_id else None,
        "span_id": format(context.span_id, '016x') if context.span_id else None,
    }
