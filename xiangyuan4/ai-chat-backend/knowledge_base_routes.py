"""
知识库路由（RAG 版本）
支持：增删改查 + 语义搜索 + 向量索引管理
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import os
import io

from database import get_db, KnowledgeBaseModel
from rag_service import RAGService, COLLECTION_NAME
from auth_utils import get_current_active_user, get_current_admin_user
from auth_models import CurrentUser

# 文件解析器
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

router = APIRouter(prefix="/api/knowledge-base", tags=["知识库"])

# RAG 服务单例
rag_service = RAGService()


class KnowledgeBaseItemCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None


class KnowledgeBaseItemUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None


class KnowledgeBaseSearchRequest(BaseModel):
    query: str
    top_k: int = 3


# 获取知识库列表
@router.get("")
async def get_knowledge_base(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    try:
        result = await db.execute(
            select(KnowledgeBaseModel).order_by(KnowledgeBaseModel.updated_at.desc())
        )
        items = result.scalars().all()
        return [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "category": item.category,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            }
            for item in items
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库失败: {str(e)}")


# 添加知识库项
@router.post("", status_code=status.HTTP_201_CREATED)
async def add_knowledge_base_item(
    item: KnowledgeBaseItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    try:
        new_item = KnowledgeBaseModel(
            title=item.title,
            content=item.content,
            category=item.category
        )
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)

        # 同步到向量库
        await rag_service.add_document(
            doc_id=str(new_item.id),
            title=new_item.title,
            content=new_item.content,
            category=new_item.category
        )

        return {
            "id": new_item.id,
            "title": new_item.title,
            "content": new_item.content,
            "category": new_item.category,
            "created_at": new_item.created_at.isoformat() if new_item.created_at else None,
            "updated_at": new_item.updated_at.isoformat() if new_item.updated_at else None
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"添加知识库项失败: {str(e)}")


# 更新知识库项
@router.put("/{id}")
async def update_knowledge_base_item(
    id: int,
    item: KnowledgeBaseItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    try:
        result = await db.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == id)
        )
        db_item = result.scalar_one_or_none()

        if not db_item:
            raise HTTPException(status_code=404, detail="知识库项不存在")

        if item.title is not None:
            db_item.title = item.title
        if item.content is not None:
            db_item.content = item.content
        if item.category is not None:
            db_item.category = item.category

        db_item.updated_at = datetime.now()
        await db.commit()
        await db.refresh(db_item)

        # 如果内容或标题变了，重建该文档的向量
        if item.content is not None or item.title is not None:
            await rag_service.delete_document(str(id))
            await rag_service.add_document(
                doc_id=str(db_item.id),
                title=db_item.title,
                content=db_item.content,
                category=db_item.category
            )

        return {
            "id": db_item.id,
            "title": db_item.title,
            "content": db_item.content,
            "category": db_item.category,
            "updated_at": db_item.updated_at.isoformat() if db_item.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新知识库项失败: {str(e)}")


# 删除知识库项
@router.delete("/{id}")
async def delete_knowledge_base_item(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    try:
        result = await db.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == id)
        )
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="知识库项不存在")

        await db.execute(sql_delete(KnowledgeBaseModel).where(KnowledgeBaseModel.id == id))
        await db.commit()

        # 从向量库删除
        await rag_service.delete_document(str(id))

        return {"message": "知识库项删除成功", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除知识库项失败: {str(e)}")


# 语义搜索
@router.post("/search")
async def search_knowledge_base(
    request: KnowledgeBaseSearchRequest,
    current_user: CurrentUser = Depends(get_current_active_user)
):
    try:
        results = await rag_service.search(request.query, top_k=request.top_k)
        return {
            "query": request.query,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# 重建向量索引（管理员）
@router.post("/rebuild")
async def rebuild_knowledge_base_index(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user)
):
    try:
        result = await db.execute(select(KnowledgeBaseModel))
        items = result.scalars().all()

        docs = [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "category": item.category
            }
            for item in items
        ]

        await rag_service.rebuild(docs)

        return {
            "message": "索引重建成功",
            "count": len(docs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")


def _parse_file_content(file: UploadFile, filename: str) -> str:
    """
    根据文件扩展名解析内容
    
    支持：txt, md, pdf, docx
    """
    ext = os.path.splitext(filename)[1].lower()
    content = ""
    
    if ext in ['.txt', '.md', '.markdown']:
        # 纯文本直接读取
        raw = file.file.read()
        # 尝试 UTF-8，失败则用 GBK
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                content = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
    
    elif ext == '.pdf':
        if not PYPDF2_AVAILABLE:
            raise HTTPException(status_code=400, detail="PDF 解析依赖未安装，请联系管理员")
        try:
            reader = PyPDF2.PdfReader(file.file)
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            content = "\n".join(pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF 解析失败: {str(e)}")
    
    elif ext == '.docx':
        if not DOCX_AVAILABLE:
            raise HTTPException(status_code=400, detail="Word 解析依赖未安装，请联系管理员")
        try:
            document = docx.Document(file.file)
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            content = "\n".join(paragraphs)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Word 解析失败: {str(e)}")
    
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式: {ext}。仅支持 txt, md, pdf, docx"
        )
    
    return content.strip()


# 上传文件到知识库
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_base_file(
    file: UploadFile = File(...),
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """
    上传文件到知识库（支持 txt, md, pdf, docx）
    
    - 自动解析文件内容
    - 文件名（去掉扩展名）作为标题
    - 自动写入 MySQL 并向量化为 RAG 可用
    """
    # 校验文件大小（限制 10MB）
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")
    
    # 重置文件指针，供解析器使用
    file.file = io.BytesIO(file_content)
    
    # 解析文件内容
    try:
        content = _parse_file_content(file, file.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")
    
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空或无法提取文本")
    
    # 生成标题：文件名去掉扩展名
    title = os.path.splitext(file.filename)[0]
    
    try:
        # 写入 MySQL
        new_item = KnowledgeBaseModel(
            title=title,
            content=content,
            category=category
        )
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        
        # 同步到向量库
        await rag_service.add_document(
            doc_id=str(new_item.id),
            title=new_item.title,
            content=new_item.content,
            category=new_item.category
        )
        
        return {
            "id": new_item.id,
            "title": new_item.title,
            "content_preview": content[:200] + ("..." if len(content) > 200 else ""),
            "category": new_item.category,
            "filename": file.filename,
            "created_at": new_item.created_at.isoformat() if new_item.created_at else None
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


# 获取向量库状态
@router.get("/status")
async def get_knowledge_base_status(
    current_user: CurrentUser = Depends(get_current_active_user)
):
    try:
        count = await rag_service.count_documents()
        return {
            "vector_count": count,
            "collection": COLLECTION_NAME
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")
