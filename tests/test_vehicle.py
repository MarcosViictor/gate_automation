import unittest
import os
from models.database import Database
from models.tag import Tag, TagRepository
from models.vehicle import Vehicle, VehicleRepository

class TestVehicleRepository(unittest.TestCase):
    def setUp(self):
        self.db_path = "data/test_vehicle.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        import config
        config.DB_PATH = self.db_path
        self.db = Database()
        self.db.create_tables()
        self.tag_repo = TagRepository(self.db)
        self.vehicle_repo = VehicleRepository(self.db)

        # Seed a tag
        self.tag_repo.upsert(Tag(server_id=1, tag_code="ABC12345", is_active=True))
        self.tag = self.tag_repo.find_by_code("ABC12345")

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_upsert_and_find_all(self):
        v = Vehicle(plate="XYZ-9876", model="Golf", portaria_id=1, tag_id=self.tag.id)
        self.vehicle_repo.upsert(v)
        
        vehicles = self.vehicle_repo.find_all()
        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0].plate, "XYZ-9876")
        self.assertEqual(vehicles[0].tag_code, "ABC12345")

    def test_find_by_tag_code(self):
        v = Vehicle(plate="XYZ-9876", model="Golf", portaria_id=1, tag_id=self.tag.id)
        self.vehicle_repo.upsert(v)
        
        found = self.vehicle_repo.find_by_tag_code("ABC12345")
        self.assertIsNotNone(found)
        self.assertEqual(found.plate, "XYZ-9876")

if __name__ == "__main__":
    unittest.main()
