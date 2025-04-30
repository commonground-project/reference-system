"""
Data processor for transforming API data into formatted content for LLM processing.
"""

from typing import Dict


class DataProcessor:
    """Process and format data from the API for LLM consumption."""

    def __init__(self, viewpoints: Dict):
        """
        Initialize the data processor.

        Args:
            viewpoints: The viewpoints data from the API
        """
        self.viewpoints = viewpoints
        self.original_id_to_new_id = {}
        self.new_id_to_original_id = {}

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

        now_id = 1

        for comment in self.viewpoints["content"]:
            result += f"  <comment>\n"
            result += f"    <content>{comment.get('content', '')}</content>\n"
            result += f"    <author>{comment.get('authorName', '')}</author>\n"

            for fact in comment.get("facts", []):
                result += f"    <fact>\n"
                result += f"      <title>{fact.get('title', '')}</title>\n"
                result += f"      <references>\n"

                for reference in fact.get("references", []):
                    if reference["id"] not in self.original_id_to_new_id:
                        # Store mapping of original ID to citation number
                        self.original_id_to_new_id[reference["id"]] = str(now_id)
                        self.new_id_to_original_id[str(now_id)] = reference["id"]

                        # Format reference with citation number
                        result += f'        <reference id="{now_id}">\n'
                        result += (
                            f"          <title>{reference.get('title', '')}</title>\n"
                        )
                        result += f"          <url>{reference.get('url', '')}</url>\n"
                        result += f"          <description>{reference.get('description', '')}</description>\n"
                        result += f"        </reference>\n"

                        now_id += 1

                result += f"      </references>\n"
                result += f"    </fact>\n"

            result += f"  </comment>\n"

        result += "</issue>"
        # Print the ID mappings for reference
        print("\n[INFO] ID Mappings:")
        print("[DEBUG] Original ID to New ID:", self.original_id_to_new_id)
        print("[DEBUG] New ID to Original ID:", self.new_id_to_original_id)
        print(f"[DEBUG] Outcome of result is :\n{result}")

        return result
