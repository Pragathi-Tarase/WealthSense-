import pymysql
import sys

try:
    # Connect to MAMP MySQL Server (no database selected yet)
    connection = pymysql.connect(
        host='127.0.0.1',
        port=8889,
        user='root',
        password='root'
    )
    
    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS wealthsense")
        print("[SUCCESS] Database 'wealthsense' created (or already exists)!")
        
    connection.close()
    sys.exit(0)

except Exception as e:
    print(f"[ERROR] Failed to create database: {e}")
    sys.exit(1)
