from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from shared.models import RoutingDecision

from scheduler.complexity_router import classify_complexity, MODEL_FOR_TIER
from scheduler.carbon_client import get_carbon_intensity, FALLBACK_CARBON_INTENSITY
from scheduler.deferred_queue import enqueue

AVAILABLE_REGIONS = ["swedencentral", "eastus2"]

# Defer batch jobs when grid is above this carbon intensity (gCO₂/kWh)
DEFER_THRESHOLD_GCO2_KWH = 250.0

# How long to defer a batch job when no forecast is available
DEFAULT_DEFER_HOURS = 2

REGION_CONFIG = {
    "swedencentral": {
        "endpoint_env": "SWEDEN_ENDPOINT",
        "key_env": "SWEDEN_KEY",
        "electricity_maps_zone": "SE",
        "fallback_carbon": 27.0,
    },
    "eastus2": {
        "endpoint_env": "EASTUS2_ENDPOINT",
        "key_env": "EASTUS2_KEY",
        "electricity_maps_zone": "US-MIDA-PJM",
        "fallback_carbon": 380.0,
    },
}


def _should_defer(urgency: str, carbon_intensity: float) -> tuple[bool, Optional[str]]:
    """Defer only if the user opted into batch AND the chosen grid is dirty."""
    if urgency != "batch":
        return False, None
    if carbon_intensity <= DEFER_THRESHOLD_GCO2_KWH:
        return False, None
    defer_until = datetime.now(timezone.utc) + timedelta(hours=DEFAULT_DEFER_HOURS)
    return True, defer_until.isoformat()


def _build_reason(
    tier: int,
    model: str,
    region: str,
    intensity: float,
    sources: dict[str, str],
    defer: bool,
) -> str:
    fallback_note = " (fallback carbon data)" if sources.get(region) == "fallback" else ""
    if defer:
        return (
            f"Deferred: {region} grid at {intensity:.0f} gCO₂/kWh exceeds "
            f"{DEFER_THRESHOLD_GCO2_KWH:.0f} threshold; batch job queued{fallback_note}."
        )
    if tier == 1:
        return (
            f"Routed to {model} in {region} ({intensity:.0f} gCO₂/kWh): "
            f"simple prompt, efficient model{fallback_note}."
        )
    return (
        f"Routed to {model} in {region} ({intensity:.0f} gCO₂/kWh): "
        f"complex prompt requires full model{fallback_note}."
    )


def get_routing_decision(prompt: str, urgency: str) -> RoutingDecision:
    """Pick the cheapest model and greenest region for this prompt.

    Stage 3 (complexity) + Stage 4 (carbon-aware routing & deferral).
    Never raises — falls back to historical carbon averages if the API is down.
    """
    # Stage 3: complexity → model tier
    tier = classify_complexity(prompt)
    model = MODEL_FOR_TIER[tier]

    # Stage 4: live carbon intensity per region (with fallback)
    intensities: dict[str, float] = {}
    sources: dict[str, str] = {}
    for region in AVAILABLE_REGIONS:
        intensity, source = get_carbon_intensity(region)
        intensities[region] = intensity
        sources[region] = source

    # Pick greenest region (every region exposes both model tiers)
    best_region = min(intensities, key=intensities.get)
    best_intensity = intensities[best_region]
    baseline_intensity = intensities.get(
        "eastus2", FALLBACK_CARBON_INTENSITY["eastus2"]
    )

    config = REGION_CONFIG[best_region]
    endpoint = os.environ.get(config["endpoint_env"], "")

    # Defer if batch + dirty grid
    defer, defer_until = _should_defer(urgency, best_intensity)
    if defer:
        enqueue(
            prompt=prompt,
            system_prompt=None,
            defer_until=defer_until,
            carbon_intensity=best_intensity,
        )

    reason = _build_reason(tier, model, best_region, best_intensity, sources, defer)

    return RoutingDecision(
        model=model,
        region=best_region,
        endpoint=endpoint,
        api_key_env=config["key_env"],
        complexity_tier=tier,
        defer=defer,
        defer_until=defer_until,
        carbon_intensity=best_intensity,
        carbon_intensity_baseline=baseline_intensity,
        routing_reason=reason,
    )
