# run_migrations.py
import os
from alembic.config import CommandLine

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL")

# Run Alembic
cli = CommandLine()
cli.run(["upgrade", "head"])
