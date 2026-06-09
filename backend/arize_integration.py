import os
import sys
import socket

def is_port_in_use(port: int) -> bool:
    # Check IPv4
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
    except OSError:
        return True

    # Check IPv6
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.bind(("::1", port))
    except OSError:
        return True

    return False

# Force stdout/stderr to UTF-8 on Windows to avoid UnicodeEncodeErrors when printing emojis
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import phoenix as px
    from phoenix.otel import register
except Exception:
    px = None
    register = None
from opentelemetry import trace

# Create a global tracer variable
tracer = None

def init_arize():
    global tracer
    if tracer is not None:
        return tracer
        
    print("Initializing Arize Phoenix Observability...")
    
    if px is None or register is None:
        print("--> Phoenix telemetry unavailable on this Python environment. Using fallback tracer.")
        tracer = trace.get_tracer("carbon-agent")
        return tracer

    # Start Phoenix locally on port 6006 (or read from environment)
    port = int(os.getenv("PHOENIX_PORT", 6006))
    grpc_port = int(os.getenv("PHOENIX_GRPC_PORT", 4317))
    
    if is_port_in_use(port) or is_port_in_use(grpc_port):
        print(f"--> Phoenix port {port} or gRPC port {grpc_port} is already in use. Skipping px.launch_app to avoid port binding crash.")
    else:
        try:
            session = px.launch_app(port=port)
            print(f"--> Arize Phoenix UI is available at: {session.url}")
        except Exception as e:
            print(f"--> Note: Phoenix app might already be running: {e}")
    
    # Register the tracer provider to export OTel spans to our local Phoenix collector
    # Default local collector endpoint is http://localhost:6006/v1/traces
    collector_endpoint = f"http://127.0.0.1:{port}/v1/traces"
    
    try:
        tracer_provider = register(
            project_name="carbon-account-agent",
            endpoint=collector_endpoint
        )
        print(f"--> Registered OpenTelemetry Tracer Provider pointing to {collector_endpoint}")
    except Exception as e:
        print(f"--> Failed to register OTel tracer provider: {e}")
        tracer = trace.get_tracer("carbon-agent")
        return tracer

    # Instrument Google GenAI if available
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
        if GoogleGenAIInstrumentor().is_instrumented_by(tracer_provider):
            print("--> Google GenAI already instrumented")
        else:
            GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
            print("--> Auto-instrumented Google GenAI with OpenInference")
    except Exception as e:
        print(f"--> Could not auto-instrument Google GenAI: {e}")

    tracer = trace.get_tracer("carbon-agent-tracer")
    return tracer

def get_tracer():
    global tracer
    if tracer is None:
        return init_arize()
    return tracer
