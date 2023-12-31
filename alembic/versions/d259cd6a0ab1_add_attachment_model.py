"""Add Attachment model

Revision ID: d259cd6a0ab1
Revises: 25c056e652aa
Create Date: 2024-01-07 18:39:38.470530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd259cd6a0ab1'
down_revision: Union[str, None] = '25c056e652aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('attachments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('discord_filename', sa.String(), nullable=False),
    sa.Column('discord_id', sa.String(), nullable=False),
    sa.Column('emoji', sa.String(), nullable=True),
    sa.Column('filename', sa.String(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('attachments')
    # ### end Alembic commands ###
