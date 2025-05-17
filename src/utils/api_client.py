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
        self.base_url = f"{self.phase}"

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
        self,
        issue_id: str,
        insight_text: str,
        title: str,
        facts_list: List[str],
        jwt_token: str,
    ) -> Dict:
        """
        Update issue with generated insights and facts.

        Args:
            issue_id: The ID of the issue to update
            insight_text: The generated insight text with citations in (num) format
            title: The title of the issue
            facts_list: List of fact IDs referenced in order
            jwt_token: JWT token for authentication

        Returns:
            The response from the API
        """
        url = f"{self.base_url}/internal/issues/{issue_id}/insight"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }

        # Prepare the request payload according to API requirements
        payload = {
            # "title": title,
            "insight": insight_text,
            "facts": facts_list,
            # "description": f" {title}'s description",
        }

        print(f"[INFO] Sending payload to API: {payload}")

        response = requests.put(url, json=payload, headers=headers)
        print(f"[INFO] API Response: {response.status_code}")

        if response.status_code >= 400:
            print(f"[ERROR] API response error: {response.text}")
            return {"error": response.text}

        return response.json()

    def create_fact(self, fact_data: Dict[str, Any], jwt_token: str) -> Dict:
        """
        Create a new fact with references.

        Args:
            fact_data: Dictionary with title and references list
            jwt_token: JWT token for authentication

        Returns:
            The created fact data with ID
        """
        url = f"{self.base_url}/internal/facts"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }

        print(f"[INFO] Creating fact: {fact_data}")
        print(f"[DEBUG] Request URL: {url}")
        print(f"[DEBUG] Request Headers: {headers}")
        print(f"[DEBUG] Request Payload: {fact_data}")

        print("\n===== FACT PAYLOAD DETAILS =====")
        print(f"Payload type: {type(fact_data)}")
        if "title" in fact_data:
            print(f"Title: {fact_data['title']}")
        if "references" in fact_data:
            print(f"References count: {len(fact_data['references'])}")
            for i, ref in enumerate(fact_data["references"]):
                print(f"  Reference {i+1}: {ref}")
        print("================================\n")

        response = requests.post(url, json=fact_data, headers=headers)

        print(f"[DEBUG] Response Status Code: {response.status_code}")
        print(f"[DEBUG] Response Headers: {response.headers}")
        print(f"[DEBUG] Response Body: {response.text}")

        if response.status_code >= 400:
            print(f"[ERROR] Failed to create fact: {response.text}")
            return {"error": response.text}

        print(f"[INFO] Fact created successfully: {response.status_code}")
        return response.json()

    def create_reference(self, url_to_create: str, jwt_token: str) -> Dict:
        """
        Create a new reference without associating it with a fact.

        Args:
            url_to_create: The URL to create a reference for
            jwt_token: JWT token for authentication

        Returns:
            The created reference data if successful, or error information with status code
        """
        api_url = f"{self.base_url}/references"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }

        payload = {"url": url_to_create}

        print(f"[INFO] Creating reference for URL: {url_to_create}")

        response = requests.post(api_url, json=payload, headers=headers)

        result = {}
        result["status_code"] = response.status_code

        if response.status_code >= 400:
            print(f"[ERROR] Failed to create reference: {response.text}")
            result["error"] = response.text
            return result

        print(f"[INFO] Reference created successfully: {response.status_code}")
        result.update(response.json())
        return result

    def check_website(self, url_to_check: str) -> Dict:
        """
        Check website title and icon using the public API.

        Args:
            url_to_check: The URL to check

        Returns:
            Dict with 'title' and 'icon' if successful, or error info
        """
        api_url = f"{self.base_url}/website/check"
        params = {"url": url_to_check}
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json(), "status_code": response.status_code}

    def create_fact_with_url_validation(
        self, fact_title: str, references: List[Dict[str, str]], jwt_token: str
    ) -> Dict:
        """
        Create a new fact with references, but first validate all URLs.

        This method will:
        1. Try to check each URL using the public API
        2. Collect only successfully checked URLs
        3. Create a fact using only the successful references

        Args:
            fact_title: Title for the fact
            references: List of reference dictionaries containing URLs
            jwt_token: JWT token for authentication

        Returns:
            The created fact data with ID if successful, or error information
        """
        print(
            f"[INFO] Attempting to create fact '{fact_title}' with {len(references)} URLs"
        )

        successful_references = []
        for reference in references:
            url = reference.get("url", "")
            if not url:
                print(f"[WARNING] Skipping reference with no URL: {reference}")
                continue

            check_result = self.check_website(url)

            if "error" not in check_result:
                print(f"[INFO] Website check passed for URL: {url}")
                successful_references.append({"url": url})
            else:
                print(
                    f"[WARNING] URL failed website check: {url}, Status: {check_result.get('status_code')}"
                )

        if not successful_references:
            print("[ERROR] No URLs could be successfully validated")
            return {"error": "All URLs failed validation"}

        print(
            f"[INFO] Successfully validated {len(successful_references)} out of {len(references)} URLs"
        )

        fact_data = {"title": fact_title, "references": successful_references}

        return self.create_fact(fact_data, jwt_token)
