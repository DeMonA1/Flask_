"""empty message

Revision ID: 27fefa6eef0d
Revises: 6fe3fcb96310
Create Date: 2024-08-01 17:44:50.482407

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27fefa6eef0d'
down_revision = '6fe3fcb96310'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('member_since', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_seen', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_seen')
        batch_op.drop_column('member_since')

    # ### end Alembic commands ###
