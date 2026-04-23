"""
Fix database schema: add agent_type column to knowledge_base table
and clean old vector DB (metadata structure changed)
"""
import asyncio
import shutil
import os
from sqlalchemy import text
from database import engine

async def fix_database():
    """Add agent_type column"""
    try:
        async with engine.begin() as conn:
            # Check if column exists
            result = await conn.execute(text("SHOW COLUMNS FROM knowledge_base LIKE 'agent_type'"))
            if result.fetchone():
                print("[OK] agent_type column already exists")
                return True
            # Add column
            await conn.execute(text(
                "ALTER TABLE knowledge_base ADD COLUMN agent_type VARCHAR(50) NULL COMMENT 'agent type'"
            ))
            print("[OK] Added agent_type column to knowledge_base table")
    except Exception as e:
        print(f"[ERROR] Database fix failed: {e}")
        return False
    return True

def fix_vector_db():
    """Delete old vector DB (metadata structure changed, needs rebuild)"""
    chroma_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_data")
    if os.path.exists(chroma_path):
        try:
            shutil.rmtree(chroma_path)
            print(f"[OK] Cleaned old vector DB: {chroma_path}")
            print("   Will auto-rebuild from MySQL on next backend startup")
        except Exception as e:
            print(f"[WARN] Failed to clean vector DB: {e}")
            print("   Please manually delete chroma_data directory")
    else:
        print("[OK] Vector DB directory not found, no cleanup needed")

if __name__ == "__main__":
    print("=" * 50)
    print("Fixing knowledge base...")
    print("=" * 50)
    
    success = asyncio.run(fix_database())
    
    if success:
        fix_vector_db()
        print("=" * 50)
        print("Fix complete! Please restart the backend.")
        print("=" * 50)
    else:
        print("Fix failed, please check database connection.")
