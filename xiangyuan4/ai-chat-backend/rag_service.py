"""
RAG 核心服务
负责文本分段、Embedding 向量化、向量检索
"""
import os
import re
import asyncio
from typing import List, Dict, Optional

from chromadb import PersistentClient
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Chroma 持久化路径
CHROMA_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chroma_data"
)
COLLECTION_NAME = "knowledge_base"


class RAGService:
    """RAG 服务（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        os.makedirs(CHROMA_DB_PATH, exist_ok=True)

        self.client = PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        # 加载 Embedding 模型（首次会自动下载到本地缓存）
        self.model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

    def _chunk_text(self, text: str, max_length: int = 512, overlap: int = 50) -> List[str]:
        """
        文本分段

        策略：
        1. 先按段落（\n\n）分割
        2. 段落过长时按句子切分
        3. 句子合并成 chunk，每段不超过 max_length
        4. 相邻 chunk 重叠 overlap 字符
        """
        if not text:
            return []

        text = text.strip()
        if len(text) <= max_length:
            return [text]

        # 按段落分割
        raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        paragraphs = []
        for p in raw_paragraphs:
            if len(p) <= max_length:
                paragraphs.append(p)
            else:
                # 按句子分割（保留分隔符）
                parts = re.split(r'([。！？.!?])', p)
                merged = []
                i = 0
                while i < len(parts):
                    if i + 1 < len(parts) and parts[i + 1] in '。！？.!?':
                        merged.append(parts[i] + parts[i + 1])
                        i += 2
                    else:
                        if parts[i].strip():
                            merged.append(parts[i])
                        i += 1

                # 合并成 chunks
                current = ""
                for s in merged:
                    if len(current) + len(s) <= max_length:
                        current += s
                    else:
                        if current.strip():
                            paragraphs.append(current.strip())
                        current = s
                if current.strip():
                    paragraphs.append(current.strip())

        # 添加重叠
        if overlap > 0 and len(paragraphs) > 1:
            final_chunks = []
            for i, chunk in enumerate(paragraphs):
                if i == 0:
                    final_chunks.append(chunk)
                else:
                    prev_tail = paragraphs[i - 1][-overlap:] if len(paragraphs[i - 1]) > overlap else paragraphs[i - 1]
                    final_chunks.append(prev_tail + chunk)
            paragraphs = final_chunks

        return [c for c in paragraphs if c.strip()]

    async def add_document(self, doc_id: str, title: str, content: str, category: Optional[str] = None):
        """添加文档到向量库"""
        chunks = self._chunk_text(content)
        if not chunks:
            return

        # 批量生成 embeddings（在线程池中执行，避免阻塞事件循环）
        embeddings = await asyncio.to_thread(self.model.encode, chunks, convert_to_numpy=True)
        embeddings = embeddings.tolist()

        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{
            "original_id": str(doc_id),
            "title": title,
            "category": category or "",
            "chunk_index": i
        } for i in range(len(chunks))]

        await asyncio.to_thread(
            self.collection.add,
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

    async def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """语义搜索"""
        if not query or not query.strip():
            return []

        query_embedding = await asyncio.to_thread(
            self.model.encode, [query], convert_to_numpy=True
        )
        query_embedding = query_embedding.tolist()

        results = await asyncio.to_thread(
            self.collection.query,
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        output = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i]
                output.append({
                    "content": results["documents"][0][i],
                    "title": results["metadatas"][0][i].get("title", ""),
                    "category": results["metadatas"][0][i].get("category", ""),
                    "distance": distance,
                    "similarity": 1 - distance
                })
        return output

    async def delete_document(self, doc_id: str):
        """删除文档的所有 chunks"""
        await asyncio.to_thread(
            self.collection.delete,
            where={"original_id": str(doc_id)}
        )

    async def count_documents(self) -> int:
        """获取向量库中文档片段数量"""
        result = await asyncio.to_thread(self.collection.count)
        return result

    async def rebuild(self, documents: List[Dict]):
        """
        全量重建索引

        Args:
            documents: List[Dict]，每个 dict 包含 id, title, content, category
        """
        # 删除旧集合
        try:
            await asyncio.to_thread(self.client.delete_collection, COLLECTION_NAME)
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        for doc in documents:
            await self.add_document(
                doc_id=str(doc["id"]),
                title=doc.get("title", ""),
                content=doc.get("content", ""),
                category=doc.get("category")
            )
