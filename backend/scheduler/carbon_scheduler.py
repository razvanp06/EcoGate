# STUB — replace with Agent 4's full implementation
import os
from shared.models import RoutingDecision


def get_routing_decision(prompt: str, urgency: str) -> RoutingDecision:
    endpoint = os.environ.get("AZURE_OAI_WESTEUROPE_ENDPOINT", "")
    return RoutingDecision(
        model="gpt-4o-mini",
        region="westeurope",
        endpoint=endpoint,
        api_key_env="AZURE_OAI_WESTEUROPE_KEY",
        complexity_tier=1,
        defer=False,
        defer_until=None,
        carbon_intensity=150.0,
        carbon_intensity_baseline=386.0,
        routing_reason="Stub: defaulting to gpt-4o-mini in westeurope.",
    )
