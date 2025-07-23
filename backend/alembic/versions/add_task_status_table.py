"""Add task_status table for async task tracking

Revision ID: task_status_001
Revises: 0455658f73d2
Create Date: 2025-07-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'task_status_001'
down_revision = '0455658f73d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create task_status table
    op.create_table('task_status',
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'SUCCESS', 'FAILURE', 'RETRY', name='taskstatusenum'), nullable=False),
        sa.Column('progress', sa.Float(), nullable=False),
        sa.Column('file_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('result_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('estimated_duration', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
        sa.ForeignKeyConstraint(['result_id'], ['analysis_results.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('task_id')
    )
    
    # Create indexes for performance
    op.create_index('idx_task_status_lookup', 'task_status', ['task_id', 'user_id'])
    op.create_index('idx_task_status_user', 'task_status', ['user_id', 'created_at'])
    op.create_index('idx_task_status_file', 'task_status', ['file_id'])
    op.create_index('idx_task_status_status', 'task_status', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_task_status_status', table_name='task_status')
    op.drop_index('idx_task_status_file', table_name='task_status')
    op.drop_index('idx_task_status_user', table_name='task_status')
    op.drop_index('idx_task_status_lookup', table_name='task_status')
    
    # Drop table
    op.drop_table('task_status')
    
    # Drop enum type
    sa.Enum(name='taskstatusenum').drop(op.get_bind())