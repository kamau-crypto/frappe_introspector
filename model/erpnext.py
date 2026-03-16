import json
from typing import Any, Dict, List, Optional

import requests

from model.auth import SessionExpiredError


class ERPNextConnection:
    """Handles connections and API calls to ERPNext instances"""

    def __init__(self, base_url: str, api_key: str, api_secret: str, APP_MODE: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.APP_MODE = APP_MODE


    def _check_response(self, response: requests.Response) -> requests.Response:
        """
        Inspect every Frappe response.
        Raises SessionExpiredError on 401/403 so the middleware can catch it
        and redirect the user back to /connect with a clear message.
        """
        if response.status_code in (401, 403):
            raise SessionExpiredError(
                "Your Frappe session has expired or the API token was revoked. "
                "Please reconnect."
            )
        return response

    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to ERPNext"""
        try:
            response = self._check_response(
                requests.get(
                    f"{self.base_url}/api/method/frappe.handler.ping",
                    headers=self.headers,
                    timeout=10,
                )
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": f"HTTP {response.status_code}"}
        except SessionExpiredError:
            raise
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_doctype_meta(self, doctype: str) -> List[Dict[str,Any]]|None:
        """Get DocType metadata using the working whitelisted method"""
        try:
            response = requests.get(
                f"{self.base_url}/api/method/frappe.desk.form.load.getdoctype",
                params={"doctype": doctype},
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("message", {})
            else:
                print(
                    f"Error getting metadata for {doctype}: HTTP {response.status_code}"
                )
                return None
        except Exception as e:
            print(f"Exception getting metadata for {doctype}: {e}")
            return None

    def get_all_doctypes(self, module: str|None = None) -> List[Dict]:
        """Get all available DocTypes"""
        try:
            response = requests.get(
                f"{self.base_url}/api/resource/DocType",
                params={
                    "fields": '["name","module","custom","is_submittable","is_tree","description"]',
                    "where": f'module="{module}"' if module else None,
                    "limit_page_length": 0,
                },
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                list_data = data.get("data", [])
                if self.APP_MODE != "erpnext":
                    # Remove custom doctypes in production mode
                    non_custom = lambda list_data: [d for d in list_data if not d.get("custom")]
                    # If there is a file present, then open it, otherwise read from the file
                    with open("./public/doctypes_list.json", "w") as f:
                        json.dump(non_custom(list_data), f, indent=2)
                return list_data
            return []
        except Exception as _e:
            return []

    def get_doctype_definition(self, doctype: str) -> Optional[Dict]:
        """Get the raw DocType definition"""
        try:
            response = requests.get(
                f"{self.base_url}/api/resource/DocType/{doctype}",
                headers=self.headers,
                timeout=30,
            )
            # Extract custom fields for the DocType per documentation
            custom_fields = requests.get(
                f"{self.base_url}/api/resource/Custom Field",
                params={"filters": f'[["dt","=","{doctype}"]]', "fields": '["*"]'},
                headers=self.headers,
                timeout=30,
            )
            #
            # [ ] Currently not working, Fix for future edge cases
            property_setter= requests.get(
                f'{self.base_url}/api/resource/Property Setter?filters=[["doctype","=","{doctype}"]]',
                headers=self.headers,
                timeout=30
            )
            # There are edge cases whereby the the client's uses the export fixtures. and the fixtures are in the fixtures.json file...
            all= self.get_doctype_meta(doctype)
            if response.status_code == 200 or custom_fields.status_code == 200:
                # Convert the response to a JSON
                data = response.json()
                #
                data_tables = data.get("data")
                # Customizations to append to the list of files
                if self.APP_MODE == "erpnext":
                    customization = custom_fields.json().get(
                        "data",
                    )
                    # Append the customizations to the application
                    for custom in customization:
                        data_tables.get("fields").append(custom)
                # Check property setters and append to the data tables
                if self.APP_MODE== "erpnext" and property_setter.status_code == 200:
                    property_setters = property_setter.json().get("data", [])
                    data_tables.get("fields").extend(property_setters)
                return data_tables
            return None
        except Exception as e:
            print(f"Exception getting DocType definition for {doctype}: {e}")
            return None
    
    def generate_doctypes_list_file(self):
        """Generate a JSON file with the list of DocTypes for production mode"""
        # with open("./public/doctypes_list.json", "r") as f:
        #     # All doctype lists
        #     for doctype in json.load(f):
        #         doctype_name = doctype.get("name")
        #         # Add a timeout to avoid overwhelming the server with requests
        #         # time.sleep(0.)
        #         if doctype_name:
        #             metadata = self.get_doctype_definition(doctype_name)
        #             if metadata:
        #                 with open(f"./public/doctype/{doctype_name}.json","w") as f:
        #                     json.dump(metadata, f, indent=2)
        #                     print(f"Saved metadata for {doctype_name}")

    def cleanup_unncessary_properties(self):
        """ Cleanup unnecessary properties from the Docttype Metadata to reduce file size and improve performance.
            - Some of the fields trimmed are:-
            1. creation,
            2. modified,
            3. modified_by,
            4. owner.
        """
        with open("./public/doctypes_list.json", "r") as f:
            for doctype in json.load(f):
                doctype_name= doctype.get("name")
                
                if doctype_name:
                    with open(f"./public/doctype/{doctype_name}.json","r") as f:
                        metadata = json.load(f)
                        # Remove unnecessary properties
                        for prop in ["creation", "modified", "modified_by", "owner"]:
                            metadata.pop(prop, None)
                        if metadata.get("fields"):
                            for field in metadata["fields"]:
                                for prop in ["creation", "modified", "modified_by", "owner"]:
                                    field.pop(prop, None)
                    with open(f"./public/doctype/{doctype_name}.json","w") as f:
                        json.dump(metadata, f, indent=2)
                        print(f"Cleaned up metadata for {doctype_name}")
