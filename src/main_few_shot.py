from typing import Dict, List, Any, Tuple
import json
import os
import re
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils import api_func
class NewsGenerator:
    def __init__(self, issue_id: str) -> None:
        self.original_id_to_new_id: Dict[str, str] = {}
        self.new_id_to_original_id: Dict[str, str] = {}
        self.current_dir, self.project_root = self._get_project_paths()
        self.data = self._load_viewspoints_from_issue_id(issue_id)
        self._initialize_llm()

    def _get_project_paths(self) -> Tuple[str, str]:
        """Get current directory and project root paths."""
        # print(os.getcwd())
        current_dir: str = os.getcwd()
        project_root: str = os.path.join(current_dir, os.pardir)
        return current_dir, project_root

    def _load_viewspoints_from_issue_id(self, issue_id) -> Dict[str, List]:
        """Load JSON data from API."""
        # 獲得在某個議題底下的所有 viewpoints
        return api_func.load_viewspoints_from_issue_id(issue_id)

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

    def process_json(self) -> str:
        """Format data for model input."""
        result: str = ""
        now_id: int = 1
        for comment in self.data["content"]:
            fact_num: int = 1
            for fact in comment["facts"]:
                result += f"事實{fact_num}:\n\n"
                for reference in fact["references"]:
                    if reference["id"] not in self.original_id_to_new_id:
                        # TODO {reference['description']} 在後端 api 更新後新增 
                        text: str = f"{reference['title']}。"
                        result += f"參考資料:\n{text}[{now_id}]\n\n"
                        self.original_id_to_new_id[reference["id"]] = str(now_id)
                        self.new_id_to_original_id[str(now_id)] = reference["id"]
                        now_id += 1
                fact_num += 1
        
        return result

    def create_prompt_template(self) -> ChatPromptTemplate:
        """Create the chat prompt template."""
        return ChatPromptTemplate([
            ("system", '''您是一位經驗豐富的新聞記者，負責根據引用的事實資訊撰寫客觀的新聞文章。您的職責是：
1. 使用引用的事實撰寫全面的新聞報導
2. 運用新聞寫作技巧自然地連接資訊（何人、何事、何時、何地、為何、如何）
3. 保持嚴格的事實準確性 - 不推測或添加超出引述範圍的細節
4. 在保留引述中所有重要細節的同時，讓文章結構具有邏輯性
5. 將輸出內容置於 ###輸出開始### 和 ###輸出結束### 標記之間
指導方針：
* 僅使用編號引述明確支持的資訊
* 使用自然的過渡同時保持準確性
* 應用標準新聞寫作風格和結構
* 包含引述中的所有相關事實
* 避免任何推測或未經支持的細節
這裡是一些範例參考撰寫方式，請學習這些範例來撰寫你的新聞報導
{examples}

請以以下格式回答：
###輸出開始###
[你的回答]
###輸出結束###'''),
            ("human", '''請根據以下引述資訊撰寫新聞文章：
{input_data}'''),
        ])

    def generate_news(self) -> Dict[str, Any]:
        """Generate news article and process the output."""
        model_input_string = self.process_json()
        few_shot_example = self._load_few_shot_example()
        
        template = self.create_prompt_template()
        chain = template | self.llm
        
        result = chain.invoke({
            "input_data": model_input_string,
            "examples": few_shot_example
        })

        # Process result
        result_content: str = result.content[11:-11]
        result_content = result_content.replace("\n", "")
        
        # Create final output
        final_output: Dict[str, Any] = {
            "Summary": result_content,
            "Citations": {
                str(citation): self.new_id_to_original_id[str(citation)]
                for citation in sorted(set(
                    map(int, re.findall(r'\[(\d+)\]', result_content) +
                        re.findall(r'\[U(\d+)\]', result_content))
                ))
            }
        }
        
        return final_output

def main():
    """Main function to run the news generation process."""
    # 先取得 issue 的所有 id

    all_issue_ids = api_func.get_all_issue_ids()
    for issue_id in all_issue_ids:
        news_generator = NewsGenerator(issue_id)
        
        result = news_generator.generate_news()
        result["Issue_id"] = issue_id
        print("Generated News Article:")
        print(result["Summary"])
        print("\nCitations:")
        print(result["Citations"])
        print("\n")
        print("Issue_id: ", result["Issue_id"])


if __name__ == "__main__":
    main()