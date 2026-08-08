"""add top_categories and top_category_id

Revision ID: 7f2c1a9b3d5e
Revises: 25c821b6b215
Create Date: 2026-08-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7f2c1a9b3d5e'
down_revision: Union[str, None] = '25c821b6b215'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建顶层分类表
    op.create_table(
        'top_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), server_default=''),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('name', name='uq_top_categories_name'),
    )

    # assets 表加 top_category_id
    op.add_column('assets', sa.Column('top_category_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index('ix_assets_top_category_id', 'assets', ['top_category_id'])


def downgrade() -> None:
    op.drop_index('ix_assets_top_category_id', table_name='assets')
    op.drop_column('assets', 'top_category_id')
    op.drop_table('top_categories')
