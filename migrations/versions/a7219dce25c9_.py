"""empty message

Revision ID: a7219dce25c9
Revises: f257f02ece66
Create Date: 2024-08-05 15:53:58.039786

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7219dce25c9'
down_revision = 'f257f02ece66'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_confirmed')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index('ix_users_confirmed', ['confirmed'], unique=False)

    # ### end Alembic commands ###
