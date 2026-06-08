import asyncio, os, sys, time

backend = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend)
sys.path.insert(0, backend)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend, '.env'))
import asyncpg

db_path = os.path.join(backend, '..', 'database')

async def run():
    url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    # retry until DB is ready
    for attempt in range(10):
        try:
            conn = await asyncpg.connect(url)
            break
        except Exception as e:
            print(f'Attempt {attempt+1}: {e}')
            await asyncio.sleep(5)
    else:
        print('Could not connect after 10 attempts')
        return

    for fname in ['pgvector_setup.sql', 'schema.sql']:
        path = os.path.join(db_path, fname)
        with open(path, encoding='utf-8') as f:
            sql = f.read()
        try:
            await conn.execute(sql)
            print(f'OK: {fname}')
        except Exception as e:
            print(f'WARN {fname}: {e}')
    await conn.close()
    print('Schema applied successfully')

asyncio.run(run())
