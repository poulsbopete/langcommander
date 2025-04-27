import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import logging

# Module-level guard to ensure tracer provider is only set up once
_tracer_provider_initialized = False

def _configure_logging():
    """Configure Python logging for OpenTelemetry debug output."""
    logging.basicConfig(
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        level=logging.DEBUG,
    )
    for name in (
        "opentelemetry",
        "opentelemetry.sdk.trace",
        "opentelemetry.sdk.trace.export",
        "opentelemetry.exporter.otlp",
    ):
        logging.getLogger(name).setLevel(logging.DEBUG)

def _setup_tracer_provider():
    global _tracer_provider_initialized
    if _tracer_provider_initialized:
        return
    _tracer_provider_initialized = True
    # Read OTLP exporter endpoint and headers from environment
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    # Ensure endpoint URI includes scheme (default to https)
    if endpoint and not endpoint.lower().startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"
    headers_env = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
    service_name = os.getenv("OTEL_SERVICE_NAME", "langcommander")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # OTLP gRPC exporter
    if endpoint:
        # Use entire headers_env as the Authorization token for gRPC metadata
        token = headers_env.strip().strip('"').strip("'")
        header_items = []
        if token:
            header_items = [("authorization", token)]
        # Debug: print header_items to stderr so we can confirm exactly what's sent
        import sys
        print(f"OTLP metadata headers: {header_items}", file=sys.stderr)
        # Create OTLP gRPC exporter with explicit metadata
        exporter = OTLPSpanExporter(endpoint=endpoint, headers=header_items)
        span_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(span_processor)

    # Optional ConsoleSpanExporter (prints spans to stdout) if requested
    if os.getenv("OTEL_CONSOLE_EXPORTER", "").lower() in ("1", "true", "yes"):
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(console_exporter))
    # Note: tracer provider is initialized here; instrumentation functions will use it

def instrument_app(app):
    """Instrument Flask app for OpenTelemetry tracing."""
    # Enable debug logging if OTEL_DEBUG is truthy
    if os.getenv("OTEL_DEBUG", "").lower() in ("1", "true", "yes"):
        _configure_logging()
    # Initialize tracer provider and exporters
    _setup_tracer_provider()
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
    except ImportError:
        pass

def instrument_es():
    """Instrument Elasticsearch client for OpenTelemetry tracing."""
    # Enable debug logging if OTEL_DEBUG is truthy
    if os.getenv("OTEL_DEBUG", "").lower() in ("1", "true", "yes"):
        _configure_logging()
    # Initialize tracer provider and exporters
    _setup_tracer_provider()
    try:
        from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor
        ElasticsearchInstrumentor().instrument()
    except ImportError:
        pass