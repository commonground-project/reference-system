from typing import Dict, List, Any, Tuple
import json
import os
import re
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from utils import api_func, prompt_template
from utils.format_data import DataProcessor

class IssueNewsGenerator:
    def __init__(self, issue: Dict) -> None:
        self.original_id_to_new_id: Dict[str, str] = {}
        self.new_id_to_original_id: Dict[str, str] = {}
        self.current_dir, self.project_root = self._get_project_paths()
        self.issue_id = issue['id']
        self.title = issue['title']
        self.viewspoints = self._load_viewspoints_from_issue_id()
        self._initialize_llm()

    def _get_project_paths(self) -> Tuple[str, str]:
        """Get current directory and project root paths."""
        # print(os.getcwd())
        current_dir: str = os.getcwd()
        project_root: str = os.path.join(current_dir, os.pardir)
        return current_dir, project_root

    def _load_viewspoints_from_issue_id(self) -> Dict[str, List]:
        """Load JSON data from API."""
        # 獲得在某個議題底下的所有 viewpoints
        return api_func.load_viewspoints_from_issue_id(self.issue_id)

    def _initialize_llm(self) -> None:
        """Initialize the language model and load environment variables."""
        dotenv_path: str = os.path.join(self.current_dir, 'config', '.env')
        load_dotenv(dotenv_path)
        self.llm = ChatOpenAI(model="gpt-4o-mini")

    def _load_few_shot_example(self) -> str:
        """Load few-shot example from file."""
        file_path: str = os.path.join(self.current_dir, 'data', 'few_shot_example.txt')
        with open(file_path, 'r', encoding="utf-8") as file:
            return file.read()

    def _put_refence_result_to_platform(self) -> None:
        """Put the result of the news generation to the platform."""
        return api_func.put_reference_result_to_platform(self.issue_id, self.result, self.title, jwt_token=os.getenv('JWT_TOKEN'))

    def get_input_data(self) -> str:
        """Format data for model input."""
        processor = DataProcessor(self.viewspoints)
        self.formatted_data = processor.format_html_metadata()
        self.original_id_to_new_id = processor.original_id_to_new_id
        self.new_id_to_original_id = processor.new_id_to_original_id
        return self.formatted_data

    def generate_news(self) -> Dict[str, Any]:
        """Generate news article and process the output."""
        model_input_string = self.get_input_data()
        few_shot_example = self._load_few_shot_example()
        
        template = prompt_template.create_prompt_template()
        chain = template | self.llm
        
        result = chain.invoke({
            "input_data": model_input_string,
            "examples": few_shot_example
        })

        # Process result
        # print(result.content)
        result_content: str = result.content[11:-11]
        
        result_content = result_content.replace("\n", "")
        
        # Create final output
        final_output: Dict[str, Any] = {
            "Summary": result_content,
            "Citations": {
                str(citation): self.new_id_to_original_id[str(citation)]
                for citation in sorted(set(
                    map(int, re.findall(r'\((\d+)\)', result_content) +
                        re.findall(r'\(U(\d+)\)', result_content))
                ))
            }
        }
        self.result = final_output
        return final_output

def main():
    """Main function to run the news generation process."""
    # 先取得 issue 的所有 id

    # all_issue_ids = api_func.get_all_issue_ids()
    all_issue = api_func.get_all_issue()
    for issue in all_issue:
        news_generator = IssueNewsGenerator(issue)
        news_generator.generate_news()
        print("Generated News Article:")
        print(news_generator.result["Summary"])
        print("\n")
        print("Citations:", news_generator.result["Citations"])
        print("\n")
        print("Issue_id: ", news_generator.issue_id)
        news_generator._put_refence_result_to_platform()


if __name__ == "__main__":
    main()