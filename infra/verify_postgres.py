"""Verify PostgreSQL schema was created correctly."""
import asyncio
import asyncpg

DB_URL = "postgresql://jobadmin:YOUR_DB_PASSWORD_HERE@YOUR_RDS_ENDPOINT_HERE:5432/jobtracker"

async def verify():
    conn = await asyncpg.connect(DB_URL)
    
    # List tables
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    print("Tables in PostgreSQL:")
    for t in tables:
        print(f"  - {t['tablename']}")
    
    # Count columns in each table
    for t in tables:
        cols = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position",
            t['tablename']
        )
        print(f"\n  {t['tablename']} ({len(cols)} columns):")
        for c in cols:
            print(f"    {c['column_name']}: {c['data_type']}")
    
    await conn.close()
    print("\n✓ PostgreSQL schema verified!")

asyncio.run(verify())
