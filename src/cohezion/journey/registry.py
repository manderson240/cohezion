from .voyages.gateway import run_gateway_voyage
from .voyages.hiho_attractor import run_hiho_voyage


def get_journey_registry():
    """
    Returns a populated JourneyRegistry with all available voyages.
    """
    from .narrator import JourneyRegistry

    registry = JourneyRegistry()

    registry.register_voyage(
        "Gateway to Cohezion",
        "Introduction to the platform and core conceptual pillars.",
        run_gateway_voyage,
    )

    registry.register_voyage(
        "The HIHO Attractor",
        "Explore the fundamental attractor of reality precipitation.",
        run_hiho_voyage,
    )

    return registry
