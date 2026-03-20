# UNIT TESTS FOR DOCTYPE LIST
# Here, I want to test the doctype. Their existence is tied to two modes.
#
#  1. The doctype is read from the ERPNext instance on each request refresh.
# 2. The doctype is read from the doc_list file on each req refresh.
# The first time, the file is not in the redis cache and if not, then we can index it based on some key.
import json

from get_file import get_file_from_path


class DoctypeList:
    name: str
    module: str
    custom: bool| int
    is_submittable: bool| int
    is_tree: bool| int
    description: str| None

def test_doctype_list():
    file= get_file_from_path("doctypes_list.json", "public")
    assert isinstance(file['contents'], str) == True, f"Expected file contents to be a string, got {type(file['contents'])}"
    assert isinstance(file['size'], int) == True, f"Expected file size to be an integer, got {type(file['size'])}"
    
    if isinstance(file['contents'], str):
        json_data = json.loads(file['contents'])
        assert isinstance(json_data, list) == True, f"Expected file contents to be a list, got {type(json_data)}"
        
        for item in json_data:
            assert isinstance(item, dict) == True, f"Expected each item in the list to be a dictionary, got {type(item)}"
            for key in DoctypeList.__annotations__.keys():
                assert key in item, f"Expected key '{key}' to be in the item, but it was not found."
            assert isinstance(DoctypeList, type) == True, f"Expected DoctypeList to be a subclass of object, got {type(DoctypeList)}"
        