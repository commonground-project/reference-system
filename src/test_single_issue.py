"""
Test script for processing a single issue with the reference system.
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


async def test_single_issue(issue_id: str = None, test_mode: bool = True) -> Dict:
    """
    Test the reference system by processing a single issue.

    Args:
        issue_id: Optional issue ID to process. If None, use example data.
        test_mode: If True, use example data instead of API.

    Returns:
        The generated result
    """
    # Load environment variables
    load_dotenv(os.path.join("config", ".env"))

    # Initialize language model
    llm = ChatOpenAI(model="gpt-4o-mini")

    # Initialize web search agent
    search_config = WebSearchConfig(
        planner_model="gpt-3.5-turbo", initial_queries_count=2, max_sections=3
    )
    search_agent = WebSearchAgent(config=search_config)

    if test_mode:
        # Load example viewpoints data for testing
        with open(
            os.path.join("data", "example_api_data.json"), "r", encoding="utf-8"
        ) as f:
            viewpoints = json.load(f)

        issue_title = "測試議題：再生能源發展與傳統能源的平衡"
    else:
        # Initialize API client and load real data
        client = APIClient()

        # If no issue_id is provided, get the first available issue
        if not issue_id:
            all_issues = client.get_all_issues()
            issue_id = all_issues[0]["id"]
            issue_title = all_issues[0]["title"]
        else:
            # Get a specific issue by ID
            viewpoints = client.load_viewpoints_from_issue_id(issue_id)
            # Note: In a real implementation, you would fetch the issue title from the API
            issue_title = "指定議題"

    # Process data
    processor = DataProcessor(viewpoints)
    formatted_data = processor.format_xml_metadata(issue_title)

    # Generate initial summary
    summary_generator = SummaryGenerator(llm)
    initial_summary = await summary_generator.generate_summary(formatted_data)

    print(f"Initial summary generated:\n{initial_summary['content'][:300]}...\n")

    # Use web search agent to enrich the summary
    search_results = await search_agent.search(
        issue_title, additional_info=initial_summary["content"]
    )

    print(f"Web search completed. Found {len(search_results.sections)} sections.")

    # Combine the initial summary with search results
    final_summary = await summary_generator.combine_with_search_results(
        initial_summary["content"], search_results
    )

    print(f"Final enriched summary created:\n{final_summary[:300]}...\n")

    # Create final result
    result = {
        "issue_id": issue_id or "test-issue",
        "title": issue_title,
        "summary": final_summary,
        "citation": initial_summary["citations"],
    }

    # Save the result to file
    with open(
        os.path.join("src", "output", "test_result.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


if __name__ == "__main__":
    asyncio.run(test_single_issue(test_mode=True))
