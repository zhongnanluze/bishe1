from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, KnowledgeBaseModel
from datetime import datetime
from pydantic import BaseModel
from auth_utils import get_current_user

# 表创建由 main.py 中的 init_db() 函数处理

# Pydantic 模型
class KnowledgeBaseItem(BaseModel):
    title: str
    content: str
    category: str = None

class KnowledgeBaseItemResponse(KnowledgeBaseItem):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])

# 获取知识库列表
@router.get("", response_model=list[KnowledgeBaseItemResponse])
async def get_knowledge_base(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    try:
        items = db.query(KnowledgeBaseModel).all()
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库失败: {str(e)}")

# 添加知识库项
@router.post("", response_model=KnowledgeBaseItemResponse)
async def add_knowledge_base_item(
    item: KnowledgeBaseItem,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        new_item = KnowledgeBaseModel(
            title=item.title,
            content=item.content,
            category=item.category
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"添加知识库项失败: {str(e)}")

# 删除知识库项
@router.delete("/{id}")
async def delete_knowledge_base_item(
    id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        item = db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.id == id).first()
        if not item:
            raise HTTPException(status_code=404, detail="知识库项不存在")
        db.delete(item)
        db.commit()
        return {"message": "知识库项删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除知识库项失败: {str(e)}")
