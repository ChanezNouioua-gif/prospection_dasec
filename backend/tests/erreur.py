import sqlite3
conn = sqlite3.connect("data/dasec_prospection.db")
conn.execute("ALTER TABLE users ADD COLUMN notifications_actives INTEGER DEFAULT 1")
conn.commit()
conn.close()
print("Migration ok")