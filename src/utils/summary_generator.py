"""
Summary generator for creating news articles from formatted data.
"""

import re
from typing import Any, Dict, List, Optional

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
        self.new_id_to_original_id = {}  # Maps "0" -> "fact-uuid-123"
        self.original_id_to_new_id = {}  # Maps "fact-uuid-123" -> "0"
        self.data_processor = None  # Will be set later
        self.web_search_context = {}  # Store web search context

    def set_id_mappings(
        self,
        new_id_to_original_id: Dict[str, str],
        original_id_to_new_id: Dict[str, str],
    ):
        """
        Set ID mappings from DataProcessor.

        Args:
            new_id_to_original_id: Mapping from numeric IDs to fact UUIDs
            original_id_to_new_id: Mapping from fact UUIDs to numeric IDs
        """
        self.new_id_to_original_id = new_id_to_original_id
        self.original_id_to_new_id = original_id_to_new_id

    def set_data_processor(self, data_processor):
        """
        Set the data processor reference to use for adding web search facts.

        Args:
            data_processor: DataProcessor instance
        """
        self.data_processor = data_processor

    async def generate_summary(self, formatted_data: str) -> Dict[str, Any]:
        """
        Generate a summary from formatted data.

        Args:
            formatted_data: XML-formatted data for the LLM

        Returns:
            Dictionary containing the summary content and facts list
        """
        template = self._create_summary_prompt_template()
        chain = template | self.llm

        result = chain.invoke({"input_data": formatted_data})
        result_content = result.content.strip()

        # Extract facts referenced in the content
        facts_used = self._extract_facts(result_content)
        print(f"[INFO] Initial summary generated: {result_content}")
        print(f"[INFO] Facts used in initial summary: {facts_used}")

        return {"content": result_content, "facts": facts_used}

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
        if self.data_processor is None:
            raise ValueError(
                "Data processor must be set before combining with search results"
            )

        # Process web search results into fact-based format
        sections_xml = self._process_search_results_to_xml(search_results)

        # Create the prompt template and invoke the LLM
        template = self._create_enrichment_prompt_template()

        # Debug: Print the input parameters
        input_params = {
            "initial_summary": initial_summary,
            "search_topic": search_results.title,
            "search_sections": sections_xml,
        }

        print("\n===== DEBUG: INPUT TO LLM CHAIN =====")
        print(f"Search Topic: {search_results.title}")
        print("\nInitial Summary:")
        print(initial_summary)
        print("\nFormatted Search Sections XML:")
        print(sections_xml)

        print("\n===== FULL FORMATTED PROMPT =====")
        print(template.format(**input_params))

        chain = template | self.llm

        result = chain.invoke(input_params)

        result_content = result.content.strip()
        return result_content

    def _process_search_results_to_xml(self, search_results: WebSearchResult) -> str:
        """
        Process web search results into XML format with facts.

        Args:
            search_results: The WebSearchResult from web search agent

        Returns:
            XML formatted string of search results with fact citations
        """
        print(
            f"\n[DEBUG] Processing search results to XML. Found {len(search_results.sections)} sections."
        )

        sections_xml = "<web_search_results>\n"

        # Process each section from the web search results
        for i, section in enumerate(search_results.sections):
            fact_title = section.title
            fact_description = section.description

            print(f"[DEBUG] Processing section {i+1}: {fact_title}")

            # Gather URLs from this section
            urls = []
            section_content = []

            for j, response in enumerate(section.search_responses):
                print(
                    f"[DEBUG]   Found search response {j+1} with query: {response.query}"
                )
                # Add query and its response content to section content
                query_info = f"Query: {response.query}\n"
                section_content.append(query_info)

                for k, result_item in enumerate(response.results):
                    print(
                        f"[DEBUG]     Found result item {k+1}: {result_item.title[:50]}..."
                    )
                    # Simplify to just include URL as required
                    urls.append({"url": result_item.url})

                    # Add content to section content
                    content_info = f"Source: {result_item.title}\nContent: {result_item.content[:200]}...\n"
                    section_content.append(content_info)

            # Skip sections with no URLs
            if not urls:
                print(f"[DEBUG] Section {i+1} has no URLs, skipping.")
                continue

            print(f"[DEBUG] Creating fact for section {i+1} with {len(urls)} URLs.")

            # Check if JWT token is available without calling the API yet
            import os

            jwt_token = os.getenv("JWT_TOKEN")
            if not jwt_token:
                print(
                    "[WARNING] No JWT token available. Will create XML without API call."
                )
                # Even without a token, we can still create the XML structure for testing
                citation_id = self.data_processor.current_id
                self.data_processor.current_id += 1

                # Add section to XML without creating a fact
                sections_xml += f'  <section fact_id="{citation_id}">\n'
                sections_xml += f"    <title>{section.title}</title>\n"
                sections_xml += (
                    f"    <description>{section.description}</description>\n"
                )
                # Add content data
                sections_xml += f"    <content>\n"
                sections_xml += "      " + "\n      ".join(section_content) + "\n"
                sections_xml += "    </content>\n"
                sections_xml += "  </section>\n"
                continue

            # Create a new fact from this section via API and get the fact ID
            condensed_description = self.condense_description(fact_description)
            print(f"[DEBUG] Condensed description: {condensed_description}")
            # Create the fact using the API
            fact_id = self._create_fact_from_section(condensed_description, urls)

            if fact_id:
                print(f"[DEBUG] Successfully created fact with ID {fact_id}")
                # Add the fact to the data processor
                citation_id = self.data_processor.add_web_search_fact(
                    fact_id, fact_title
                )

                # Add section to XML
                sections_xml += f'  <section fact_id="{citation_id}">\n'
                sections_xml += f"    <title>{section.title}</title>\n"
                sections_xml += (
                    f"    <description>{section.description}</description>\n"
                )
                # Add content data
                sections_xml += f"    <content>\n"
                sections_xml += "      " + "\n      ".join(section_content) + "\n"
                sections_xml += "    </content>\n"
                sections_xml += "  </section>\n"
            else:
                print(f"[DEBUG] Failed to create fact for section {i+1}")

        sections_xml += "</web_search_results>"
        print(f"[DEBUG] Final XML length: {len(sections_xml)}")
        return sections_xml

    def _create_fact_from_section(
        self, description: str, urls: List[Dict[str, str]]
    ) -> Optional[str]:
        """
        Create a fact from search section by calling the API.

        Args:
            description: The description of the section/fact
            urls: List of URLs with titles from the search results

        Returns:
            Fact ID if successfully created, None otherwise
        """
        try:
            # Import the API client dynamically to avoid circular imports
            import os

            from utils.api_client import APIClient

            client = APIClient(phase=os.getenv("API_PHASE", "stage"))
            jwt_token = os.getenv("JWT_TOKEN")

            if not jwt_token:
                print("[WARNING] No JWT token available. Cannot create fact.")
                return None

            # Format the references for the API
            references = []
            for url_info in urls:
                references.append({"url": url_info["url"]})

            # Create the fact
            fact_payload = {"fact_title": description, "references": references}

            # Call the API to create the fact
            response = client.create_fact_with_url_validation(
                **fact_payload, jwt_token=jwt_token
            )

            # Return the fact ID
            if response and "id" in response:
                return response["id"]
            else:
                print(f"[ERROR] Failed to create fact: {response}")
                return None

        except Exception as e:
            print(f"[ERROR] Error creating fact: {e}")
            return None

    def get_facts_list(self) -> List[str]:
        """
        Get all fact IDs referenced in order of citation.

        Returns:
            List of fact UUIDs in order of citation
        """
        if self.data_processor is None:
            return []

        return self.data_processor.get_facts_list()

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

    def condense_description(self, description: str) -> str:
        """
        Condense a long description to a shorter version using LLM.

        Args:
            description: The long description text to condense

        Returns:
            A condensed version of the description
        """
        # Import the prompts
        from .prompt import (
            condense_description_human_prompt,
            condense_description_system_prompt,
        )

        # Skip condensation if description is already short (less than 150 chars)
        if len(description) < 15:
            return description

        template = ChatPromptTemplate.from_messages(
            [
                ("system", condense_description_system_prompt),
                ("human", condense_description_human_prompt),
            ]
        )

        chain = template | self.llm

        try:
            print(f"[INFO] Condensing description of {len(description)} characters")
            result = chain.invoke({"description": description})
            condensed = result.content.strip()
            print(f"[INFO] Condensed to {len(condensed)} characters")
            return condensed
        except Exception as e:
            print(f"[ERROR] Failed to condense description: {e}")
            # Return original if condensation fails
            return description

    def _extract_facts(self, content: str) -> Dict[str, str]:
        """
        Extract fact references from content using the new [](num) format.

        Args:
            content: The generated content

        Returns:
            Dictionary mapping citation numbers to fact IDs
        """
        # Find all citations with format [](0), [](1,2), etc.
        citation_pattern = r"\[\]\((\d+(?:,\d+)*)\)"
        matches = re.findall(citation_pattern, content)

        facts_used = {}
        for match in matches:
            # Split comma-separated citations
            citation_ids = match.split(",")
            for citation_id in citation_ids:
                citation_id = citation_id.strip()
                if citation_id in self.new_id_to_original_id:
                    facts_used[citation_id] = self.new_id_to_original_id[citation_id]

        return facts_used
