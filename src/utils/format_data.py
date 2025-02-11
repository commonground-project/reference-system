from typing import Dict

class DataProcessor:
    def __init__(self, viewspoints: Dict):
        self.viewspoints = viewspoints
        self.original_id_to_new_id = {}
        self.new_id_to_original_id = {}
        
    def format_html_metadata(self) -> str:
        """Format data for model input."""
        result: str = ""
        now_id: int = 1
        for comment in self.viewspoints["content"]:
            fact_num: int = 1
            for fact in comment["facts"]:
                result += f"事實{fact_num}:{fact['title']}\n\n"
                for reference in fact["references"]:
                    if reference["id"] not in self.original_id_to_new_id:
                        text: str = f"{reference['title']}。"
                        result += f"參考資料:\n{text}[{now_id}]\n\n"
                        self.original_id_to_new_id[reference["id"]] = str(now_id)
                        self.new_id_to_original_id[str(now_id)] = reference["id"]
                        now_id += 1
                fact_num += 1
        return result
    def foramt_user_message_data(self) -> Dict:
        pass