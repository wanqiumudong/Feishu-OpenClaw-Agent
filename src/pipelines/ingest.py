from providers.mock_provider import MockProvider
from retrieval.indexer import build_index


def ingest_mock_knowledge(provider: MockProvider):
    """Load mock data and build the in-memory knowledge index."""

    bundle = provider.load_bundle()
    return build_index(bundle)
