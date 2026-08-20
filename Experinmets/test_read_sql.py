import sqlite3 as sql
from pathlib import Path

conn = sql.connect(Path.home() / "Projects" / "FBS" / "Data"/ "TestData" / "lightning.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM flashes")

print(cursor.fetchone()[0])

conn.close()