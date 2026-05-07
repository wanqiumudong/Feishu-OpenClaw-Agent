import unittest

from config import Settings
from providers.mock_provider import MockProvider
from retrieval.graphrag_index import build_graphrag_index
from retrieval.graphrag import graphrag_retrieve


class GraphRAGTest(unittest.TestCase):
    def setUp(self):
        self.settings = Settings.default()
        self.provider = MockProvider(self.settings)
        self.bundle = self.provider.load_bundle()

    def test_graphrag_index_builds_standard_tables(self):
        index = build_graphrag_index(self.bundle)
        self.assertGreaterEqual(len(index.text_units), 80)
        self.assertGreaterEqual(len(index.entities), 40)
        self.assertGreaterEqual(len(index.relationships), 80)
        self.assertGreaterEqual(len(index.community_reports), 4)

    def test_graphrag_expands_beyond_seed_items(self):
        result = graphrag_retrieve(self.bundle, "Go/No-Go 灰度发布有哪些阻塞？", seed_limit=5, limit=10)
        self.assertEqual(result.context.mode, "local")
        self.assertGreaterEqual(len(result.context.selected_entities), 3)
        self.assertGreaterEqual(len(result.context.text_units), 3)
        self.assertGreaterEqual(len(result.context.relationships), 1)

    def test_graphrag_global_uses_community_reports(self):
        result = graphrag_retrieve(self.bundle, "项目当前主要主题和风险是什么？", mode="global", limit=10)
        self.assertEqual(result.context.mode, "global")
        self.assertGreaterEqual(len(result.context.community_reports), 2)
        self.assertGreaterEqual(len(result.expanded_items), 3)


if __name__ == "__main__":
    unittest.main()
