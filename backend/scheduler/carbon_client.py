from __future__ import annotations
import os
import logging
import time

import httpx

logger = logging.getLogger(__name__)

# Azure region → Electricity Maps zone code
REGION_TO_ZONE = {
    "swedencentral": "SE",      # Sweden grid (mostly hydro + nuclear)
    "eastus2": "US-MIDA-PJM",   # US East 2 (Virginia) on the PJM grid
}

# Historical-average gCO₂/kWh, used when the API is unreachable or unkeyed.
# Values from electricitymaps.com 2023–2024 yearly averages.
FALLBACK_CARBON_INTENSITY = {
    "swedencentral": 40.0,      # Sweden grid is one of the cleanest in Europe
    "eastus2": 386.0,           # PJM grid, gas + coal heavy
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

    if not api_key:
        logger.warning(
            "ELECTRICITY_MAPS_KEY not set — using fallback carbon for %s", region
        )
        return FALLBACK_CARBON_INTENSITY.get(region, 300.0), "fallback"

    if not zone:
        logger.warning("Unknown region %r — using fallback carbon", region)
        return FALLBACK_CARBON_INTENSITY.get(region, 300.0), "fallback"

    try:
        t0 = time.perf_counter()
        response = httpx.get(
            _API_BASE,
            params={"zone": zone},
            headers={"auth-token": api_key},
            timeout=_TIMEOUT_SECONDS,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if response.status_code == 200:
            data = response.json()
            intensity = float(data["carbonIntensity"])
            logger.info(
                "Electricity Maps live: %s (zone %s) = %.1f gCO2/kWh (%.0fms)",
                region, zone, intensity, elapsed_ms,
            )
            return intensity, "live"
        logger.warning(
            "Electricity Maps returned HTTP %s for zone %s — falling back",
            response.status_code, zone,
        )
    except Exception as exc:
        logger.warning(
            "Electricity Maps request failed for zone %s: %s — falling back",
            zone, exc,
        )

    fallback = FALLBACK_CARBON_INTENSITY.get(region, 300.0)
    logger.info("Using fallback carbon for %s: %.1f gCO2/kWh", region, fallback)
    return fallback, "fallback"


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    for region in REGION_TO_ZONE:
        intensity, source = get_carbon_intensity(region)
        print(f"{region:14} {intensity:6.1f} gCO₂/kWh  ({source})")
