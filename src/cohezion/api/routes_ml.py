"""Machine learning endpoints - FLUME VAE and RL policy."""

from cohezion.api import routes_flume, routes_rl


# Re-export routers
flume_router = routes_flume.router
rl_router = routes_rl.router

__all__ = ["flume_router", "rl_router"]
