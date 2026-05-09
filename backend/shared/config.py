import os


class Config:
    # Sweden Central — clean region (~27 gCO₂/kWh, hydro + nuclear)
    SWEDEN_ENDPOINT: str = os.environ.get("SWEDEN_ENDPOINT", "")
    SWEDEN_KEY: str = os.environ.get("SWEDEN_KEY", "")

    # East US 2 — baseline/dirty region (~380 gCO₂/kWh)
    EASTUS2_ENDPOINT: str = os.environ.get("EASTUS2_ENDPOINT", "")
    EASTUS2_KEY: str = os.environ.get("EASTUS2_KEY", "")

    ELECTRICITY_MAPS_KEY: str = os.environ.get("ELECTRICITY_MAPS_KEY", "")

    PINECONE_API_KEY: str = os.environ.get("PINECONE_API_KEY", "")
    PINECONE_INDEX_HOST: str = os.environ.get("PINECONE_INDEX_HOST", "")

    @classmethod
    def validate(cls) -> list[str]:
        required = ["SWEDEN_ENDPOINT", "SWEDEN_KEY", "EASTUS2_ENDPOINT", "EASTUS2_KEY"]
        return [k for k in required if not os.environ.get(k)]
