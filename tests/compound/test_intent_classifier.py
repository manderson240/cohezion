"""Tests for zero-token intent classifier."""
import pytest
from cohezion.compound.intent_classifier import IntentClassifier


class TestIntentClassifier:

    @pytest.fixture
    def clf(self):
        return IntentClassifier()

    def test_generate_intent(self, clf):
        assert clf.classify("Generate 10 creative ideas") == "generate"
        assert clf.classify("Create a function to sort a list") == "generate"

    def test_analyze_intent(self, clf):
        assert clf.classify("Analyze the CSV data") == "analyze"
        assert clf.classify("Evaluate the performance metrics") == "analyze"

    def test_search_intent(self, clf):
        assert clf.classify("Search for relevant files") == "search"
        assert clf.classify("Find all Python files") == "search"

    def test_transform_intent(self, clf):
        assert clf.classify("Transform the JSON to CSV") == "transform"
        assert clf.classify("Convert the data format") == "transform"

    def test_default_intent(self, clf):
        result = clf.classify("xyz_unintelligible_gibberish_12345")
        assert result == clf.default_operation

    def test_case_insensitive(self, clf):
        assert clf.classify("GENERATE content") == "generate"
        assert clf.classify("ANALYZE data") == "analyze"

    def test_get_all_keywords_returns_dict(self, clf):
        keywords = clf.get_all_keywords()
        assert isinstance(keywords, dict)
        assert "generate" in keywords
        assert "analyze" in keywords

    def test_custom_default_operation(self):
        clf = IntentClassifier(default_operation="analyze")
        result = clf.classify("unintelligible_gibberish")
        assert result == "analyze"

