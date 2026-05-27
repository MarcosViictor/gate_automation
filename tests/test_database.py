import unittest
import os
import sqlite3
from models.database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_gate_local.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Import config and override DB_PATH dynamically for tests
        import config
        config.DB_PATH = self.db_path
        self.db = Database()
        self.db.create_tables()

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_vehicles_table_exists(self):
        conn = self.db.connect()
        cursor = conn.execute("PRAGMA table_info(vehicles)")
        columns = {row["name"]: row["type"] for row in cursor.fetchall()}
        
        self.assertIn("id", columns)
        self.assertIn("server_id", columns)
        self.assertIn("plate", columns)
        self.assertIn("tag_id", columns)
        self.assertIn("portaria_id", columns)
        self.assertIn("model", columns)
        self.assertIn("is_active", columns)
        self.assertIn("updated_at", columns)

if __name__ == "__main__":
    unittest.main()
