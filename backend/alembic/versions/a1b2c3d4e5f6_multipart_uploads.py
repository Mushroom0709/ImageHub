"""multipart_uploads 分片上传登记表

Revision ID: a1b2c3d4e5f6
Revises: 8a3f5d2c1b9e
Create Date: 2026-08-09

分片上传（断点续传）状态持久化：
- batch_id: 前端业务批次 ID
- obs_upload_id: OBS 侧 uploadId
- uploaded_parts: JSONB 已上传分片 [{part_number, etag, size}]
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8a3f5d2c1b9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'multipart_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('batch_id', sa.String(64), server_default='', nullable=False),
        sa.Column('obs_upload_id', sa.String(128), server_default='', nullable=False),
        sa.Column('obs_key', sa.String(500), server_default='', nullable=False),
        sa.Column('file_name', sa.String(500), server_default='', nullable=False),
        sa.Column('file_size', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('content_type', sa.String(100), server_default='', nullable=False),
        sa.Column('asset_type', sa.String(16), server_default='image', nullable=False),
        sa.Column('total_parts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('part_size', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('uploaded_parts', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('status', sa.String(16), server_default='pending', nullable=False),
        sa.Column('error_message', sa.String(500), server_default='', nullable=False),
        sa.Column('top_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_multipart_uploads_batch_id', 'multipart_uploads', ['batch_id'])
    op.create_index('ix_multipart_uploads_status', 'multipart_uploads', ['status'])


def downgrade() -> None:
    op.drop_index('ix_multipart_uploads_status', table_name='multipart_uploads')
    op.drop_index('ix_multipart_uploads_batch_id', table_name='multipart_uploads')
    op.drop_table('multipart_uploads')
