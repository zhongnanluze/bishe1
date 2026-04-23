"""
数据库初始化脚本
安全创建所有表（不删除已有数据和表）
对于已有表，会跳过；对于缺失的表/字段，需要手动处理
"""
import asyncio
from database import engine, Base
from sqlalchemy import text

async def init_database():
    """创建所有缺失的表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] 数据库表检查/创建完成")

async def fix_knowledge_base_column():
    """为 knowledge_base 表添加 agent_type 字段（如果不存在）"""
    async with engine.begin() as conn:
        result = await conn.execute(text("SHOW COLUMNS FROM knowledge_base LIKE 'agent_type'"))
        if not result.fetchone():
            await conn.execute(text(
                "ALTER TABLE knowledge_base ADD COLUMN agent_type VARCHAR(50) NULL COMMENT 'agent type'"
            ))
            print("[OK] 已为 knowledge_base 表添加 agent_type 字段")
        else:
            print("[OK] knowledge_base.agent_type 字段已存在")

async def main():
    print("=" * 50)
    print("初始化数据库...")
    print("=" * 50)
    
    await init_database()
    await fix_knowledge_base_column()
    
    # 正确释放连接池
    await engine.dispose()
    
    print("=" * 50)
    print("完成！请重新启动后端服务。")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
