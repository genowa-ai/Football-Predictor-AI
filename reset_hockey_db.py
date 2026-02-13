import psycopg2
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src import config
except ImportError:
    import config

def reset_database():
    print(f"🔥 CONNECTING TO DATABASE: {config.DB_NAME}...")
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST, database=config.DB_NAME,
            user=config.DB_USER, password=config.DB_PASS
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # TRUNCATE ensures a complete wipe and resets ID counters if needed
        print(f"⚠️ TRUNCATING TABLE: {config.HOCKEY_TABLE}...")
        cursor.execute(f"TRUNCATE TABLE {config.HOCKEY_TABLE} RESTART IDENTITY CASCADE;")
        
        print("✅ SUCCESS: Hockey table has been completely wiped.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    reset_database()