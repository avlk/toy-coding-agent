
# A class contains a checklist, which is a list of items that are either completed or not completed.
# Each item has the following attributes:
# - id: is a number or a word that uniquely identifies the item.
# - description: is a string that describes the item.
# - points: the number of points that the item is worth, between 0 (absolutely optional) and 9 (critical).
# - completed: is a boolean that indicates whether the item is completed or not.
# - created_by: indicates an entity that created the item.
# - created_at: execution round the item was created.

# A checklist item is a dictionary with the aforementioned attributes. A checklist is an ordered list of checklist items.
# A new item is added to the end of the checklist. The checklist is ordered by the natuaral order of item creation, it is not re-ordered.
# The items in the checklist are not deleted when they are completed.
# A checklist has methods to load and save the checklist to a file. The file is in JSON format, and the checklist is stored as a list of checklist items.

import json
import os
import os
from typing import List, Dict, Any, Union
from utils import to_lines

class Checklist:
    def __init__(self, filename: str):
        self.filename = filename
        try:
            with open(self.filename, 'r') as f:
                self.items = json.load(f)
        except FileNotFoundError:
            self.items: List[Dict[str, Any]] = []

    def add_item(self, item_id: str, title: str, description: Union[str, List[str]], points: int, created_by: str, created_at: int):
        item = {
            "id": item_id,
            "title": title,
            "description": to_lines(description),
            "points": points,
            "completed": False,
            "created_by": created_by,
            "created_at": created_at
        }
        self.items.append(item)

    def complete_item(self, item_id: str):
        for item in self.items:
            if item["id"] == item_id:
                item["completed"] = True
                break

    def edit_item(self, item_id: str, title: str = None, description: Union[str, List[str], None] = None, points: int = None, completed: bool = None):
        for item in self.items:
            if item["id"] == item_id:
                if title is not None:
                    item["title"] = title
                if description is not None:
                    item["description"] = to_lines(description)
                if points is not None:
                    item["points"] = points
                if completed is not None:
                    item["completed"] = completed
                break

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.items, f, indent=4)

    def get_items(self, completed: bool = None) -> List[Dict[str, Any]]:
        if completed is None:
            return self.items
        return [item for item in self.items if item["completed"] == completed]

    def __len__(self):
        return len(self.items)

    def __empty__(self):
        return len(self.items) == 0

# A factory that creates checklist instances. Each checklist has a unique name and they are stored in a folder.
# The factory object is initialized with the folder path where the checklists are stored. The checklist files are named as <checklist_name>.json.
# When a checklist is requsted, the factory checks if the checklist already exists in the folder. 
# If it does, it loads the checklist from the file. If it does not, it creates a new checklist and returns it.
# The factory keeps a reference to the checklist in memory and returns the reference when the checklist is requested again.
# The factory also has methods to:
# - list all the checklists in the folder, which returns a list of checklist names.
# - delete a checklist, which deletes the file and removes the reference from memory.

class ChecklistFactory:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.checklists: Dict[str, Checklist] = {}

    def get_checklist(self, checklist_name: str) -> Checklist:
        if checklist_name in self.checklists:
            return self.checklists[checklist_name]

        checklist = Checklist(f"{self.folder_path}/{checklist_name}.json")
        self.checklists[checklist_name] = checklist
        return checklist

    def list_checklists(self) -> List[str]:
        return [filename[:-5] for filename in os.listdir(self.folder_path) if filename.endswith('.json')]

    def delete_checklist(self, checklist_name: str):
        if checklist_name in self.checklists:
            del self.checklists[checklist_name]
        try:
            os.remove(f"{self.folder_path}/{checklist_name}.json")
        except FileNotFoundError:
            pass

    def save_all(self):
        for checklist in self.checklists.values():
            checklist.save()
