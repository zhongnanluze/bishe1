"""
RAG 核心服务
负责文本分段、Embedding 向量化、向量检索
"""
import os
import re
import asyncio
from typing import List, Dict, Optional

import httpx
from chromadb import PersistentClient
from chromadb.config import Settings

# Chroma 持久化路径
CHROMA_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chroma_data"
)
COLLECTION_NAME = "knowledge_base"

# Embedding API 配置（优先从环境变量读取）
EMBEDDING_API_KEY = (
    os.getenv("ALIYUN_BAILIAN_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("EMBEDDING_API_KEY")
)
EMBEDDING_BASE_URL = (
    os.getenv("ALIYUN_BAILIA_BASE_URL")
    or os.getenv("EMBEDDING_BASE_URL")
    or "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or "text-embedding-v3"
EMBEDDING_BATCH_SIZE = 25  # 每批最大文本数，避免 API 超时


class EmbeddingClient:
    """
    Embedding 客户端
    优先调用远程 Embedding API，无配置时自动回退到本地模型
    """

    def __init__(self):
        self.api_key = EMBEDDING_API_KEY
        self.base_url = EMBEDDING_BASE_URL.rstrip("/")
        self.model = EMBEDDING_MODEL
        self.use_local = not self.api_key

        if self.use_local:
            print("[EmbeddingClient] 未检测到 Embedding API Key，回退到本地模型 SentenceTransformer")
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        else:
            print(f"[EmbeddingClient] 使用 API Embedding: {self.base_url} / {self.model}")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        对文本列表生成 Embedding 向量

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 每个文本对应的向量
        """
        if not texts:
            return []

        if self.use_local:
            return await self._embed_local(texts)

        return await self._embed_api(texts)

    async def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """本地模型生成 embedding"""
        embeddings = await asyncio.to_thread(
            self._local_model.encode, texts, convert_to_numpy=True
        )
        return embeddings.tolist()

    async def _embed_api(self, texts: List[str]) -> List[List[float]]:
        """远程 API 生成 embedding，支持分批"""
        all_embeddings = []

        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.base_url}/embeddings",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={"model": self.model, "input": batch},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                # OpenAI 兼容格式: data[i].embedding
                batch_embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                print(f"[EmbeddingClient] API 调用失败: {e}")
                # API 失败时，如果本地模型已加载，回退到本地
                if not self.use_local:
                    print("[EmbeddingClient] 尝试回退到本地模型...")
                    try:
                        from sentence_transformers import SentenceTransformer
                        self._local_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
                        self.use_local = True
                        # 用本地模型重新生成全部文本的 embedding
                        return await self._embed_local(texts)
                    except Exception as local_err:
                        print(f"[EmbeddingClient] 本地模型回退也失败: {local_err}")
                raise

        return all_embeddings


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
        # 初始化 Embedding 客户端（API 优先，无配置则回退本地）
        self.embed_client = EmbeddingClient()

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

    def _is_dimension_error(self, error_msg: str) -> bool:
        """判断错误是否由向量维度不匹配引起"""
        lower = error_msg.lower()
        return any(k in lower for k in ["dimension", "expecting embedding", "embedding dimension", "size mismatch"])

    async def _recreate_collection(self):
        """删除旧集合并重新创建（用于维度变化等场景）"""
        print("[RAGService] 正在重建向量集合...")
        try:
            await asyncio.to_thread(self.client.delete_collection, COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print("[RAGService] 向量集合重建完成")

    async def add_document(self, doc_id: str, title: str, content: str, category: Optional[str] = None, agent_type: Optional[str] = None):
        """添加文档到向量库"""
        chunks = self._chunk_text(content)
        if not chunks:
            return

        # 生成 embeddings（API 优先，失败回退本地）
        embeddings = await self.embed_client.embed(chunks)

        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{
            "original_id": str(doc_id),
            "title": title,
            "category": category or "",
            "agent_type": agent_type or "",
            "chunk_index": i
        } for i in range(len(chunks))]

        try:
            await asyncio.to_thread(
                self.collection.add,
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas
            )
        except Exception as e:
            if self._is_dimension_error(str(e)):
                print(f"[RAGService] 维度不匹配，自动重建集合并重试添加: {e}")
                await self._recreate_collection()
                await asyncio.to_thread(
                    self.collection.add,
                    ids=ids,
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
            else:
                raise

    async def search(self, query: str, top_k: int = 3, agent_type: Optional[str] = None) -> List[Dict]:
        """语义搜索
        
        Args:
            query: 查询语句
            top_k: 返回结果数量
            agent_type: 按智能体类型过滤（可选）
        """
        if not query or not query.strip():
            return []

        query_embedding = await self.embed_client.embed([query])

        # 构建过滤条件
        where_filter = None
        if agent_type:
            where_filter = {"agent_type": agent_type}

        try:
            results = await asyncio.to_thread(
                self.collection.query,
                query_embeddings=query_embedding,
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            if self._is_dimension_error(str(e)):
                print(f"[RAGService] 维度不匹配，自动重建集合并重试查询: {e}")
                await self._recreate_collection()
                results = await asyncio.to_thread(
                    self.collection.query,
                    query_embeddings=query_embedding,
                    n_results=top_k,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                raise

        output = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i]
                output.append({
                    "content": results["documents"][0][i],
                    "title": results["metadatas"][0][i].get("title", ""),
                    "category": results["metadatas"][0][i].get("category", ""),
                    "agent_type": results["metadatas"][0][i].get("agent_type", ""),
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
                category=doc.get("category"),
                agent_type=doc.get("agent_type")
            )
