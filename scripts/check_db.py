import os
import psycopg2

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD', ''),
        dbname=os.getenv('DB_NAME', 'postgres'),
        connect_timeout=3
    )
    cur = conn.cursor()
    cur.execute('SELECT version();')
    print('CONECTADO:', cur.fetchone()[0][:60])
    cur.execute("SELECT datname FROM pg_database WHERE datname IN ('taller_db', 'taller_v3') ORDER BY datname;")
    dbs = cur.fetchall()
    print('BDs existentes:', [r[0] for r in dbs])
    conn.close()
except Exception as e:
    print('ERROR:', e)
