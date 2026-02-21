"""Test database connection"""
import asyncio
import os
import asyncpg

async def test_connection():
    try:
        # Try different connection methods
        print("Testing connection methods...")
        
        # Method 1: DSN string
        try:
            db_url = os.environ.get('DATABASE_URL', 'postgresql://truthchain:CHANGE_ME@localhost:5432/truthchain')
            conn = await asyncpg.connect(db_url)
            print('✅ Method 1 (DSN) successful!')
            await conn.close()
        except Exception as e:
            print(f'❌ Method 1 (DSN) failed: {e}')
        
        # Method 2: Separate parameters
        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                database='truthchain',
                user='truthchain',
                password=os.environ.get('DB_PASSWORD', 'CHANGE_ME')
            )
            print('✅ Method 2 (params) successful!')
            
            # Test query
            version = await conn.fetchval('SELECT version()')
            print(f'PostgreSQL version: {version[:80]}...')
            
            # Test creating a simple table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS connection_test (
                    id SERIAL PRIMARY KEY,
                    test_data TEXT
                )
            ''')
            print('✅ Table creation successful!')
            
            # Drop test table
            await conn.execute('DROP TABLE IF EXISTS connection_test')
            print('✅ Table deletion successful!')
            
            await conn.close()
            print('\n🎉 Database connectivity test passed!')
            return True
            
        except Exception as e:
            print(f'❌ Method 2 (params) failed: {e}')
        
        # Method 3: Try with explicit 127.0.0.1
        try:
            conn = await asyncpg.connect(
                host='127.0.0.1',
                port=5432,
                database='truthchain',
                user='truthchain',
                password='truthchain_dev_password'
            )
            print('✅ Method 3 (127.0.0.1) successful!')
            await conn.close()
        except Exception as e:
            print(f'❌ Method 3 (127.0.0.1) failed: {e}')
            
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    asyncio.run(test_connection())
