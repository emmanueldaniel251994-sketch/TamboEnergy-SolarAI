"""Store PDF provenance reviews transactionally.

Revision ID: a8d52f4c901e
Revises: 0c7151855e86
"""
from alembic import op
import sqlalchemy as sa

revision = 'a8d52f4c901e'
down_revision = '0c7151855e86'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('manufacturer_pdf_reviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('decision', sa.String(32), nullable=False),
        sa.Column('reviewer_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewer_reference', sa.String(120), nullable=False),
        sa.Column('evidence_url', sa.String(2048), nullable=True),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('legacy_key', sa.String(64), nullable=True),
        sa.CheckConstraint("decision IN ('approve_provenance','reject','needs_more_evidence')", name='ck_pdf_review_decision'),
        sa.UniqueConstraint('legacy_key'),
    )
    op.create_index('ix_pdf_review_sha_id', 'manufacturer_pdf_reviews', ['sha256', 'id'])


def downgrade():
    op.drop_index('ix_pdf_review_sha_id', table_name='manufacturer_pdf_reviews')
    op.drop_table('manufacturer_pdf_reviews')
