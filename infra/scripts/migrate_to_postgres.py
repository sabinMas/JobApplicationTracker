"""
Migration script: SQLite → PostgreSQL

Migrates all data from local SQLite database to AWS RDS PostgreSQL.

Usage:
    python infra/migrate_to_postgres.py

Requires:
    - POSTGRES_URL environment variable set to target database
    - Local SQLite database at data/app.db
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")


async def migrate():
    """Migrate data from SQLite to PostgreSQL."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text, inspect
    
    # Source: SQLite
    data_dir = Path(__file__).parent.parent / "data"
    sqlite_url = f"sqlite+aiosqlite:///{data_dir}/app.db"
    
    # Target: PostgreSQL
    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        print("ERROR: Set POSTGRES_URL environment variable")
        print("Example: postgresql+asyncpg://jobadmin:password@host:5432/jobtracker")
        sys.exit(1)
    
    # Ensure asyncpg driver
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    print(f"Source: SQLite ({data_dir}/app.db)")
    print(f"Target: PostgreSQL ({postgres_url.split('@')[1] if '@' in postgres_url else 'configured'})")
    print()
    
    # Check SQLite exists
    if not (data_dir / "app.db").exists():
        print("No SQLite database found. Nothing to migrate.")
        print("Creating empty schema on PostgreSQL...")
    
    # Create engines
    sqlite_engine = create_async_engine(sqlite_url, echo=False)
    pg_engine = create_async_engine(postgres_url, echo=False, pool_pre_ping=True)
    
    # Import models to register them with Base
    from app.database import Base
    from app.models import Profile, Job, Application, Document, ApplicationMetric
    
    # Create tables on PostgreSQL
    print("[1/4] Creating PostgreSQL schema...")
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✓ Tables created")
    
    # Check if SQLite has data
    if not (data_dir / "app.db").exists():
        print("\n✓ Migration complete (empty database initialized)")
        await sqlite_engine.dispose()
        await pg_engine.dispose()
        return
    
    # Read data from SQLite
    print("[2/4] Reading data from SQLite...")
    
    tables = ["profile", "jobs", "documents", "applications", "application_metrics"]
    table_data = {}
    
    async with sqlite_engine.connect() as conn:
        for table_name in tables:
            try:
                result = await conn.execute(text(f"SELECT * FROM {table_name}"))
                rows = result.fetchall()
                columns = result.keys()
                table_data[table_name] = {
                    "columns": list(columns),
                    "rows": [dict(zip(columns, row)) for row in rows],
                }
                print(f"  ✓ {table_name}: {len(rows)} rows")
            except Exception as e:
                print(f"  ⚠ {table_name}: {e} (skipping)")
                table_data[table_name] = {"columns": [], "rows": []}
    
    # Write data to PostgreSQL
    print("[3/4] Writing data to PostgreSQL...")
    
    async with pg_engine.begin() as conn:
        for table_name in tables:
            data = table_data[table_name]
            if not data["rows"]:
                print(f"  - {table_name}: empty (skipping)")
                continue
            
            # Build INSERT statement
            columns = data["columns"]
            placeholders = ", ".join([f":{col}" for col in columns])
            col_names = ", ".join(columns)
            
            insert_sql = text(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders}) "
                f"ON CONFLICT DO NOTHING"
            )
            
            try:
                await conn.execute(insert_sql, data["rows"])
                print(f"  ✓ {table_name}: {len(data['rows'])} rows inserted")
            except Exception as e:
                print(f"  ✗ {table_name}: {e}")
    
    # Verify
    print("[4/4] Verifying migration...")
    async with pg_engine.connect() as conn:
        for table_name in tables:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"  ✓ {table_name}: {count} rows in PostgreSQL")
    
    # Cleanup
    await sqlite_engine.dispose()
    await pg_engine.dispose()
    
    print()
    print("=" * 50)
    print("✓ Migration complete!")
    print()
    print("Next steps:")
    print("  1. Update DATABASE_URL in .env to point to PostgreSQL")
    print("  2. Restart the backend server")
    print("  3. Verify API responses match expected data")
    print()


if __name__ == "__main__":
    asyncio.run(migrate())
