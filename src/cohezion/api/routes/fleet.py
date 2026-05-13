"""
Fleet API - Routes for monitoring and managing the service fleet.
"""

from fastapi import APIRouter, HTTPException

from cohezion.governance.fleet_monitor import ServiceStatus, get_fleet_monitor


router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.get("/status", response_model=list[ServiceStatus])
async def get_fleet_status():
    """Get the current status of all registered services."""
    monitor = get_fleet_monitor()
    return list(monitor.services.values())


@router.post("/register")
async def register_service(service: ServiceStatus):
    """Register a new service with the fleet monitor."""
    monitor = get_fleet_monitor()
    await monitor.register_service(service)
    return {"message": f"Service '{service.name}' registered successfully."}


@router.post("/check/{name}")
async def trigger_health_check(name: str):
    """Manually trigger a health check for a specific service."""
    monitor = get_fleet_monitor()
    if name not in monitor.services:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found.")

    await monitor.check_health(name)
    return monitor.services[name]


@router.get("/events")
async def get_fleet_events(limit: int = 20):
    """Retrieve the latest fleet lifecycle and health events."""
    monitor = get_fleet_monitor()
    try:
        events = await monitor.db.query(
            "SELECT * FROM fleet_events ORDER BY timestamp DESC LIMIT $limit", {"limit": limit}
        )
        return events if events else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
