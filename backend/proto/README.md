# gRPC Service Definitions

This directory contains Protocol Buffer (protobuf) definitions for gRPC services used in the Shadower Analytics platform.

## Files

- `analytics.proto`: Analytics service definition for high-performance inter-service communication

## Generating Python Code

To generate Python code from the proto files, run:

```bash
cd backend
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src/grpc_generated \
    --grpc_python_out=./src/grpc_generated \
    ./proto/analytics.proto
```

This will generate:
- `analytics_pb2.py`: Message class definitions
- `analytics_pb2_grpc.py`: Service stub and server definitions

## Usage

### Server Implementation

```python
from src.grpc_generated import analytics_pb2_grpc
from src.services.grpc_analytics_service import AnalyticsServiceImpl

server = grpc.aio.server()
analytics_pb2_grpc.add_AnalyticsServiceServicer_to_server(
    AnalyticsServiceImpl(), server
)
server.add_insecure_port('[::]:50051')
await server.start()
```

### Client Usage

```python
from src.grpc_generated import analytics_pb2, analytics_pb2_grpc
import grpc

async with grpc.aio.insecure_channel('localhost:50051') as channel:
    stub = analytics_pb2_grpc.AnalyticsServiceStub(channel)

    request = analytics_pb2.MetricsRequest(
        workspace_id="ws_123",
        metric_type="agent_executions",
        start_time=1234567890,
        end_time=1234567999
    )

    response = await stub.GetMetrics(request)
    print(f"Found {len(response.metrics)} metrics")
```

## Service Methods

### GetMetrics
- **Request**: MetricsRequest
- **Response**: MetricsResponse
- **Description**: Retrieve metrics for a workspace with filtering and pagination

### StreamMetrics
- **Request**: StreamRequest
- **Response**: Stream of MetricUpdate
- **Description**: Subscribe to real-time metric updates

### CalculateAggregates
- **Request**: AggregateRequest
- **Response**: AggregateResponse
- **Description**: Calculate aggregations (sum, avg, min, max) over metrics

### GetWorkspaceSummary
- **Request**: WorkspaceSummaryRequest
- **Response**: WorkspaceSummaryResponse
- **Description**: Get comprehensive workspace analytics summary

### GetAgentPerformance
- **Request**: AgentPerformanceRequest
- **Response**: AgentPerformanceResponse
- **Description**: Get detailed agent performance metrics

## Best Practices

1. **Versioning**: When making breaking changes, create a new proto file (e.g., `analytics_v2.proto`)
2. **Backward Compatibility**: Use field numbers consistently, don't reuse deleted field numbers
3. **Performance**: Use streaming for large datasets or real-time updates
4. **Error Handling**: Use gRPC status codes for error responses
5. **Authentication**: Implement metadata-based authentication for production

## Performance Considerations

- gRPC uses HTTP/2 for multiplexing multiple requests over a single connection
- Protocol Buffers are more efficient than JSON for serialization
- Streaming reduces overhead for real-time data
- Connection pooling is handled automatically by gRPC

## Security

For production deployments:
1. Use TLS for encryption
2. Implement token-based authentication via metadata
3. Apply rate limiting at the service level
4. Use mTLS for service-to-service communication

## Monitoring

gRPC services can be monitored using:
- OpenTelemetry for distributed tracing
- Prometheus for metrics collection
- Custom interceptors for logging

## References

- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [Protocol Buffers Guide](https://developers.google.com/protocol-buffers)
- [gRPC Best Practices](https://grpc.io/docs/guides/performance/)
