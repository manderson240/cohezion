"""Datamesh federation layer - coordinate across domain boundaries.

Charter: Transparent routing, no single point of failure, HIHO consistency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cohezion.datamesh.ingestion import DatameshIngestion
from cohezion.datamesh.query import DatameshQuery


logger = logging.getLogger(__name__)


@dataclass
class DomainEndpoint:
    """Endpoint configuration for a data domain."""

    name: str
    ingestion: DatameshIngestion | None = None
    query: DatameshQuery | None = None
    health_check: str | None = None  # URL or callable
    priority: int = 1  # Lower = higher priority


class FederationLayer:
    """Coordinates access to all data domains.

    Responsibilities:
    1. Domain registration
    2. Query routing
    3. Health monitoring
    4. Failover handling
    """

    def __init__(self):
        self._domains: dict[str, DomainEndpoint] = {}
        self._unhealthy: set[str] = set()

    def register_domain(self, endpoint: DomainEndpoint) -> None:
        """Register a data domain."""
        self._domains[endpoint.name] = endpoint
        logger.info(f"Registered domain: {endpoint.name}")

    def get_ingestion(self, domain: str) -> DatameshIngestion | None:
        """Get ingestion for domain (with failover)."""
        if domain in self._unhealthy:
            # Try fallback
            for name, ep in sorted(self._domains.items(), key=lambda x: x[1].priority):
                if name not in self._unhealthy and ep.ingestion:
                    logger.warning(f"Failing over {domain} to {name}")
                    return ep.ingestion
            return None

        ep = self._domains.get(domain)
        return ep.ingestion if ep else None

    def get_query(self, domain: str) -> DatameshQuery | None:
        """Get query interface for domain."""
        ep = self._domains.get(domain)
        return ep.query if ep else None

    async def health_check(self) -> dict[str, bool]:
        """Check health of all domains."""
        results = {}
        for name, ep in self._domains.items():
            try:
                if ep.health_check:
                    # Try to use health check
                    if callable(ep.health_check):
                        healthy = await ep.health_check()
                    else:
                        # Assume healthy if configured
                        healthy = True
                else:
                    # No health check configured, assume healthy
                    healthy = True

                results[name] = healthy
                if healthy and name in self._unhealthy:
                    self._unhealthy.remove(name)
                    logger.info(f"Domain {name} recovered")
                elif not healthy:
                    self._unhealthy.add(name)
                    logger.error(f"Domain {name} unhealthy")

            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = False
                self._unhealthy.add(name)

        return results

    def list_domains(self) -> list[str]:
        """List all registered domains."""
        return list(self._domains.keys())

    def endpoint(self, domain: str) -> DomainEndpoint | None:
        """Return the registered endpoint for a domain (read access for observability)."""
        return self._domains.get(domain)

    def list_healthy(self) -> list[str]:
        """List healthy domains."""
        return [name for name in self._domains if name not in self._unhealthy]
