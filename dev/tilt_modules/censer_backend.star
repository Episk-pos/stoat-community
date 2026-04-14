# =============================================================================
# Censer Backend Tilt Module
# =============================================================================
# Reusable Tilt extension for starting the Censer backend stack from
# individual product repos (stoat-flutter, stoat-backend, stoat-frontend).
#
# Usage (from another repo's Tiltfile):
#   COMMUNITY_PATH = os.path.join(os.getcwd(), '..', 'stoat-community')
#   load_dynamic(COMMUNITY_PATH + '/dev/tilt_modules/censer_backend.star',
#                'censer_backend_compose')
#   censer_backend_compose(minimal=True, seed=True)
#
# This module provides:
#   - censer_backend_compose(): Start backend via Docker Compose
#   - censer_backend_k8s(): Start backend via Kind/Kubernetes (future)
#   - CENSER_CORE: Minimal service list for Flutter/web frontends
#   - CENSER_FULL: All censer services + optional components
# =============================================================================

# Service definitions
CENSER_CORE = [
    "redis",
    "mongodb",
    "rabbitmq",
    "minio",
    "minio-init",
    "delta",      # REST API :14702
    "bonfire",    # WebSocket :14703
    "autumn",     # File server :14704
    "january",    # Proxy :14705
]

CENSER_FULL = CENSER_CORE + [
    "maildev",    # Email testing UI
]

def censer_backend_compose(services=None, seed=True, minimal=False, ci_mode=False):
    """Start Censer backend via Docker Compose.

    Args:
        services: List of service names to start (default: CENSER_CORE)
        seed: Run seed container to populate test data (default: True)
        minimal: Use minimal service set (default: False)
        ci_mode: Use docker-compose.ci.yml overlay for resource limits (default: False)

    Example:
        censer_backend_compose(minimal=True, seed=True)
    """

    # Determine which services to start
    if services is None:
        services = CENSER_CORE if minimal else CENSER_FULL

    # Path to stoat-community dev directory (where this module lives)
    module_dir = os.path.dirname(__file__)
    community_dev_dir = os.path.dirname(module_dir)  # Go up one level from tilt_modules/

    # Build docker-compose command
    compose_files = [
        os.path.join(community_dev_dir, "docker-compose.yml"),
    ]

    if ci_mode:
        compose_files.append(os.path.join(community_dev_dir, "docker-compose.ci.yml"))

    compose_args = []
    for f in compose_files:
        compose_args.extend(["-f", f])

    # Create a docker-compose resource
    # Note: Tilt's docker_compose() expects paths relative to Tiltfile location,
    # but we're being called from another repo. Use absolute paths.
    docker_compose(
        " ".join([f for f in compose_files]),
        project_name="censer-backend",
    )

    # Register each service as a Tilt resource
    for service in services:
        if service == "minio-init":
            # Init job, not a long-running service
            dc_resource(service, labels=["infra"])
        elif service in ["redis", "mongodb", "rabbitmq", "minio", "maildev"]:
            dc_resource(service, labels=["infra"])
        elif service in ["delta", "bonfire", "autumn", "january"]:
            dc_resource(service, labels=["backend"])
        else:
            dc_resource(service)

    # Seed data (optional)
    if seed:
        local_resource(
            "seed",
            cmd="cd {} && docker compose --profile seed up seed".format(community_dev_dir),
            deps=[os.path.join(community_dev_dir, "seed")],
            auto_init=False,  # Manual trigger
            trigger_mode=TRIGGER_MODE_MANUAL,
            labels=["seed"],
        )

def censer_backend_k8s(services=None, seed=True, minimal=False):
    """Start Censer backend via Kubernetes/Kind.

    Args:
        services: List of service names to start (default: CENSER_CORE)
        seed: Run seed job to populate test data (default: True)
        minimal: Use minimal service set (default: False)

    Note: This is a placeholder for future K8s support.
    For now, use censer_backend_compose() instead.
    """
    fail("censer_backend_k8s() not yet implemented - use censer_backend_compose() for now")

# Export symbols
__all__ = [
    "censer_backend_compose",
    "censer_backend_k8s",
    "CENSER_CORE",
    "CENSER_FULL",
]
