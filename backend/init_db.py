#!/usr/bin/env python3
"""初始化数据库 + 种子数据"""
import sys

from app.core.database import engine, SessionLocal, Base
from app.models import *  # noqa: F403
from app.services.tag_service import seed_tags


def init_db():
    # 创建所有表（如果不用 alembic 的话）
    # Base.metadata.create_all(bind=engine)
    pass


def init_seed():
    db = SessionLocal()
    try:
        count = seed_tags(db)
        print(f"导入种子标签: {count} 个")
    finally:
        db.close()


if __name__ == "__main__":
    if "seed" in sys.argv:
        init_seed()
    else:
        init_db()
        print("数据库初始化完成")
