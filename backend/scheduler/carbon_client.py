from __future__ import annotations
import os
import logging

import httpx

logger = logging.getLogger(__name__)

# Azure region → Electricity Maps zone code
REGION_TO_ZONE = {
    "westeurope": "NL",         # Netherlands grid
    "eastus": "US-MIDA-PJM",    # US East PJM grid
}

# Historical-average gCO₂/kWh, used when the API is unreachable or unkeyed.
# Values from electricitymaps.com 2023–2024 yearly averages.
FALLBACK_CARBON_INTENSITY = {
    "westeurope": 150.0,
    "eastus": 386.0,
}

_API_BASE = "https://api.electricitymap.org/v3/carbon-intensity/latest"
_TIMEOUT_SECONDS = 3.0


def get_carbon_intensity(region: str) -> tuple[float, str]:
    """Fetch live gCO₂/kWh for an Azure region.

    Returns (intensity, source) where source is 'live' or 'fallback'.
    Never raises — falls back silently on any error so a carbon API outage
    cannot break a user request.
    """
    api_key = os.environ.get("ELECTRICITY_MAPS_KEY")
    zone = REGION_TO_ZONE.get(region)

    if not api_key or not zone:
        return FALLBACK_CARBON_INTENSITY.get(region, 300.0), "fallback"

    try:
        response = httpx.get(
            _API_BASE,
            params={"zone": zone},
            headers={"auth-token": api_key},
            timeout=_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            data = response.json()
            return float(data["carbonIntensity"]), "live"
        logger.warning("Electricity Maps returned %s for %s", response.status_code, zone)
    except Exception as exc:
        logger.warning("Electricity Maps request failed for %s: %s", zone, exc)

    return FALLBACK_CARBON_INTENSITY.get(region, 300.0), "fallback"


if __name__ == "__main__":
    for region in REGION_TO_ZONE:
        intensity, source = get_carbon_intensity(region)
        print(f"{region:12} {intensity:6.1f} gCO₂/kWh  ({source})")
