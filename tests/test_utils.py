"""
Unit tests for the reference system.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest

from utils.data_processor import DataProcessor
from utils.summary_generator import SummaryGenerator


class TestDataProcessor(unittest.TestCase):
    """Tests for the DataProcessor class."""

    def setUp(self):
        """Set up test data."""
        self.test_viewpoints = {
            "content": [
                {
                    "content": "Test comment content",
                    "authorName": "Test Author",
                    "facts": [
                        {
                            "title": "Test Fact",
                            "references": [
                                {
                                    "id": "ref-123",
                                    "title": "Test Reference",
                                    "url": "https://example.com",
                                    "description": "Test description",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        self.processor = DataProcessor(self.test_viewpoints)

    def test_format_xml_metadata(self):
        """Test XML formatting of metadata."""
        issue_title = "Test Issue Title"
        result = self.processor.format_xml_metadata(issue_title)

        # Check that the XML contains the expected elements
        assert "<issue>" in result
        assert f"<title>{issue_title}</title>" in result
        assert "<comment>" in result
        assert "<content>Test comment content</content>" in result
        assert "<author>Test Author</author>" in result
        assert "<fact>" in result
        assert "<title>Test Fact</title>" in result
        assert '<reference id="1">' in result
        assert "<title>Test Reference</title>" in result
        assert "<url>https://example.com</url>" in result
        assert "<description>Test description</description>" in result

        # Check that the mapping is created correctly
        assert "ref-123" in self.processor.original_id_to_new_id
        assert self.processor.original_id_to_new_id["ref-123"] == "1"
        assert "1" in self.processor.new_id_to_original_id
        assert self.processor.new_id_to_original_id["1"] == "ref-123"


@pytest.mark.asyncio
class TestSummaryGenerator:
    """Tests for the SummaryGenerator class."""

    @patch("langchain_openai.ChatOpenAI")
    async def test_generate_summary(self, mock_llm):
        """Test summary generation."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Test summary with citation [1]"
        mock_llm.return_value.invoke.return_value = mock_response

        # Create SummaryGenerator with mock LLM
        generator = SummaryGenerator(mock_llm.return_value)

        # Test generating summary
        result = await generator.generate_summary("<issue><title>Test</title></issue>")

        # Check that the summary is extracted correctly
        assert result["content"] == "Test summary with citation [1]"
        assert "1" in result["citations"]

    @patch("langchain_openai.ChatOpenAI")
    async def test_combine_with_search_results(self, mock_llm):
        """Test combining summary with search results."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Enhanced summary with web search info"
        mock_llm.return_value.invoke.return_value = mock_response

        # Create SummaryGenerator with mock LLM
        generator = SummaryGenerator(mock_llm.return_value)

        # Mock WebSearchResult
        mock_search_result = MagicMock()
        mock_search_result.title = "Test Search"
        mock_section = MagicMock()
        mock_section.title = "Section 1"
        mock_section.description = "Description 1"
        mock_search_result.sections = [mock_section]

        # Test combining summary with search results
        result = await generator.combine_with_search_results(
            "Initial summary", mock_search_result
        )

        # Check that the result contains the enhanced summary
        assert result == "Enhanced summary with web search info"

        # Verify that the LLM was called with the correct arguments
        mock_llm.return_value.invoke.assert_called_once()
        call_args = mock_llm.return_value.invoke.call_args[0][0]
        assert "Initial summary" in str(call_args)
        assert "Test Search" in str(call_args)
        assert "Section 1" in str(call_args)
        assert "Description 1" in str(call_args)
