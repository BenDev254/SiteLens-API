# run_migrations.py
import os
from alembic.config import Config
from alembic import command

# Get the DATABASE_URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set!")

# Load alembic.ini
alembic_cfg = Config("alembic.ini")

# Override the URL from environment
alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

# Apply all migrations
command.upgrade(alembic_cfg, "head")

print("Migrations applied successfully.")
