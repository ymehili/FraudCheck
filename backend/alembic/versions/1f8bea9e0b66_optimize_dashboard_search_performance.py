"""optimize_dashboard_search_performance

Revision ID: 1f8bea9e0b66
Revises: 63035876a3de
Create Date: 2025-07-22 11:56:25.880621

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f8bea9e0b66'
down_revision = '63035876a3de'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create search_index table
    op.create_table('search_index',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('analysis_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False, server_default=''),
        sa.Column('violations_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('risk_factors_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('ocr_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('search_text', sa.Text(), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(['analysis_id'], ['analysis_results.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('analysis_id')
    )
    
    # Create optimized indexes for efficient ILIKE searches
    op.create_index('idx_search_filename', 'search_index', ['filename'])
    op.create_index('idx_search_violations', 'search_index', ['violations_text'])
    op.create_index('idx_search_risk_factors', 'search_index', ['risk_factors_text'])
    op.create_index('idx_search_ocr_text', 'search_index', ['ocr_text'])
    op.create_index('idx_search_combined', 'search_index', ['search_text'])
    op.create_index('idx_search_filename_violations', 'search_index', ['filename', 'violations_text'])
    
    # Populate search index with existing data
    # This will be handled by a separate data migration script


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_search_filename_violations', 'search_index')
    op.drop_index('idx_search_combined', 'search_index')
    op.drop_index('idx_search_ocr_text', 'search_index')
    op.drop_index('idx_search_risk_factors', 'search_index')
    op.drop_index('idx_search_violations', 'search_index')
    op.drop_index('idx_search_filename', 'search_index')
    
    # Drop table
    op.drop_table('search_index')