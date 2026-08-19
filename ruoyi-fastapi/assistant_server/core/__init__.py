"""Application-wide configuration, lifecycle, middleware, and concurrency primitives."""

# Keep this package initializer deliberately light. Importing configuration must
# not construct or import network-facing services as a side effect.
from .config import Settings, load_local_env

__all__ = ["Settings", "load_local_env"]
