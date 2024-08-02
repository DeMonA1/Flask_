"""empty message

Revision ID: d643a025524f
Revises: 55f8b3273fc5
Create Date: 2024-08-01 17:36:31.056545

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd643a025524f'
down_revision = '55f8b3273fc5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(), nullable=False))
        batch_op.add_column(sa.Column('location', sa.String(), nullable=False))
        batch_op.add_column(sa.Column('about_me', sa.String(), nullable=False))
        batch_op.add_column(sa.Column('member_since', sa.DateTime(), nullable=False))
        batch_op.add_column(sa.Column('last_seen', sa.DateTime(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_seen')
        batch_op.drop_column('member_since')
        batch_op.drop_column('about_me')
        batch_op.drop_column('location')
        batch_op.drop_column('name')

    # ### end Alembic commands ###
