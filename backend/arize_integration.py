import os
import sys
import socket
from opentelemetry import trace

# Create a global tracer variable
tracer = None

def is_port_in_use(port: int) -> bool:
    """Checks if a local TCP port is already active."""
    # 1. Try connecting to the port on localhost (very reliable check for active listeners)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            s.connect(("127.0.0.1", port))
            return True
    except OSError:
        pass

    # 2. Try binding to wildcard IPv4
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", port))
    except OSError:
        return True

    # 3. Try binding to wildcard IPv6
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.bind(("::", port))
    except OSError:
        return True

    return False

# Force stdout/stderr to UTF-8 on Windows to avoid UnicodeEncodeErrors
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import phoenix as px
    from phoenix.otel import register
except Exception as e:
    print(f"--> Warning: Could not import Arize Phoenix: {e}")
    px = None
    register = None

def init_arize():
    """Initializes Arize Phoenix Observability.
    Optimized for both local development and Google Cloud Run.
    """
    global tracer
    if tracer is not None:
        return tracer
        
    print("Initializing Arize Phoenix Observability...")
    
    if px is None or register is None:
        print("--> Arize Phoenix telemetry packages unavailable in this environment. Using fallback tracer.")
        tracer = trace.get_tracer("carbon-agent")
        return tracer

    # Check if running on Google Cloud Run (or other containerized envs)
    is_cloud_run = os.getenv("K_SERVICE") is not None
    
    port = int(os.getenv("PHOENIX_PORT", 6006))
    grpc_port = int(os.getenv("PHOENIX_GRPC_PORT", 4317))
    
    # Run Phoenix UI server locally ONLY when running locally (not in Cloud Run)
    if is_cloud_run:
        print("--> Detected Google Cloud Run environment. Skipping local Phoenix UI startup.")
    else:
        if is_port_in_use(port) or is_port_in_use(grpc_port):
            print(f"--> Phoenix port {port} or gRPC port {grpc_port} is already in use. Assuming Phoenix is already running.")
        else:
            try:
                session = px.launch_app(port=port)
                print(f"--> Arize Phoenix UI is available at: {session.url}")
            except Exception as e:
                print(f"--> Note: Phoenix app might already be running: {e}")
    
    # Configure the exporter endpoint
    # In Cloud Run, traces should be sent to a hosted/central Phoenix collector URL configured in the env,
    # otherwise we default to the local UI instance endpoint.
    collector_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    if not collector_endpoint:
        if is_cloud_run:
            print("--> Warning: PHOENIX_COLLECTOR_ENDPOINT is not set in Cloud Run. Traces will not be exported.")
            tracer = trace.get_tracer("carbon-agent")
            return tracer
        else:
            collector_endpoint = f"http://127.0.0.1:{port}/v1/traces"
    
    try:
        tracer_provider = register(
            project_name="carbon-account-agent",
            endpoint=collector_endpoint
        )
        print(f"--> Registered OpenTelemetry Tracer Provider pointing to {collector_endpoint}")
    except Exception as e:
        print(f"--> Failed to register OTel tracer provider pointing to {collector_endpoint}: {e}")
        tracer = trace.get_tracer("carbon-agent")
        return tracer

    # Auto-instrument Google GenAI SDK (Gemini calls)
    try:
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        print("--> Auto-instrumented Google GenAI with OpenInference")
    except Exception as e:
        print(f"--> Could not auto-instrument Google GenAI: {e}")

    tracer = trace.get_tracer("carbon-agent-tracer")
    return tracer

def get_tracer():
    """Returns the active tracer, initializing it if necessary."""
    global tracer
    if tracer is None:
        return init_arize()
    return tracer
