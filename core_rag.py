import os
import json
import asyncio
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

class BaseRAGManager:
    """
    Independent RAG Manager for viewing and searching established SillyTavern FAISS indices.
    Extracts cross-universe logic, re-ranking basics, and intent query logic without large project overhead.
    """
    def __init__(self, data_root: str):
        self.data_root = data_root
        self.vectorstore_dir = os.path.join(data_root, "vectorstore", "st_memory")
        self.chunks_dir = os.path.join(data_root, "debug", "chunks")
        
        # Adjust embedding model initialization as needed for your specific env
        self.embedder = HuggingFaceEmbeddings(model_name="BAAI/bge-large-zh-v1.5", model_kwargs={'device': 'cpu'})
        
        self.indices: Dict[str, FAISS] = {}

    def load_index(self, character_name: str, world_line: Optional[str] = None) -> Optional[FAISS]:
        import re
        safe_name = re.sub(r'[^\w\u4e00-\u9fff \-_]', '', character_name).strip()
        filename = f"{safe_name}.index"
        if world_line:
            safe_world = re.sub(r'[^\w\u4e00-\u9fff \-_]', '', world_line).strip()
            filename = f"{safe_name}_{safe_world}.index"
        
        if not filename or filename.startswith("_") or filename == ".index":
            filename = "default_char.index"
            
        index_path = os.path.join(self.vectorstore_dir, filename)

        if not os.path.exists(index_path):
            return None
        
        if index_path in self.indices:
            return self.indices[index_path]
            
        try:
            vectorstore = FAISS.load_local(
                folder_path=index_path,
                embeddings=self.embedder,
                allow_dangerous_deserialization=True
            )
            self.indices[index_path] = vectorstore
            return vectorstore
        except Exception as e:
            return None

    def search_verse(self, vs: FAISS, query: str, k: int) -> List[Document]:
        return vs.similarity_search_with_relevance_scores(query, k=k)
