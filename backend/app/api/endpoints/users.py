"""用户管理 API 端点（仅管理员）"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.models.user import User
from app.api.endpoints.auth import get_current_user, hash_password

router = APIRouter(tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@router.get("")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """用户列表"""
    users = db.query(User).order_by(User.created_at).all()
    return ok({
        "items": [
            {
                "id": str(u.id),
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": len(users),
    })


@router.post("")
def create_user(data: CreateUserRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """创建用户"""
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok({
        "id": str(user.id),
        "username": user.username,
        "role": user.role,
    })


@router.delete("/{user_id}")
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """禁用用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    user.is_active = False
    db.commit()
    return ok({"ok": True})
