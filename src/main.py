"""
Main module for the reference system application.
This integrates API data processing with web-search-agent for enhanced context.
"""

import asyncio
import json
import os
from typing import Dict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from web_search_agent import WebSearchAgent, WebSearchConfig

from utils.api_client import APIClient
from utils.data_processor import DataProcessor
from utils.summary_generator import SummaryGenerator


async def process_issue(
    issue_id: str,
    issue_title: str,
    client: APIClient,
    llm: ChatOpenAI,
    search_agent: WebSearchAgent,
) -> Dict:
    """
    Process a single issue by generating a summary and enriching with web search.

    Args:
        issue_id: The ID of the issue to process
        issue_title: The title of the issue
        client: API client for data retrieval
        llm: Language model for summary generation
        search_agent: Web search agent for additional context

    Returns:
        A dictionary containing the processed results
    """
    # Get viewpoints data for this issue
    viewpoints = client.load_viewpoints_from_issue_id(issue_id)

    # Process data and generate initial summary
    processor = DataProcessor(viewpoints)
    formatted_data = processor.format_xml_metadata(issue_title)

    # Generate initial summary
    summary_generator = SummaryGenerator(llm)
    # Connect the summary generator with the data processor
    summary_generator.set_data_processor(processor)
    summary_generator.set_id_mappings(
        processor.new_id_to_original_id, processor.original_id_to_new_id
    )

    # Generate initial summary from user data
    initial_summary = await summary_generator.generate_summary(formatted_data)

    # Use web search agent to enrich the summary with additional context
    search_config = WebSearchConfig(
        planner_model="gpt-4o",
        initial_queries_count=3,
        max_sections=5,
        must_cover_section_title="請針對此議題提供以下幾個面向的資訊：主要涉及方、不同立場觀點、關鍵數據與事實",
    )
    search_agent = WebSearchAgent(config=search_config)

    search_results = await search_agent.search(
        issue_title, additional_info=initial_summary["content"]
    )

    print(f"[INFO] Web search completed with {len(search_results.sections)} sections")

    # Combine the initial summary with search results
    final_insight = await summary_generator.combine_with_search_results(
        initial_summary["content"], search_results
    )

    # Get final list of facts in ordered citation format
    facts_list = processor.get_facts_list()

    # Create final result
    result = {
        "issue_id": issue_id,
        "title": issue_title,
        "insight": final_insight,
        "facts": facts_list,
    }

    return result


async def main() -> None:
    """Main function to run the news generation and web search process."""
    # Load environment variables
    load_dotenv(os.path.join(os.getcwd(), "config", ".env"))

    # Initialize API client
    client = APIClient(phase=os.getenv("API_PHASE", "stage"))

    # Initialize language model
    llm = ChatOpenAI(model="gpt-4o")

    # Get all issues
    all_issues = client.get_all_issues()

    # Process each issue
    results = []
    for i, issue in enumerate(all_issues):
        # needed to be commented
        if i == 2:
            break
        print(
            f"\n[INFO] === Processing issue {i+1}/{len(all_issues)}: {issue.get('title', 'No title')} ==="
        )

        try:
            # Create a new WebSearchAgent for each issue to avoid state conflicts
            search_agent = WebSearchAgent(
                config=WebSearchConfig(
                    planner_model="gpt-4o",
                    initial_queries_count=3,
                    max_sections=5,
                    must_cover_section_title="請針對此議題提供以下幾個面向的資訊：主要涉及方、不同立場觀點、關鍵數據與事實",
                )
            )

            result = await process_issue(
                issue["id"], issue["title"], client, llm, search_agent
            )
            results.append(result)

            # Send results back to platform
            if os.getenv("JWT_TOKEN"):
                response = client.put_reference_result_to_platform(
                    issue["id"],
                    result["insight"],
                    issue["title"],
                    result["facts"],
                    os.getenv("JWT_TOKEN"),
                )
                print(f"[INFO] API update response: {response}")

        except Exception as e:
            print(f"[ERROR] Error processing issue {issue['id']}: {str(e)}")
            continue

    # Format results to match expected output structure
    output_data = {"results": results}

    # Write results to output files
    output_paths = ["./src/output/results.json", "./docker_output/results.json"]

    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
