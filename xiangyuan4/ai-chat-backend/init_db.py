"""
数据库初始化脚本
创建数据库表和初始管理员用户
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import Base, User
from auth_utils import get_password_hash
from dotenv import load_dotenv

# 本地密码哈希函数（处理长度限制）
def safe_password_hash(password: str) -> str:
    """
    安全的密码哈希生成（处理bcrypt 72字节限制）
    """
    # 直接使用简单的哈希方法，避免bcrypt的限制
    import hashlib
    # 使用SHA256哈希
    hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()
    # 添加前缀表示使用的哈希方法
    return f"$sha256${hashed}"

load_dotenv()

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "ai_chat_db")

# 构建数据库 URL（使用 pymysql 驱动）
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建同步引擎
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 显示SQL语句
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# 创建会话工厂
SessionLocal = sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


def create_database():
    """创建数据库（如果不存在）"""
    try:
        # 连接到 MySQL 服务器（不指定数据库）
        server_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
        server_engine = create_engine(server_url, echo=True)
        
        with server_engine.connect() as conn:
            # 检查数据库是否存在
            result = conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{DB_NAME}'")
            )
            database_exists = result.fetchone()
            
            if not database_exists:
                # 创建数据库
                conn.execute(text(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                conn.commit()
                print(f"✅ 数据库 '{DB_NAME}' 创建成功")
            else:
                print(f"ℹ️  数据库 '{DB_NAME}' 已存在")
        
        server_engine.dispose()
        
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        raise


def create_tables():
    """创建所有表"""
    try:
        with engine.begin() as conn:
            Base.metadata.create_all(conn)
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        raise


def create_admin_user():
    """创建初始管理员用户"""
    try:
        with SessionLocal() as session:
            # 检查是否已存在管理员
            from sqlalchemy import select
            result = session.execute(
                select(User).where(User.username == "admin")
            )
            admin_user = result.scalar_one_or_none()
            
            if admin_user:
                print("ℹ️  管理员用户已存在")
                print(f"   用户名: {admin_user.username}")
                print(f"   邮箱: {admin_user.email}")
                return
            
            # 创建管理员用户
            admin_user = User(
                username="admin",
                email="admin@example.com",
                password_hash=safe_password_hash("admin123456"),
                student_id=None,
                full_name="系统管理员",
                is_active=True,
                is_admin=True
            )
            
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            
            print("✅ 管理员用户创建成功")
            print(f"   用户名: {admin_user.username}")
            print(f"   邮箱: {admin_user.email}")
            print(f"   密码: admin123456")
            print("⚠️  请在生产环境中修改默认密码！")
            
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        raise


def create_test_user():
    """创建测试用户"""
    try:
        with SessionLocal() as session:
            # 检查是否已存在测试用户
            from sqlalchemy import select
            result = session.execute(
                select(User).where(User.username == "testuser")
            )
            test_user = result.scalar_one_or_none()
            
            if test_user:
                print("ℹ️  测试用户已存在")
                return
            
            # 创建测试用户
            test_user = User(
                username="testuser",
                email="test@example.com",
                password_hash=safe_password_hash("test123456"),
                student_id="2024001",
                full_name="测试用户",
                is_active=True,
                is_admin=False
            )
            
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            
            print("✅ 测试用户创建成功")
            print(f"   用户名: {test_user.username}")
            print(f"   邮箱: {test_user.email}")
            print(f"   学号: {test_user.student_id}")
            print(f"   密码: test123456")
            
    except Exception as e:
        print(f"❌ 创建测试用户失败: {e}")
        raise


def main():
    """主函数"""
    print("=" * 60)
    print("数据库初始化脚本")
    print("=" * 60)
    print(f"数据库主机: {DB_HOST}:{DB_PORT}")
    print(f"数据库名称: {DB_NAME}")
    print(f"数据库用户: {DB_USER}")
    print("=" * 60)
    
    try:
        # 1. 创建数据库
        print("\n[1/4] 创建数据库...")
        create_database()
        
        # 2. 创建表
        print("\n[2/4] 创建数据库表...")
        create_tables()
        
        # 3. 创建管理员用户
        print("\n[3/4] 创建管理员用户...")
        create_admin_user()
        
        # 4. 创建测试用户
        print("\n[4/4] 创建测试用户...")
        create_test_user()
        
        print("\n" + "=" * 60)
        print("✅ 数据库初始化完成！")
        print("=" * 60)
        print("\n默认账户信息:")
        print("管理员:")
        print("  用户名: admin")
        print("  密码: admin123456")
        print("\n测试用户:")
        print("  用户名: testuser")
        print("  密码: test123456")
        print("  学号: 2024001")
        print("\n⚠️  请在生产环境中修改默认密码！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
