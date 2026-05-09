import os


class Config:
    AZURE_OAI_WESTEUROPE_ENDPOINT: str = os.environ.get("AZURE_OAI_WESTEUROPE_ENDPOINT", "")
    AZURE_OAI_WESTEUROPE_KEY: str = os.environ.get("AZURE_OAI_WESTEUROPE_KEY", "")
    AZURE_OAI_EASTUS_ENDPOINT: str = os.environ.get("AZURE_OAI_EASTUS_ENDPOINT", "")
    AZURE_OAI_EASTUS_KEY: str = os.environ.get("AZURE_OAI_EASTUS_KEY", "")
    AZURE_OAI_API_VERSION: str = os.environ.get("AZURE_OAI_API_VERSION", "2024-02-01")
    ELECTRICITY_MAPS_KEY: str = os.environ.get("ELECTRICITY_MAPS_KEY", "")

    PINECONE_API_KEY: str = os.environ.get("PINECONE_API_KEY", "")
    PINECONE_INDEX_HOST: str = os.environ.get("PINECONE_INDEX_HOST", "")

    @classmethod
    def validate(cls) -> list[str]:
        """Returns a list of missing required env vars. Empty = all good."""
        required = [
            "AZURE_OAI_WESTEUROPE_ENDPOINT",
            "AZURE_OAI_WESTEUROPE_KEY",
        ]
        return [k for k in required if not os.environ.get(k)]
