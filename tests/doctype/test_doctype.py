#
# UNIT TESTS FOR DOCTYPE
# Since doctypes are read one at a time, we should test that the doctype can be:-
# 1. Read from the ERPNext instance on each request refresh.
# 2. Read from the doc_list file on each req refresh.
# Each doctype is cached for a period of time so we should also test that the caching mechanism works as expected.
import json

from get_file import get_file_from_path


def test_doctype():
    """Test that the doctype file has a some valid structure. """
    file= get_file_from_path("doctype/Sales Invoice.json", "public")
    assert isinstance(file['contents'], str) == True, f"Expected file contents to be a string, got {type(file['contents'])}"
    assert isinstance(file['size'], int) == True, f"Expected file size to be an integer, got {type(file['size'])}"
    
    
    if isinstance(file['contents'], str):
        for key in ["doctype", "fields", "permissions"]:
            json_data = json.loads(file['contents'])
            assert key in json_data, f"Expected key '{key}' to be in the file contents, but it was not found."
            assert isinstance(json_data["fields"], list) == True, f"Expected 'fields' to be a list, got {type(json_data['fields'])}"