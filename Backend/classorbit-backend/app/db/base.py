from app.models import Base

# Importing app.models registers every model on Base.metadata for Alembic and create_all.

__all__ = ["Base"]
