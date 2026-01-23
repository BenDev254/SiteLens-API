import asyncio
from sqlmodel import SQLModel, create_engine
from sqlalchemy import text

# Use your DATABASE_URL
DATABASE_URL = "postgresql+asyncpg://fmmcqhyjsk:bfKx$vh0y9$13rkS@bac-server.postgres.database.azure.com:5432/bac-database?ssl=require"

# Create a synchronous engine for simple inspection
engine = create_engine(DATABASE_URL.replace('+asyncpg', ''))

# List all tables
with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public';"))
    print("Tables in the database:")
    for row in result:
        print(row[0])

# Optionally, query one of your tables
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM project LIMIT 5;"))
    print("\nSample data from project table:")
    for row in result:
        print(row)
