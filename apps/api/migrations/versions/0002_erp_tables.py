"""Add ERP customers and invoices tables."""
from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "0002_erp_tables"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    pass
