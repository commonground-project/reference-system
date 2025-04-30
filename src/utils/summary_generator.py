"""
Summary generator for creating news articles from formatted data.
"""

import re
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from web_search_agent import WebSearchResult

from .prompt import (
    conbine_summary_human_prompt,
    conbine_summary_system_prompt,
    reference_summary_human_prompt,
    reference_summary_system_prompt,
)


class SummaryGenerator:
    """Generate summaries and news articles from formatted data."""

    def __init__(self, llm: ChatOpenAI):
        """
        Initialize the summary generator.

        Args:
            llm: LangChain LLM instance for text generation
        """
        self.llm = llm
        self.new_id_to_original_id = {}  # Maps "1" -> "uuid-123-456"
        self.original_id_to_new_id = {}  # Maps "uuid-123-456" -> "1"

    def set_id_mappings(
        self,
        new_id_to_original_id: Dict[str, str],
        original_id_to_new_id: Dict[str, str],
    ):
        """
        Set ID mappings from DataProcessor.

        Args:
            new_id_to_original_id: Mapping from numeric IDs to UUIDs
            original_id_to_new_id: Mapping from UUIDs to numeric IDs
        """
        self.new_id_to_original_id = new_id_to_original_id
        self.original_id_to_new_id = original_id_to_new_id

    async def generate_summary(self, formatted_data: str) -> Dict[str, Any]:
        """
        Generate a summary from formatted data.

        Args:
            formatted_data: XML-formatted data for the LLM

        Returns:
            Dictionary containing the summary content and citations
        """
        template = self._create_summary_prompt_template()
        chain = template | self.llm

        result = chain.invoke({"input_data": formatted_data})
        result_content = self._extract_output_from_content(result.content)

        # Get references from the content
        citations = self._extract_citations(result_content)
        print(f"Result of the summarization {result_content}")
        return {"content": result_content, "citations": citations}

    async def combine_with_search_results(
        self, initial_summary: str, search_results: WebSearchResult
    ) -> str:
        """
        Combine initial summary with web search results.

        Args:
            initial_summary: The initial summary generated from user data
            search_results: Results from web search agent

        Returns:
            Enhanced summary with web search context
        """
        template = self._create_enrichment_prompt_template()
        chain = template | self.llm

        # Extract sections from web search results
        sections_text = "\n\n".join(
            [
                f"- {section.title}: {section.description}"
                for section in search_results.sections
            ]
        )

        result = chain.invoke(
            {
                "initial_summary": initial_summary,
                "search_topic": search_results.title,
                "search_sections": sections_text,
            }
        )

        result_content = self._extract_output_from_content(result.content)
        return result_content

    def _create_summary_prompt_template(self) -> ChatPromptTemplate:
        """Create the summary generation prompt template."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", reference_summary_system_prompt),
                ("human", reference_summary_human_prompt),
            ]
        )

    def _create_enrichment_prompt_template(self) -> ChatPromptTemplate:
        """Create the template for enriching summaries with web search results."""
        return ChatPromptTemplate.from_messages(
            [
                ("system", conbine_summary_system_prompt),
                ("human", conbine_summary_human_prompt),
            ]
        )

    def _extract_output_from_content(self, content: str) -> str:
        """Extract the output from the model response content."""
        # Look for output between XML article tags if present
        if "<article>" in content and "</article>" in content:
            start_idx = content.find("<article>") + len("<article>")
            end_idx = content.find("</article>")
            return content[start_idx:end_idx].strip()

        # Fallback to markdown-style delimiters if XML tags not found
        elif "###輸出開始###" in content and "###輸出結束###" in content:
            start_idx = content.find("###輸出開始###") + len("###輸出開始###")
            end_idx = content.find("###輸出結束###")
            return content[start_idx:end_idx].strip()

        # Otherwise return the entire content
        return content.strip()

    def _extract_citations(self, content: str) -> Dict[str, str]:
        """
        Extract citation numbers from content.

        Args:
            content: The generated content

        Returns:
            Dictionary mapping citation numbers to reference IDs
        """
        citation_numbers = sorted(set(map(int, re.findall(r"\[(\d+)\]", content))))
        return {
            str(citation): self._get_reference_id(citation)
            for citation in citation_numbers
        }

    def _get_reference_id(self, citation_number: int) -> str:
        """
        Get original UUID for a citation number.

        Args:
            citation_number: The citation number (1, 2, 3...)

        Returns:
            The corresponding original UUID
        """
        citation_str = str(citation_number)
        if citation_str in self.new_id_to_original_id:
            return self.new_id_to_original_id[citation_str]
        else:
            # Fallback for citations not in mapping
            return f"ref-{citation_number}"
