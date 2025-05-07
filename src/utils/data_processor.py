"""
Data processor for transforming API data into formatted content for LLM processing.
"""

from typing import Dict, List


class DataProcessor:
    """Process and format data from the API for LLM consumption."""

    def __init__(self, viewpoints: Dict):
        """
        Initialize the data processor.

        Args:
            viewpoints: The viewpoints data from the API
        """
        self.viewpoints = viewpoints
        self.original_id_to_new_id = {}  # Maps fact UUID to citation number
        self.new_id_to_original_id = {}  # Maps citation number to fact UUID
        self.current_id = 0  # Track the current ID for citations, starting from 0
        self.web_search_facts = {}  # Store web search facts with their IDs

    def format_xml_metadata(self, issue_title: str) -> str:
        """
        Format data for model input using XML tags.

        Args:
            issue_title: The title of the issue

        Returns:
            A formatted string with XML tags
        """
        print(f"[INFO] Formatting XML for issue: {issue_title}")
        result = f"<issue>\n  <title>{issue_title}</title>\n"

        for comment in self.viewpoints["content"]:
            result += f"  <comment>\n"

            for fact in comment.get("facts", []):
                fact_id = fact.get("id", "")

                # Store mapping of fact ID to citation number
                if fact_id not in self.original_id_to_new_id:
                    self.original_id_to_new_id[fact_id] = str(self.current_id)
                    self.new_id_to_original_id[str(self.current_id)] = fact_id
                    new_id = self.current_id
                    self.current_id += 1
                else:
                    new_id = int(self.original_id_to_new_id[fact_id])

                # Format fact with citation number
                result += f'    <fact id="{new_id}">\n'
                result += f"      <title>{fact.get('title', '')}</title>\n"
                result += f"      <references>\n"

                for reference in fact.get("references", []):
                    result += f"        <reference>\n"
                    result += f"          <title>{reference.get('title', '')}</title>\n"
                    result += f"          <url>{reference.get('url', '')}</url>\n"
                    result += f"          <description>{reference.get('description', '')}</description>\n"
                    result += f"        </reference>\n"

                result += f"      </references>\n"
                result += f"    </fact>\n"

            result += f"  </comment>\n"

        result += "</issue>"

        # Print the ID mappings for reference
        print("\n[INFO] ID Mappings:")
        print("[DEBUG] Original ID (fact UUID) to New ID:", self.original_id_to_new_id)
        print("[DEBUG] New ID to Original ID (fact UUID):", self.new_id_to_original_id)
        print(f"[DEBUG] Current citation ID counter: {self.current_id}")
        print(f"[DEBUG] Outcome of result is :\n{result}")

        return result

    def add_web_search_fact(self, fact_id: str, title: str) -> int:
        """
        Add a web search fact and assign it a citation number.

        Args:
            fact_id: The UUID of the fact from the API
            title: The title of the fact

        Returns:
            Citation number assigned to this fact
        """
        # Assign the next citation number
        new_id = self.current_id
        citation_id = str(new_id)

        # Store mappings
        self.original_id_to_new_id[fact_id] = citation_id
        self.new_id_to_original_id[citation_id] = fact_id

        # Store the fact details
        self.web_search_facts[fact_id] = {
            "id": fact_id,
            "title": title,
            "citation_id": new_id,
        }

        self.current_id += 1
        return new_id

    def get_facts_list(self) -> List[str]:
        """
        Get the list of fact IDs in order of citation numbers.

        Returns:
            List of fact UUIDs ordered by citation number
        """
        # Create a list of the right size
        facts_list = [""] * self.current_id

        # Fill the list with fact IDs in the correct positions
        for new_id, fact_id in self.new_id_to_original_id.items():
            try:
                index = int(new_id)
                facts_list[index] = fact_id
            except (ValueError, IndexError):
                print(f"[WARNING] Invalid citation ID: {new_id} for fact: {fact_id}")

        return facts_list
