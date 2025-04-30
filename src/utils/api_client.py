"""
API client for interacting with the backend services.
"""

from typing import Any, Dict, List

import requests


class APIClient:
    """Client for interacting with the backend API."""

    def __init__(self, phase: str = "stage"):
        """
        Initialize the API client.

        Args:
            phase: The deployment phase to use (default: 'stage')
        """
        self.phase = phase
        self.base_url = f"https://{self.phase}.api.commonground.tw/api"

    def get_number_of_total_pages(self) -> int:
        """Get the total number of pages of issues."""
        params = {"sort": "createdAt;asc", "page": 0, "size": 200}
        response = requests.get(f"{self.base_url}/issues", params=params)
        return response.json()["page"]["totalPage"]

    def get_all_issue_ids(self) -> List[str]:
        """Get all issue IDs."""
        total_pages = self.get_number_of_total_pages()
        all_issue_ids = []

        for i in range(total_pages):
            params = {"sort": "createdAt;asc", "page": i, "size": 200}
            response = requests.get(f"{self.base_url}/issues", params=params)

            for issue in response.json()["content"]:
                all_issue_ids.append(issue["id"])

        return all_issue_ids

    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all issues with their metadata."""
        total_pages = self.get_number_of_total_pages()
        all_issues = []

        for i in range(total_pages):
            params = {"sort": "createdAt;asc", "page": i, "size": 200}
            response = requests.get(f"{self.base_url}/issues", params=params)

            for issue in response.json()["content"]:
                all_issues.append(issue)

        return all_issues

    def load_viewpoints_from_issue_id(self, issue_id: str) -> Dict[str, List]:
        """
        Load viewpoints data for a specific issue.

        Args:
            issue_id: The ID of the issue to load viewpoints for

        Returns:
            A dictionary containing the viewpoints data
        """
        params = {"sort": "createdAt;asc", "size": 200, "page": 0}
        url = f"{self.base_url}/issue/{issue_id}/viewpoints"

        response = requests.get(url, params=params)
        total_page = response.json()["page"]["totalPage"]

        contents = {"content": []}
        for i in range(total_page):
            params["page"] = i
            response = requests.get(url, params=params)

            for viewpoint in response.json()["content"]:
                contents["content"].append(viewpoint)

        return contents

    def put_reference_result_to_platform(
        self, issue_id: str, result: Dict[str, Any], title: str, jwt_token: str
    ) -> Dict:
        """
        Update issue with generated insights and facts.

        Args:
            issue_id: The ID of the issue to update
            result: The generated results
            title: The title of the issue
            jwt_token: JWT token for authentication

        Returns:
            The response from the API
        """
        url = f"{self.base_url}/issue/{issue_id}"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }

        facts_list = []
        for fact in result["Citations"]:
            facts_list.append(result["Citations"][fact])

        payload = {
            "title": title,
            "description": "description",
            "insight": result["Summary"],
            "facts": facts_list,
        }

        response = requests.put(url, json=payload, headers=headers)
        print(response.json())

        return response.json()
