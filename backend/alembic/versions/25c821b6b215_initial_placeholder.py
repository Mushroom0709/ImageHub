"""initial schema placeholder

Revision ID: 25c821b6b215
Revises:
Create Date: 2026-08-08

说明：此文件为占位。最初的 25c821b6b215 迁移文件在多次部署覆盖中丢失，
但数据库已应用该版本（表已存在）。此占位让 alembic revision 链完整，
upgrade 不做任何操作（表结构已在数据库中）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '25c821b6b215'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 表已存在，无需操作
    pass


def downgrade() -> None:
    pass
