#!/usr/bin/env python3
"""创建初始管理员账号"""
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.models.user import User
from app.api.endpoints.auth import hash_password


def create_admin(username: str = "admin", password: str = "admin123"):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"管理员 {username} 已存在")
            return
        user = User(
            username=username,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"✅ 创建管理员 {username} / {password}")
    finally:
        db.close()


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    create_admin(username, password)
