"""starred(bool) -> star_level(int 0-5)

Revision ID: 8a3f5d2c1b9e
Revises: 7f2c1a9b3d5e
Create Date: 2026-08-08

原 starred 布尔字段升级为 star_level 整数 0-5。
starred=True 的旧数据 → star_level=3（默认三星）
starred=False 的旧数据 → star_level=0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8a3f5d2c1b9e'
down_revision: Union[str, None] = '7f2c1a9b3d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 新增 star_level 列
    op.add_column('assets', sa.Column('star_level', sa.Integer(), server_default='0', nullable=False))

    # 迁移旧数据：starred=True -> star_level=3
    op.execute("UPDATE assets SET star_level = 3 WHERE starred = true")

    # 删除旧列和索引
    op.drop_index('ix_assets_starred', table_name='assets')
    op.drop_column('assets', 'starred')

    # 新索引
    op.create_index('ix_assets_star_level', 'assets', ['star_level'])


def downgrade() -> None:
    op.add_column('assets', sa.Column('starred', sa.Boolean(), server_default='false', nullable=False))
    op.execute("UPDATE assets SET starred = true WHERE star_level > 0")
    op.drop_index('ix_assets_star_level', table_name='assets')
    op.drop_column('assets', 'star_level')
    op.create_index('ix_assets_starred', 'assets', ['starred'])
