import unittest
import os
from models.database import Database
from models.tag import Tag, TagRepository
from models.vehicle import Vehicle, VehicleRepository
from models.access_log import AccessLog, AccessLogRepository

class TestAccessLogRepository(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_access_log.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import config
        config.DB_PATH = self.db_path
        self.db = Database(self.db_path)
        self.db.create_tables()
        self.tag_repo = TagRepository(self.db)
        self.vehicle_repo = VehicleRepository(self.db)
        self.log_repo = AccessLogRepository(self.db)

        # Seed tag & vehicle
        self.tag_repo.upsert(Tag(server_id=1, tag_code="LOGTAG123", is_active=True))
        self.tag = self.tag_repo.find_by_code("LOGTAG123")
        self.vehicle = Vehicle(plate="XYZ-1111", model="Cruze", portaria_id=3, tag_id=self.tag.id)
        self.vehicle_repo.upsert(self.vehicle)

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_find_recent_includes_vehicle_details(self):
        log = AccessLog(tag_code="LOGTAG123", authorized=True, direction="IN")
        self.log_repo.save(log)

        recent = self.log_repo.find_recent(limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].vehicle_plate, "XYZ-1111")
        self.assertEqual(recent[0].vehicle_model, "Cruze")
        self.assertEqual(recent[0].portaria_id, 3)

if __name__ == "__main__":
    unittest.main()
