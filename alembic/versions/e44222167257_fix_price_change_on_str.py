"""fix price, change on str

Revision ID: e44222167257
Revises: ec361aa48603
Create Date: 2025-01-12 12:18:19.673373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e44222167257'
down_revision: Union[str, None] = 'ec361aa48603'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('products', sa.Column('title', sa.String(), nullable=False))
    op.add_column('products', sa.Column('image_urls', sa.String(), nullable=True))
    op.alter_column('products', 'price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.String(),
               existing_nullable=True)
    op.drop_column('products', 'image_url')
    op.drop_column('products', 'name')
    op.add_column('sellers', sa.Column('region', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('sellers', 'region')
    op.add_column('products', sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('products', sa.Column('image_url', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.alter_column('products', 'price',
               existing_type=sa.String(),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=True)
    op.drop_column('products', 'image_urls')
    op.drop_column('products', 'title')
    # ### end Alembic commands ###
