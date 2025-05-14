import unittest
import sys
from kazqad_retrieval import KazQADRetrieval
from tokenizer import KazakhTokenizer


class TestKazQADRetrieval(unittest.TestCase):
    """Tests for the KazQADRetrieval class"""

    # Create a shared retrieval instance to speed up tests
    # This avoids the need for setUp/tearDown methods
    try:
        # Ensure stdout is properly configured for Windows
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

        retrieval = KazQADRetrieval(threshold=0.1)

        # Set up test queries
        test_queries = [
            "Қазақстан тарихы",
            "Абай Құнанбаев",
            "Қазақстан астанасы",
            "Алматы қаласы"
        ]
    except Exception as e:
        print(f"Error initializing retrieval system: {e}")
        retrieval = None

    def test_initialization(self):
        """Test that retrieval system initializes correctly"""
        self.assertIsNotNone(self.retrieval)
        self.assertIsNotNone(self.retrieval.dataset)
        self.assertTrue(len(self.retrieval.passages) > 0)
        self.assertTrue(len(self.retrieval.tokenized_passages) > 0)

    def test_dataset_info(self):
        """Test dataset info method returns correct information"""
        if not self.retrieval:
            self.skipTest("Retrieval system not initialized")

        info = self.retrieval.dataset_info()

        self.assertIn('total_passages', info)
        self.assertIn('splits', info)
        self.assertIn('passage_statistics', info)
        self.assertIn('token_statistics', info)

        # Check if values are populated
        self.assertTrue(info['total_passages'] > 0)
        self.assertTrue(len(info['splits']) > 0)

    def test_basic_retrieval(self):
        """Test basic retrieval functionality"""
        if not self.retrieval:
            self.skipTest("Retrieval system not initialized")

        query = self.test_queries[0]  # Use first query
        results = self.retrieval.retrieve(query, threshold=0.1)

        # Test that we get some results
        self.assertTrue(len(results) > 0, f"No results found for query: {query}")

        # Check result structure
        for result in results:
            self.assertIn('text', result)
            self.assertIn('score', result)
            self.assertIn('tokens', result)

            # Make sure text is a string and not empty
            self.assertIsInstance(result['text'], str)
            self.assertTrue(len(result['text']) > 0)

            # Make sure score is a float
            self.assertIsInstance(result['score'], float)

    def test_tokenization(self):
        """Test tokenization with KazakhTokenizer"""
        # Test basic tokenization
        text = "Қазақстан Республикасы - тәуелсіз мемлекет."
        tokens = KazakhTokenizer.tokenize(text)

        self.assertTrue(len(tokens) > 0)
        self.assertTrue(all(isinstance(t, str) for t in tokens))

        # Test with stemming
        tokens_stemmed = KazakhTokenizer.tokenize(text, apply_stemming=True)
        self.assertTrue(len(tokens_stemmed) > 0)

    def test_empty_query(self):
        """Test that empty queries return empty results"""
        if not self.retrieval:
            self.skipTest("Retrieval system not initialized")

        results = self.retrieval.retrieve("")
        self.assertEqual(len(results), 0)

        results = self.retrieval.retrieve("   ")
        self.assertEqual(len(results), 0)

    def test_query_analysis(self):
        """Test query analysis functionality"""
        if not self.retrieval:
            self.skipTest("Retrieval system not initialized")

        query = self.test_queries[0]
        analysis = self.retrieval.query_analysis(query)

        self.assertIn('query', analysis)
        self.assertIn('tokenized_query', analysis)
        self.assertIn('expanded_query', analysis)
        self.assertIn('results', analysis)
        self.assertIn('execution_time', analysis)

        self.assertEqual(analysis['query'], query)
        self.assertTrue(len(analysis['tokenized_query']) > 0)
        self.assertTrue(len(analysis['expanded_query']) > 0)
        self.assertIsInstance(analysis['execution_time'], float)

    def test_search_with_filters(self):
        """Test search with additional filters"""
        if not self.retrieval:
            self.skipTest("Retrieval system not initialized")

        query = "Қазақстан"

        # Get regular results
        regular_results = self.retrieval.retrieve(query)

        # Get filtered results (by length)
        min_length = 200
        filtered_results = self.retrieval.search_with_filters(query, min_length=min_length)

        # All filtered results should have at least min_length characters
        for result in filtered_results:
            self.assertGreaterEqual(len(result['text']), min_length)

    def test_different_threshold(self):
        """Test retrieval with different thresholds"""
        if not self.retrieval:
            self.skipTest("Retrieval system not initialized")

        query = self.test_queries[0]

        # Get results with low threshold
        low_threshold_results = self.retrieval.retrieve(query, threshold=0.1)

        # Get results with high threshold
        high_threshold_results = self.retrieval.retrieve(query, threshold=3.0)

        # High threshold should return fewer or equal results
        self.assertGreaterEqual(len(low_threshold_results), len(high_threshold_results))

        # High threshold results should all have scores above threshold
        for result in high_threshold_results:
            self.assertGreaterEqual(result['score'], 3.0)


if __name__ == '__main__':
    unittest.main()