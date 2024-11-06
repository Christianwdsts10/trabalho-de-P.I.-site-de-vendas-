from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'f9c49d47c96c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Verificar se a coluna 'age' existe antes de tentar removê-la
    inspector = Inspector.from_engine(op.get_bind())
    columns = [column['name'] for column in inspector.get_columns('user')]

    # Adicionar a coluna de senha
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password', sa.String(length=200), nullable=False, default=''))

        # Alterar os tipos das colunas 'username' e 'email'
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=80),
               existing_nullable=False)
        batch_op.alter_column('email',
               existing_type=sa.VARCHAR(length=100),
               type_=sa.String(length=120),
               existing_nullable=False)

        # Verificar se as colunas 'age', 'name' e 'birth_date' existem antes de removê-las
        if 'age' in columns:
            batch_op.drop_column('age')
        if 'name' in columns:
            batch_op.drop_column('name')
        if 'birth_date' in columns:
            batch_op.drop_column('birth_date')


def downgrade():
    # ### comandos de downgrade ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('birth_date', sa.DATE(), nullable=False))
        batch_op.add_column(sa.Column('name', sa.VARCHAR(length=100), nullable=False))
        batch_op.add_column(sa.Column('age', sa.INTEGER(), nullable=False))
        batch_op.alter_column('email',
               existing_type=sa.String(length=120),
               type_=sa.VARCHAR(length=100),
               existing_nullable=False)
        batch_op.alter_column('username',
               existing_type=sa.String(length=80),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)
        batch_op.drop_column('password')

    # ### fim dos comandos de downgrade ###


