from typing import Dict, List, Any, Tuple
import json
import os
import re
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma, FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain import hub
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import chain

# Constants
CHUNK_SIZE: int = 100
CHUNK_OVERLAP: int = 10

# Global variables
all_passage_id: Dict[str, Any] = {}
original_id_to_new_id: Dict[str, str] = {}
new_id_to_original_id: Dict[str, str] = {}


def get_project_paths() -> Tuple[str, str]:
    """Get current directory and project root paths."""
    current_dir: str = os.getcwd()
    project_root: str = os.path.join(current_dir, os.pardir)
    return current_dir, project_root


def load_json_data(project_root: str) -> Dict[str, Any]:
    """Load JSON data from file."""
    json_file_path: str = os.path.join(project_root, 'data', 'example_api_data.json')
    with open(json_file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def process_documents(data: Dict[str, Any]) -> List[Document]:
    """Process documents and create splits."""
    documents: List[Document] = []
    now_id: int = 1
    
    for comment in data["content"]:
        for fact in comment["facts"]:
            for reference in fact["references"]:
                if reference["id"] not in original_id_to_new_id:
                    text: str = f"{reference['title']}。{reference['description']}"
                    document = Document(
                        page_content=text,
                        metadata={
                            "original_id": reference["id"],
                            "new_id": now_id,
                            "type": "html_metadata",
                        }
                    )
                    documents.append(document)
                    original_id_to_new_id[reference["id"]] = str(now_id)
                    new_id_to_original_id[str(now_id)] = reference["id"]
                    now_id += 1

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    return text_splitter.split_documents(documents)


def get_user_message_imply(
    llm: ChatOpenAI,
    user_message: str,
    html_metadata: str
) -> Any:
    """Get implied message from user input."""
    prompt = PromptTemplate.from_template(
        '''
        你是一個能夠閱讀文章描述與使用者留言的助手。請根據下面的「文章描述」與「使用者評論」，
        推斷這篇文章中尚未明確提到但很可能被涵蓋的內容，並寫成簡潔的摘要。

        文章描述:
        {html_metadata}

        使用者評論:
        {user_message}

        請將可能被涵蓋的內容以一段話敘述出來，並用中文回答。
        '''
    )
    result = prompt | llm
    return result.invoke({
        "user_message": user_message,
        "html_metadata": html_metadata
    })


def process_message(
    data: Dict[str, Any],
    llm: ChatOpenAI
) -> List[Document]:
    """Process user messages and create document splits."""
    documents: List[Document] = []
    
    for comment in data["content"]:
        user_message: str = comment["content"]
        for fact in comment["facts"]:
            for reference in fact["references"]:
                html_metadata: str = f"{reference['title']}。{reference['description']}"
                user_message_imply = get_user_message_imply(llm, user_message, html_metadata)
                
                document = Document(
                    page_content=user_message_imply.content,
                    metadata={
                        "original_id": reference["id"],
                        "new_id": original_id_to_new_id[reference["id"]],
                        "type": "user_message_imply",
                    }
                )
                documents.append(document)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    return text_splitter.split_documents(documents)


@chain
def retriever(query: str, vector_store: FAISS) -> List[Document]:
    """Retrieve similar documents with relevance scores."""
    docs, scores = zip(*vector_store.similarity_search_with_relevance_scores(query, k=3))
    for doc, score in zip(docs, scores):
        doc.metadata["score"] = score
    return docs


def format_qa_result(final_result: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Format QA results into structured JSON."""
    model_input_json: Dict[str, Any] = {}
    
    for i, qa in enumerate(final_result, 1):
        question_key: str = f"Question_{i}"
        model_input_json[question_key] = {
            "Question": qa['input'],
            "Answer": qa['answer'],
            "cited_passages": {}
        }
        
        for j, context in enumerate(qa['context'], 1):
            model_input_json[question_key]["cited_passages"][f"passage{j}"] = {
                "source_original_id": context.metadata['original_id'],
                "source_new_id": context.metadata['new_id'],
                "type": context.metadata['type']
            }

    return model_input_json


def create_model_input_string(model_input_json: Dict[str, Any]) -> str:
    """Create formatted string from model input JSON."""
    model_input_string: str = ""
    
    for key, value in model_input_json.items():
        model_input_string += f"{key[-1]}. {value['Question']}\n"
        answer: str = f"答: {value['Answer']}"
        
        if answer.endswith("。"):
            answer = answer[:-1]
            
        model_input_string += answer
        
        for context in value['cited_passages']:
            citation_type: str = value['cited_passages'][context]["type"]
            new_id: str = value['cited_passages'][context]['source_new_id']
            
            if citation_type == "user_message_imply":
                model_input_string += f"[U{new_id}]"
            elif citation_type == "html_metadata":
                model_input_string += f"[{new_id}]"
                
        model_input_string += "\n"
        
    return model_input_string


def save_output_to_json(final_output: Dict[str, Any], filename: str) -> None:
    """Save final output to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)


def main() -> None:
    """Main execution function."""
    # Initialize paths and load data
    current_dir, project_root = get_project_paths()
    data = load_json_data(project_root)
    
    # Load environment variables
    dotenv_path: str = os.path.join(project_root, 'config', '.env')
    load_dotenv(dotenv_path)
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    # Process documents
    all_splits = process_documents(data)
    all_message_splits = process_message(data, llm)
    all_splits.extend(all_message_splits)
    
    # Initialize embeddings and vector store
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vector_store = FAISS.from_documents(all_splits, embeddings)
    
    # Set up retrieval chain
    retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )
    
    combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
    rag_chain = create_retrieval_chain(retriever, combine_docs_chain)
    
    # Process questions
    questions: List[str] = [
        "黃牛票",
        "2023年?",
        "這個事件的結果是?",
        "這個事件的影響是?",
        "這個事件的意義是?"
    ]
    
    final_result: List[Dict[str, Any]] = []
    for question in questions:
        result = rag_chain.invoke({"input": question})
        final_result.append(result)
    
    # Format and save results
    model_input_json = format_qa_result(final_result)
    model_input_string = create_model_input_string(model_input_json)
    
    # Load few-shot example
    file_path: str = os.path.join(project_root, 'data', 'few_shot_example.txt')
    with open(file_path, 'r', encoding="utf-8") as file:
        few_shot_example: str = file.read()
    
    # Create final prompt and get response
    prompt = PromptTemplate.from_template(
        '''
        您是一位專業的文章撰寫者，請根據以下的撰寫要求，撰寫一份完整且連貫的摘要報告。
    撰寫要求：
    1. 內容結構：
    - 按照時間順序或邏輯順序組織內容
    - 確保段落之間的轉折自然
    - 使用適當的連接詞來增加文章流暢度
    - 除了摘要內容之外不要有任何多餘的文字
    - 在輸出的內容中不要有任何除了摘要內容和引用標註之外的描述性文字
    - 不可以用列點的方式來輸出
    - 必須嚴格遵守在結束一個句子之後有兩個換行符號

    2. 引用格式：
    - 每個論述都必須標註來源：[n]
    - 如果一個段落包含多個來源的內容，需分別標註

    3. 寫作風格：
    - 使用客觀、專業的語氣
    - 避免重複QA中的問題形式
    - 將問答轉化為敘事性的描述

    4. 內容完整性：
    - 確保涵蓋所有QA中的重要信息
    - 適當整合相關信息，避免過度分散
    - 在不同觀點間取得平衡

    以下是範例問答輸入和範例摘要示例輸出包含一系列的問題和答案：
    {examples}

    以下是一個你需要處理的問答集，你要對這個問答及做摘要其中包含一系列的問題和答案：
    {input}

    請以以下格式回答：
    ###輸出開始###
    [你的回答]
    ###輸出結束###
    '''
    )
    
    answer_to_abstract_chain = prompt | llm
    result = answer_to_abstract_chain.invoke({
        "input": model_input_string,
        "examples": few_shot_example
    })
    
    # Process and save final output
    result_content: str = result.content[11:-11]
    final_output: Dict[str, Any] = {
        "Summary": result_content,
        "Citations": {
            str(citation): new_id_to_original_id[str(citation)]
            for citation in sorted(set(
                map(int, re.findall(r'\[(\d+)\]', result_content) +
                    re.findall(r'\[U(\d+)\]', result_content))
            ))
        }
    }
    
    save_output_to_json(final_output, 'summary_output.json')


if __name__ == "__main__":
    main()