"""Add weather_location to users

Revision ID: 25c056e652aa
Revises: 9de4b56d1b4f
Create Date: 2024-01-01 14:53:33.741943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25c056e652aa'
down_revision: Union[str, None] = '9de4b56d1b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('weather_location', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'weather_location')
    # ### end Alembic commands ###
