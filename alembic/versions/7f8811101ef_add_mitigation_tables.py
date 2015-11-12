"""Add mitigation tables

Revision ID: 7f8811101ef
Revises: 59eacaa4aaf1
Create Date: 2015-11-12 09:04:02.102115

"""

# revision identifiers, used by Alembic.
revision = '7f8811101ef'
down_revision = '59eacaa4aaf1'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('beam_classes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('number')
    )
    op.create_table('mitigation_devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('allowed_classes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fault_state_id', sa.Integer(), nullable=False),
    sa.Column('mitigation_device_id', sa.Integer(), nullable=False),
    sa.Column('class_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['class_id'], ['beam_classes.id'], ),
    sa.ForeignKeyConstraint(['fault_state_id'], ['fault_states.id'], ),
    sa.ForeignKeyConstraint(['mitigation_device_id'], ['mitigation_devices.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('allowed_classes')
    op.drop_table('mitigation_devices')
    op.drop_table('beam_classes')
    ### end Alembic commands ###
