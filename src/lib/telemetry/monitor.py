from prometheus_client import Counter, Histogram, Gauge
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from typing import Callable, Any

class Telemetry:
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.logger = structlog.get_logger()
        self.tracer = trace.get_tracer(__name__)

        # Metrics
        self.tool_calls = Counter(
            'mcp_tool_calls_total',
            'Total number of MCP tool calls',
            ['server_name', 'tool_name', 'status']
        )

        self.tool_duration = Histogram(
            'mcp_tool_duration_seconds',
            'Duration of MCP tool calls',
            ['server_name', 'tool_name']
        )

        # A2A specific metrics
        self.a2a_messages = Counter(
            'a2a_messages_total',
            'Total number of A2A messages',
            ['server_name', 'direction', 'message_type', 'status']
        )

        self.a2a_message_duration = Histogram(
            'a2a_message_duration_seconds',
            'Duration of A2A message processing',
            ['server_name', 'direction', 'message_type']
        )

    def track_tool_call(self, tool_name: str):
        """Decorator to track tool calls"""
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs) -> Any:
                with self.tracer.start_as_current_span(f"tool:{tool_name}") as span:
                    span.set_attribute("tool.name", tool_name)
                    span.set_attribute("server.name", self.server_name)

                    with self.tool_duration.labels(
                        server_name=self.server_name,
                        tool_name=tool_name
                    ).time():
                        try:
                            result = await func(*args, **kwargs)
                            self.tool_calls.labels(
                                server_name=self.server_name,
                                tool_name=tool_name,
                                status="success"
                            ).inc()
                            span.set_status(trace.Status(trace.StatusCode.OK))
                            return result
                        except Exception as e:
                            self.tool_calls.labels(
                                server_name=self.server_name,
                                tool_name=tool_name,
                                status="error"
                            ).inc()
                            span.record_exception(e)
                            span.set_status(
                                trace.Status(trace.StatusCode.ERROR, str(e))
                            )
                            raise
            return wrapper
        return decorator

    def track_a2a_message(self, direction: str, message_type: str):
        """Decorator to track A2A messages"""
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs) -> Any:
                with self.tracer.start_as_current_span(f"a2a:{direction}:{message_type}") as span:
                    span.set_attribute("a2a.direction", direction)
                    span.set_attribute("a2a.message_type", message_type)
                    span.set_attribute("server.name", self.server_name)

                    with self.a2a_message_duration.labels(
                        server_name=self.server_name,
                        direction=direction,
                        message_type=message_type
                    ).time():
                        try:
                            result = await func(*args, **kwargs)
                            self.a2a_messages.labels(
                                server_name=self.server_name,
                                direction=direction,
                                message_type=message_type,
                                status="success"
                            ).inc()
                            span.set_status(trace.Status(trace.StatusCode.OK))
                            return result
                        except Exception as e:
                            self.a2a_messages.labels(
                                server_name=self.server_name,
                                direction=direction,
                                message_type=message_type,
                                status="error"
                            ).inc()
                            span.record_exception(e)
                            span.set_status(
                                trace.Status(trace.StatusCode.ERROR, str(e))
                            )
                            raise
            return wrapper
        return decorator
