"""Environmental Data MCP Server for EcoResilience Grounding.

Provides tools to fetch real-time environmental data from NOAA and Copernicus
(mocked for the hackathon but following real schema structures).
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime
from typing import Any

from fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("EnvironmentalData")

logger = logging.getLogger(__name__)


@mcp.tool()
async def fetch_noaa_data(station_id: str = "GHCND:USW00094728") -> str:
    """Fetch current weather/climate data from NOAA for a specific station.
    
    Args:
        station_id: NOAA Global Historical Climatology Network station ID.
    """
    # Mock NOAA GHCN Schema
    data = {
        "station": station_id,
        "date": datetime.now().isoformat(),
        "measurements": {
            "TMAX": round(random.uniform(15.0, 35.0), 1),
            "TMIN": round(random.uniform(5.0, 15.0), 1),
            "PRCP": round(random.uniform(0.0, 50.0), 1),
            "AWND": round(random.uniform(2.0, 12.0), 1),
        },
        "units": {
            "temperature": "Celsius",
            "precipitation": "mm",
            "wind_speed": "m/s"
        },
        "source": "NOAA GHCN-Daily (Mocked)"
    }
    return json.dumps(data, indent=2)


@mcp.tool()
async def fetch_copernicus_data(region: str = "Amazon_Basin") -> str:
    """Fetch Earth Observation data from Copernicus (Sentinel-2/3) for a region.
    
    Args:
        region: Geographic region name or bounding box coordinates.
    """
    # Mock Copernicus Sentinel Schema
    data = {
        "region": region,
        "product": "Sentinel-2 MSI Level-2A",
        "timestamp": datetime.now().isoformat(),
        "indices": {
            "NDVI": round(random.uniform(0.2, 0.9), 3),  # Vegetation health
            "NDWI": round(random.uniform(-0.5, 0.5), 3), # Water index
            "EVI": round(random.uniform(0.1, 0.8), 3),   # Enhanced vegetation
        },
        "land_cover_stats": {
            "forest_cover_pct": round(random.uniform(40.0, 85.0), 1),
            "urban_area_pct": round(random.uniform(1.0, 15.0), 1),
            "water_body_pct": round(random.uniform(5.0, 20.0), 1),
        },
        "source": "Copernicus Hub (Mocked)"
    }
    return json.dumps(data, indent=2)


if __name__ == "__main__":
    mcp.run()
