import unittest
import json
import os
import tempfile
import shutil
from checklist import Checklist, ChecklistFactory


class TestChecklist(unittest.TestCase):
    def setUp(self):
        """Set up temporary directory and file for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_checklist.json")
        self.current_round = 1

    def tearDown(self):
        """Clean up temporary directory after tests."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init_with_no_file(self):
        """Test initialization when checklist file doesn't exist."""
        checklist = Checklist(self.test_file, self.current_round)
        self.assertEqual(len(checklist), 0)
        self.assertEqual(checklist.items, [])

    def test_init_with_existing_file(self):
        """Test initialization when checklist file already exists."""
        # Create a file with some items
        test_items = [
            {
                "id": "1",
                "description": "Test item",
                "points": 5,
                "completed": False,
                "created_by": "tester",
                "created_at": 1
            }
        ]
        with open(self.test_file, 'w') as f:
            json.dump(test_items, f)

        checklist = Checklist(self.test_file, self.current_round)
        self.assertEqual(len(checklist), 1)
        self.assertEqual(checklist.items[0]["description"], "Test item")

    def test_add_item(self):
        """Test adding an item to the checklist."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "Test description", 5, "creator")

        self.assertEqual(len(checklist), 1)
        item = checklist.items[0]
        self.assertEqual(item["id"], "item1")
        self.assertEqual(item["description"], "Test description")
        self.assertEqual(item["points"], 5)
        self.assertEqual(item["completed"], False)
        self.assertEqual(item["created_by"], "creator")
        self.assertEqual(item["created_at"], self.current_round)

    def test_add_multiple_items(self):
        """Test adding multiple items to the checklist."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "First item", 3, "creator1")
        checklist.add_item("item2", "Second item", 7, "creator2")
        checklist.add_item("item3", "Third item", 9, "creator3")

        self.assertEqual(len(checklist), 3)
        self.assertEqual(checklist.items[0]["id"], "item1")
        self.assertEqual(checklist.items[1]["id"], "item2")
        self.assertEqual(checklist.items[2]["id"], "item3")

    def test_complete_item(self):
        """Test completing an item in the checklist."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "Test item", 5, "creator")
        self.assertFalse(checklist.items[0]["completed"])

        checklist.complete_item("item1")
        self.assertTrue(checklist.items[0]["completed"])

    def test_complete_nonexistent_item(self):
        """Test completing an item that doesn't exist (should do nothing)."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "Test item", 5, "creator")
        
        # This should not raise an error
        checklist.complete_item("nonexistent_id")
        self.assertFalse(checklist.items[0]["completed"])

    def test_save(self):
        """Test saving the checklist to a file."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "Test item", 5, "creator")
        checklist.save()

        self.assertTrue(os.path.exists(self.test_file))
        with open(self.test_file, 'r') as f:
            loaded_items = json.load(f)

        self.assertEqual(len(loaded_items), 1)
        self.assertEqual(loaded_items[0]["id"], "item1")

    def test_get_items_all(self):
        """Test getting all items regardless of completion status."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "First item", 5, "creator")
        checklist.add_item("item2", "Second item", 7, "creator")
        checklist.complete_item("item1")

        all_items = checklist.get_items()
        self.assertEqual(len(all_items), 2)

    def test_get_items_completed(self):
        """Test getting only completed items."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "First item", 5, "creator")
        checklist.add_item("item2", "Second item", 7, "creator")
        checklist.add_item("item3", "Third item", 3, "creator")
        checklist.complete_item("item1")
        checklist.complete_item("item3")

        completed_items = checklist.get_items(completed=True)
        self.assertEqual(len(completed_items), 2)
        self.assertEqual(completed_items[0]["id"], "item1")
        self.assertEqual(completed_items[1]["id"], "item3")

    def test_get_items_not_completed(self):
        """Test getting only incomplete items."""
        checklist = Checklist(self.test_file, self.current_round)
        checklist.add_item("item1", "First item", 5, "creator")
        checklist.add_item("item2", "Second item", 7, "creator")
        checklist.add_item("item3", "Third item", 3, "creator")
        checklist.complete_item("item1")

        incomplete_items = checklist.get_items(completed=False)
        self.assertEqual(len(incomplete_items), 2)
        self.assertEqual(incomplete_items[0]["id"], "item2")
        self.assertEqual(incomplete_items[1]["id"], "item3")

    def test_len(self):
        """Test the __len__ method."""
        checklist = Checklist(self.test_file, self.current_round)
        self.assertEqual(len(checklist), 0)

        checklist.add_item("item1", "First item", 5, "creator")
        self.assertEqual(len(checklist), 1)

        checklist.add_item("item2", "Second item", 7, "creator")
        self.assertEqual(len(checklist), 2)


class TestChecklistFactory(unittest.TestCase):
    def setUp(self):
        """Set up temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.current_round = 1

    def tearDown(self):
        """Clean up temporary directory after tests."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init(self):
        """Test factory initialization."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        self.assertEqual(factory.folder_path, self.test_dir)
        self.assertEqual(factory.current_round, self.current_round)
        self.assertEqual(len(factory.checklists), 0)

    def test_get_checklist_new(self):
        """Test getting a new checklist."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklist = factory.get_checklist("test_checklist")

        self.assertIsInstance(checklist, Checklist)
        self.assertIn("test_checklist", factory.checklists)
        self.assertEqual(len(checklist), 0)

    def test_get_checklist_cached(self):
        """Test that getting the same checklist returns the cached instance."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklist1 = factory.get_checklist("test_checklist")
        checklist1.add_item("item1", "Test item", 5, "creator")

        checklist2 = factory.get_checklist("test_checklist")
        
        # Should be the same instance
        self.assertIs(checklist1, checklist2)
        self.assertEqual(len(checklist2), 1)

    def test_get_checklist_existing_file(self):
        """Test getting a checklist that already has a saved file."""
        # Create a file first
        test_file = os.path.join(self.test_dir, "existing.json")
        test_items = [
            {
                "id": "1",
                "description": "Existing item",
                "points": 5,
                "completed": False,
                "created_by": "tester",
                "created_at": 1
            }
        ]
        with open(test_file, 'w') as f:
            json.dump(test_items, f)

        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklist = factory.get_checklist("existing")

        self.assertEqual(len(checklist), 1)
        self.assertEqual(checklist.items[0]["description"], "Existing item")

    def test_list_checklists_empty(self):
        """Test listing checklists when folder is empty."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklists = factory.list_checklists()
        self.assertEqual(len(checklists), 0)

    def test_list_checklists(self):
        """Test listing existing checklists."""
        # Create some checklist files
        for name in ["checklist1", "checklist2", "checklist3"]:
            with open(os.path.join(self.test_dir, f"{name}.json"), 'w') as f:
                json.dump([], f)

        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklists = factory.list_checklists()

        self.assertEqual(len(checklists), 3)
        self.assertIn("checklist1", checklists)
        self.assertIn("checklist2", checklists)
        self.assertIn("checklist3", checklists)

    def test_list_checklists_filters_non_json(self):
        """Test that list_checklists only returns .json files."""
        # Create both .json and other files
        with open(os.path.join(self.test_dir, "checklist1.json"), 'w') as f:
            json.dump([], f)
        with open(os.path.join(self.test_dir, "readme.txt"), 'w') as f:
            f.write("test")
        with open(os.path.join(self.test_dir, "data.csv"), 'w') as f:
            f.write("test")

        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklists = factory.list_checklists()

        self.assertEqual(len(checklists), 1)
        self.assertIn("checklist1", checklists)

    def test_delete_checklist_from_memory_and_disk(self):
        """Test deleting a checklist removes it from memory and disk."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklist = factory.get_checklist("test_checklist")
        checklist.add_item("item1", "Test item", 5, "creator")
        checklist.save()

        # Verify it exists
        self.assertIn("test_checklist", factory.checklists)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "test_checklist.json")))

        # Delete it
        factory.delete_checklist("test_checklist")

        self.assertNotIn("test_checklist", factory.checklists)
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test_checklist.json")))

    def test_delete_nonexistent_checklist(self):
        """Test deleting a checklist that doesn't exist (should not error)."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        
        # Should not raise an error
        factory.delete_checklist("nonexistent")

    def test_delete_checklist_only_in_memory(self):
        """Test deleting a checklist that's only in memory, not on disk."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        checklist = factory.get_checklist("test_checklist")
        # Don't save it
        
        self.assertIn("test_checklist", factory.checklists)
        
        # Delete it (file doesn't exist, but should handle gracefully)
        factory.delete_checklist("test_checklist")
        
        self.assertNotIn("test_checklist", factory.checklists)

    def test_save_all(self):
        """Test saving all checklists in the factory."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        
        checklist1 = factory.get_checklist("checklist1")
        checklist1.add_item("item1", "First item", 5, "creator")
        
        checklist2 = factory.get_checklist("checklist2")
        checklist2.add_item("item2", "Second item", 7, "creator")
        
        # Save all
        factory.save_all()

        # Verify both files exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "checklist1.json")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "checklist2.json")))

        # Verify contents
        with open(os.path.join(self.test_dir, "checklist1.json"), 'r') as f:
            data1 = json.load(f)
        self.assertEqual(len(data1), 1)
        self.assertEqual(data1[0]["id"], "item1")

        with open(os.path.join(self.test_dir, "checklist2.json"), 'r') as f:
            data2 = json.load(f)
        self.assertEqual(len(data2), 1)
        self.assertEqual(data2[0]["id"], "item2")

    def test_save_all_empty_factory(self):
        """Test save_all when factory has no checklists."""
        factory = ChecklistFactory(self.test_dir, self.current_round)
        
        # Should not raise an error
        factory.save_all()


if __name__ == '__main__':
    unittest.main()
