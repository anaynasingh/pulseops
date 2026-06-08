import asyncio, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import asyncpg
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def run():
    url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url, ssl='disable')
    new_hash = pwd_ctx.hash('anaynasingh')
    result = await conn.execute("UPDATE users SET password_hash = $1", new_hash)
    rows = await conn.fetch("SELECT email FROM users")
    print('Reset password for:', [r['email'] for r in rows])
    await conn.close()

asyncio.run(run())
