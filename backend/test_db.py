import asyncio
import asyncpg


async def test_connection():
    try:
        conn = await asyncpg.connect(
            user="postgres",
            password="postgres",
            database="profile_optimizer",
            host="localhost",
        )
        print("✓ Connection successful!")
        await conn.close()
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print(f"Error type: {type(e)}")


asyncio.run(test_connection())
