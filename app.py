import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from ollama import Message

from ai import AIChat
from db import AIChatDB

load_dotenv()
import requests
from flask import (Flask, Response, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session, stream_with_context,
                   url_for)
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired

from auth import SessionExpiredError, validate_session

ERPNEXT_URL = os.environ.get("ERPNEXT_URL", "http://127.0.0.1:8000")
ERP_API_KEY = os.environ.get("ERP_API_KEY", None)
ERP_API_SECRET = os.environ.get("ERP_API_SECRET", None)
APP_MODE = os.environ.get("MODE", "erpnext")  # "erpnext" or "production"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "erpnextinspectorsecretkey")
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1MB max file upload

class ERPNextConnection:
    """Handles connections and API calls to ERPNext instances"""

    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


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

    def get_all_doctypes(self) -> List[Dict]:
        """Get all available DocTypes"""
        try:
            response = requests.get(
                f"{self.base_url}/api/resource/DocType",
                params={
                    "fields": '["name","module","custom","is_submittable","is_tree","description"]',
                    "limit_page_length": 0,
                },
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                list_data = data.get("data", [])
                if APP_MODE != "erpnext":
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
            # [ ] Currently not working, Fix for future tests cases
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
                if APP_MODE == "erpnext":
                    customization = custom_fields.json().get(
                        "data",
                    )
                    # Append the customizations to the application
                    for custom in customization:
                        data_tables.get("fields").append(custom)
                # Check property setters and append to the data tables
                if APP_MODE== "erpnext" and property_setter.status_code == 200:
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

class OpenAPIGenerator:
    def json_schema_to_typescript_interface(
        self, schema: Dict, interface_name: str = "DocTypeSchema"
    ) -> str:
        """Generate TypeScript interface from JSON schema, formatted for display"""
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        enums = []
        enum_order = []
        lines = [f"export interface {interface_name} {{"]
        for prop, details in properties.items():
            ts_type = "any"
            if details.get("type") == "string":
                ts_type = "string"
            elif details.get("type") == "integer":
                ts_type = "number"
            elif details.get("type") == "number":
                ts_type = "number"
            elif details.get("type") == "boolean":
                ts_type = "boolean"
            elif details.get("type") == "array":
                item_type = "any"
                if details.get("items", {}).get("type"):
                    if details["items"]["type"] == "object":
                        item_type = "Record<string, any>"
                    else:
                        item_type = details["items"]["type"]
                ts_type = f"{item_type}[]"
            elif details.get("type") == "object":
                ts_type = "Record<string, any>"

            # Handle enums
            if "enum" in details:
                enum_name = f"{prop[0].upper() + prop[1:]}Enum"
                enum_values = details["enum"]
                formatted_values = []
                for v in enum_values:
                    if isinstance(v, str):
                        formatted_values.append(f"'{v}'")
                    else:
                        formatted_values.append(str(v))
                enum_def = (
                    f"export enum {enum_name} {{ " + ", ".join(formatted_values) + " }"
                )
                enums.append(enum_def)
                enum_order.append(enum_name)
                ts_type = enum_name

            # Optional if not required
            optional = "?" if prop not in required else ""
            lines.append(f"  {prop}{optional}: {ts_type};")
        lines.append("}")
        # Add enums above interface, separated by two newlines
        return "\n\n".join(enums + ["\n".join(lines)])

    def frappe_fields_to_typescript_json_schema(self, fields: List[Dict]) -> Dict:
        """Generate a TypeScript-compatible JSON schema from Frappe fields"""
        schema = {"type": "object", "properties": {}, "required": []}
        for field in fields:
            if not field.get("fieldname") or field.get("fieldtype") in [
                "Section Break",
                "Column Break",
                "HTML",
            ]:
                continue
            fieldname = field["fieldname"]
            property_def = self.map_frappe_field_to_openapi(field)
            schema["properties"][fieldname] = property_def
            if field.get("reqd"):
                schema["required"].append(fieldname)
        return schema

    """Generates OpenAPI specifications from ERPNext DocTypes"""

    def __init__(self, connection: ERPNextConnection| None = None):
        self.conn = connection

    def map_frappe_field_to_openapi(self, field: Dict) -> Dict:
        """Map Frappe field types to OpenAPI schema properties"""
        property_def = {"description": field.get("label", field.get("fieldname", ""))}

        # Add read-only flag
        if field.get("read_only"):
            property_def["readOnly"] = True

        # Add default value
        if field.get("default"):
            property_def["default"] = field["default"]

        # Map field types
        fieldtype = field.get("fieldtype", "Data")

        field_type_mapping = {
            "Data": {"type": "string"},
            "Small Text": {"type": "string"},
            "Long Text": {"type": "string"},
            "Text Editor": {"type": "string"},
            "Text": {"type": "string", "maxLength": 65535},
            "Code": {"type": "string"},
            "Int": {"type": "integer"},
            "Float": {"type": "number", "format": "float"},
            "Currency": {"type": "number", "format": "float"},
            "Percent": {"type": "number", "format": "float"},
            "Check": {"type": "integer", "enum": [0, 1]},
            "Select": {"type": "string"},
            "Link": {"type": "string"},
            "Date": {"type": "string", "format": "date"},
            "Datetime": {"type": "string", "format": "date-time"},
            "Time": {"type": "string", "format": "time"},
            "Password": {"type": "string", "format": "password", "writeOnly": True},
            "Attach": {"type": "string", "format": "uri"},
            "Attach Image": {"type": "string", "format": "uri"},
            "Table": {"type": "array", "items": {"type": "object"}},
            "JSON": {"type": "object"},
            "HTML": {"type": "string"},
            "Signature": {"type": "string"},
            "Color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
            "Barcode": {"type": "string"},
            "Geolocation": {"type": "string"},
        }

        property_def.update(field_type_mapping.get(fieldtype, {"type": "string"}))

        # Handle Select options
        if fieldtype == "Select" and field.get("options"):
            options = [
                opt.strip() for opt in field["options"].split("\n") if opt.strip()
            ]
            if options:
                property_def["enum"] = options

        # Handle Link field description
        if fieldtype == "Link" and field.get("options"):
            property_def["description"] += f" (Links to {field['options']})"

        return property_def

    def generate_doctype_schema(self, doctype: str, metadata: List[Dict[str,Any]]| Dict [str, Any]) -> Dict:
        """Generate OpenAPI schema for a DocType"""
        if isinstance(metadata, list):
            return {}
        docs = metadata.get("docs", [])
        if not docs:
            return {}

        doctype_doc = docs[0]  # Main DocType document
        fields = doctype_doc.get("fields", [])

        schema = {
            "type": "object",
            "properties": {
                # Standard Frappe document properties
                "name": {
                    "type": "string",
                    "description": "Document ID/name",
                    "readOnly": True,
                },
                "owner": {
                    "type": "string",
                    "description": "Document owner",
                    "readOnly": True,
                },
                "creation": {"type": "string", "format": "date-time", "readOnly": True},
                "modified": {"type": "string", "format": "date-time", "readOnly": True},
                "modified_by": {"type": "string", "readOnly": True},
                "docstatus": {"type": "integer", "enum": [0, 1, 2], "readOnly": True},
                "doctype": {"type": "string", "readOnly": True},
            },
            "required": [],
        }

        # Process fields
        for field in fields:
            if not field.get("fieldname") or field.get("fieldtype") in [
                "Section Break",
                "Column Break",
                "HTML",
            ]:
                continue

            fieldname = field["fieldname"]
            property_def = self.map_frappe_field_to_openapi(field)
            schema["properties"][fieldname] = property_def

            # Add to required fields if mandatory
            if field.get("reqd"):
                schema["required"].append(fieldname)

        return schema

    def generate_openapi_spec(self, doctypes: List[str], info: Dict = {}) -> Dict:
        """Generate complete OpenAPI specification"""
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": info.get("title", "ERPNext API"),
                "description": info.get(
                    "description", "Auto-generated OpenAPI specification for ERPNext"
                ),
                "version": info.get("version", "1.0.0"),
            },
            "servers": [{"url": self.conn.base_url if self.conn else "http://127.0.0.1:8000", "description": "ERPNext Server"}],
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "Authorization",
                        "description": 'Use "token api_key:api_secret"',
                    }
                },
                "schemas": {},
            },
            "security": [{"ApiKeyAuth": []}],
            "paths": {},
        }

        for doctype in doctypes:
            print(f"Processing DocType: {doctype}")
            metadata = self.conn.get_doctype_meta(doctype) if self.conn else self.get_doctype_static_metadata(doctype)
            if metadata:
                schema = self.generate_doctype_schema(doctype, metadata)
                if schema:
                    spec["components"]["schemas"][doctype] = schema
                    self._add_crud_paths(spec, doctype)

        return spec
    
    def get_doctype_static_metadata(self, doctype: str) -> Optional[Dict]:
        """Get DocType metadata from the static file for production mode"""
        try:
            with open(f"./public/doctype/{doctype}.json", "r") as f:
                metadata = json.load(f)
                return metadata
        except Exception as e:
            print(f"Error loading static metadata for {doctype}: {e}")
            return None
        

    def _add_crud_paths(self, spec: Dict, doctype: str):
        """Add CRUD paths for a DocType to the OpenAPI spec"""
        collection_path = f"/api/resource/{doctype}"
        item_path = f"/api/resource/{doctype}/{{name}}"

        # Collection endpoints (GET, POST)
        spec["paths"][collection_path] = {
            "get": {
                "summary": f"List {doctype} documents",
                "tags": [doctype],
                "parameters": [
                    {
                        "name": "fields",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "Comma-separated list of fields",
                    },
                    {
                        "name": "filters",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "JSON string of filters",
                    },
                    {
                        "name": "limit_start",
                        "in": "query",
                        "schema": {"type": "integer"},
                        "description": "Starting index",
                    },
                    {
                        "name": "limit_page_length",
                        "in": "query",
                        "schema": {"type": "integer"},
                        "description": "Page size",
                    },
                ],
                "responses": {
                    "200": {
                        "description": f"List of {doctype} documents",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {
                                            "type": "array",
                                            "items": {
                                                "$ref": f"#/components/schemas/{doctype}"
                                            },
                                        }
                                    },
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "summary": f"Create {doctype} document",
                "tags": [doctype],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{doctype}"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": f"{doctype} document created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {
                                            "$ref": f"#/components/schemas/{doctype}"
                                        }
                                    },
                                }
                            }
                        },
                    }
                },
            },
        }

        # Item endpoints (GET, PUT, DELETE)
        spec["paths"][item_path] = {
            "get": {
                "summary": f"Get {doctype} document",
                "tags": [doctype],
                "parameters": [
                    {
                        "name": "name",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": f"{doctype} document",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {
                                            "$ref": f"#/components/schemas/{doctype}"
                                        }
                                    },
                                }
                            }
                        },
                    }
                },
            },
            "put": {
                "summary": f"Update {doctype} document",
                "tags": [doctype],
                "parameters": [
                    {
                        "name": "name",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{doctype}"}
                        }
                    },
                },
                "responses": {"200": {"description": f"{doctype} document updated"}},
            },
            "delete": {
                "summary": f"Delete {doctype} document",
                "tags": [doctype],
                "parameters": [
                    {
                        "name": "name",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"202": {"description": f"{doctype} document deleted"}},
            },
        }

# Flask Forms
class ConnectionForm(FlaskForm):
    # Read the environment Variables for the variables
    base_url = StringField(
        "ERPNext URL",
        validators=[DataRequired(), URL()],
        render_kw={"placeholder": "https://your-site.erpnext.com"},
    )
    api_key = StringField(
        "API Key",
        validators=[DataRequired()],
        render_kw={"placeholder": "Your API Key"},
    )
    api_secret = PasswordField(
        "API Secret",
        validators=[DataRequired()],
        render_kw={"placeholder": "Your API Secret"},
    )

class OpenAPIGenerateForm(FlaskForm):
    doctypes = StringField(
        "DocTypes (comma-separated)",
        validators=[DataRequired()],
        render_kw={"placeholder": "Lead,Customer,Item,Sales Order"},
    )
    title = StringField("API Title", default="ERPNext API Documentation")
    version = StringField("API Version", default="1.0.0")
    description = TextAreaField(
        "API Description", default="Auto-generated OpenAPI specification for ERPNext"
    )


# Global connection object (rebuilt from session on each request via before_request)
current_connection: Optional["ERPNextConnection"] = None

_NO_AUTH_ROUTES = {"connect", "index", "static", "disconnect"}


@app.before_request
def restore_or_validate_session():
    """
    Before every request (except connect / static):
    1. Rebuild ERPNextConnection from the Flask session if the global is missing.
    2. Validate the stored credentials are still accepted by Frappe.
    3. If expired or missing, flash a message and redirect to /connect.
    """
    
    if APP_MODE == "production":
        # In production mode, skip all the authentication and session checks
        return
    global current_connection

    # Skip routes that don't need an active connection
    if request.endpoint in _NO_AUTH_ROUTES or request.endpoint is None:
        return

    base_url  = str(session.get("erpnext_url"))
    api_key   = str(session.get("erpnext_api_key"))
    api_secret = str(session.get("erpnext_api_secret"))

    # No credentials in session → send to connect
    if not all([base_url, api_key, api_secret]):
        flash("Please connect to ERPNext first.", "warning")
        return redirect(url_for("connect"))

    # Rebuild connection object if lost (e.g. worker restart)
    if current_connection is None:
        current_connection = ERPNextConnection(base_url, api_key, api_secret)

    # Validate credentials are still accepted by Frappe
    result = validate_session(base_url, api_key, api_secret)
    print("result", result)
    if not result["valid"]:
        current_connection = None
        session.clear()
        reason = result["reason"]
        if reason == "expired":
            flash("Your ERPNext session has expired. Please reconnect.", "warning")
        elif reason == "unreachable":
            flash("ERPNext is unreachable. Please check the URL and reconnect.", "error")
        else:
            flash(f"Connection lost ({reason}). Please reconnect.", "error")
        return redirect(url_for("connect"))

@app.errorhandler(SessionExpiredError)
def handle_session_expired(e):
    """Catch SessionExpiredError raised inside any route and redirect gracefully."""
    if APP_MODE == "production":
        return redirect(url_for("index"))
    global current_connection
    current_connection = None
    session.clear()
    flash(str(e), "warning")
    return redirect(url_for("connect"))


@app.route("/disconnect")
def disconnect():
    """Clear the stored session and return to the connect page."""
    if APP_MODE == "production":
        return redirect(url_for("index"))
    
    global current_connection
    current_connection = None
    session.clear()
    flash("Disconnected successfully.", "success")
    return redirect(url_for("connect"))

@app.route("/")
def index():
    """Home page"""
    return render_template("index.html")

@app.route("/connect", methods=["GET", "POST"])
def connect():
    """Connection setup page"""
    form = ConnectionForm()
    # Pre-fill from environment vars or existing session
    form.base_url.data = session.get("erpnext_url") or ERPNEXT_URL
    form.api_key.data  = session.get("erpnext_api_key") or ERP_API_KEY
    form.api_secret.data = session.get("erpnext_api_secret") or ERP_API_SECRET

    if form.validate_on_submit():
        global current_connection

        base_url   = (form.base_url.data or "").strip()
        api_key    = (form.api_key.data or "").strip()
        api_secret = (form.api_secret.data or "").strip()

        try:
            conn = ERPNextConnection(base_url, api_key, api_secret)
            result = conn.test_connection()

            if result["success"]:
                # Persist credentials in the signed Flask session cookie
                session["erpnext_url"]        = base_url
                session["erpnext_api_key"]    = api_key
                session["erpnext_api_secret"] = api_secret
                current_connection = conn
                flash("Connected successfully!", "success")
                return redirect(url_for("doctypes"))
            else:
                flash(f"Connection failed: {result['message']}", "error")

        except SessionExpiredError as e:
            flash(str(e), "warning")
        except Exception as e:
            flash(f"Connection error: {str(e)}", "error")

    return render_template("connect.html", form=form)

@app.route("/doctypes")
def doctypes():
    """DocTypes listing page"""
    if APP_MODE == "production":
         # In production mode, read from the static file instead of making API calls
        if os.path.exists("./public/doctypes_list.json"):
            with open("./public/doctypes_list.json", "r") as f:
                list_data = json.load(f)
                return render_template("doctypes.html", doctypes = list_data)
        else:
            flash("Invalid Operations.", "warning")
            return redirect(url_for("index"))
    if not current_connection:
        flash("Please connect to ERPNext first", "warning")
        return redirect(url_for("connect"))

    print(f"Fetching list of DocTypes..., {APP_MODE}")   
    doctypes_list = current_connection.get_all_doctypes()
    # Cleanup unnecessary properties fromt the metadata
    return render_template("doctypes.html", doctypes=doctypes_list)

@app.route("/doctype/<doctype_name>")
def doctype_detail(doctype_name):
    """DocType detail page"""
    metadata = None
    if APP_MODE == "production":
        # In production mode, read from the static file instead of making API calls
        if os.path.exists(f"./public/doctype/{doctype_name}.json"):
            with open(f"./public/doctype/{doctype_name}.json", "r") as f:
                metadata = json.load(f)
        else:
            flash("DocType {doctype_name} not found", "warning")
            return redirect(url_for("index"))
    else:
        if not current_connection:
            flash("Please connect to ERPNext first", "warning")
            return redirect(url_for("connect"))

        metadata = current_connection.get_doctype_definition(doctype_name)
        if not metadata:
            flash(f"Could not load DocType: {doctype_name}", "error")
            return redirect(url_for("doctypes"))

    # Extract the fields objects
    fields = metadata.get("fields", [])
    # metadata
    doctype_meta= {
        "name": metadata.get("name"),
        "module": metadata.get("module"),
        "custom": metadata.get("custom"),
        "is_submittable": metadata.get("is_submittable"),
        "is_tree": metadata.get("is_tree"),
        "description": metadata.get("description"),
        "is_submittable": metadata.get("is_submittable"),
        "track_changes": metadata.get("track_changes"),
        "search_fields": metadata.get("search_fields"),
    }
    actual_fields = [
        f
        for f in fields
        if f.get("fieldname")
        and f.get("fieldtype") not in ["Section Break", "Column Break", "HTML","Tab Break"]
    ]
    # Categorize fields
    required_fields = [f for f in actual_fields if f.get("reqd")]
    readonly_fields = [f for f in actual_fields if f.get("read_only")]
    link_fields = [f for f in actual_fields if f.get("fieldtype") == "Link"]

    field_stats = {
        "total": len(actual_fields),
        "required": len(required_fields),
        "readonly": len(readonly_fields),
        "links": len(link_fields),
    }

    # Generate TypeScript-compatible JSON schema
    generator = OpenAPIGenerator(current_connection)
    typescript_json_schema = generator.frappe_fields_to_typescript_json_schema(
        actual_fields
    )
    ts_code = generator.json_schema_to_typescript_interface(
        typescript_json_schema, interface_name=doctype_name + "Schema"
    )

    return render_template(
        "doctype_detail.html",
        doctype_name=doctype_name,
        doctype_doc=doctype_meta,
        ts_code =ts_code,
        fields=actual_fields,
        field_stats=field_stats,
    )

@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat requests with conversation history context"""
    if request.method == "POST" and APP_MODE != "production":
        
        data = request.get_json()
        message: str = data.get("message", "")
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        
        # Initialize session data for new conversations
        if "conversation_id" not in session:
            session["conversation_id"] = str(uuid.uuid4())
            session["conversation_history"] = []
        
        conversation_id = session["conversation_id"]
        user_id = session.get("user_id", "guest")
        
        # Get conversation history from session
        conversation_history = session.get("conversation_history", [])
        
        # Add user message to history
        conversation_history.append({"role": "user", "content": message})
        
        # Store user message in database
        db = AIChatDB()
        db.store_message(session_id=conversation_id, role="user", content=message)
        
        # Convert history to Message objects for Ollama
        messages = [Message(role=msg["role"], content=msg["content"]) for msg in conversation_history]
        
        # Initialize the AI chat class
        chat_app = AIChat()
        
        # Accumulate assistant response for storage
        accumulated_response = ""
        
        # Stream the response directly from the chat generator
        def event_stream():
            nonlocal accumulated_response
            for text_chunk in chat_app.chat(messages=messages):
                if text_chunk:
                    accumulated_response += text_chunk
                    yield text_chunk
            
            # After streaming completes, store assistant response
            if accumulated_response:
                conversation_history.append({"role": "assistant", "content": accumulated_response})
                session["conversation_history"] = conversation_history
                # Current session Id, plus the conversation history
                print(f"Conversation ID: {conversation_id}, History: {conversation_history}")
                db.store_message(role="assistant", content=accumulated_response, session_id=conversation_id)
        
        # Return the response as a stream
        response = Response(stream_with_context(event_stream()), mimetype='text/event-stream')
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Cache-Control'] = 'no-cache'
        return response
    
    return jsonify({"error": "Invalid request method"}), 405

@app.route("/conversation_history", methods=["GET"])
def conversation_history():
    """Retrieve conversation history for the current session"""
    
    if APP_MODE == "production":
        return jsonify({"error": "Conversation history is not available"}), 404
    user_id = session.get("user_id")
    
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    db = AIChatDB()
    conversations = db.retrieve_conversations(user_id=user_id)
    
    return jsonify({"conversations": conversations})

@app.route("/get_message", methods=["GET"])
def get_messages():
    """Retrieve conversation history from database"""
    if APP_MODE == "production":
        return jsonify({"error": "Conversation history is not available"}), 404
    # Get the conversation_id unique to this conversation
    conversation_id = request.args.get("conversation_id")
    # Check if the current user is active and if not, then return a proper error
    user_id = session.get("user_id", "guest")
    if user_id == "guest":
        return jsonify({"error": "User not authenticated"}), 401
    if not conversation_id:
        return jsonify({"error": "Conversation ID is required"}), 400
    
    db = AIChatDB()
    messages = db.retrieve_conversation_messages(conversation_id=conversation_id)
    
    if isinstance(messages, bool):
        return jsonify({"error": "No messages found for this session"}), 404
    
    # Format messages for frontend consumption
    formatted_messages = [
        {
            "message_id": msg[0],
            "role": msg[1],
            "thinking": msg[2],
            "content": msg[3]
        }
        for msg in messages
    ]
    
    return jsonify({"messages": formatted_messages, "user": user_id})


@app.route("/clear_history", methods=["POST"])
def clear_history():
    """Clear conversation history for current session"""
    if APP_MODE == "production":
        return jsonify({"error": "Conversation history is not available"}), 404
    if "conversation_history" in session:
        session["conversation_history"] = []
    if "conversation_id" in session:
        session["conversation_id"] = str(uuid.uuid4())
    
    return jsonify({"success": True, "message": "Conversation history cleared"})


@app.route("/generate-openapi", methods=["GET", "POST"])
def generate_openapi():
    """Generate OpenAPI specification"""
    if APP_MODE == "production":
        flash("OpenAPI generation is not available in production mode.", "warning")
        return redirect(url_for("index"))
    if not current_connection:
        flash("Please connect to ERPNext first", "warning")
        return redirect(url_for("connect"))

    form = OpenAPIGenerateForm()

    if form.validate_on_submit():
        try:
            doctypes_raw = form.doctypes.data or ""
            doctypes = [dt.strip() for dt in doctypes_raw.split(",") if dt.strip()]

            generator = OpenAPIGenerator(current_connection)
            spec = generator.generate_openapi_spec(
                doctypes,
                {
                    "title": form.title.data,
                    "version": form.version.data,
                    "description": form.description.data,
                },
            )

            # Save spec to file for Swagger UI
            os.makedirs("static/swagger", exist_ok=True)
            with open("static/swagger/openapi.json", "w") as f:
                json.dump(spec, f, indent=2)

            flash(
                f"OpenAPI specification generated for {len(doctypes)} DocTypes!",
                "success",
            )
            return redirect(url_for("swagger_ui"))

        except Exception as e:
            flash(f"Error generating OpenAPI spec: {str(e)}", "error")

    return render_template("generate_openapi.html", form=form)


@app.route("/swagger-ui")
def swagger_ui():
    """Swagger UI page"""
    return render_template("swagger_ui.html")


@app.route("/api/doctype/<doctype_name>/metadata")
def api_doctype_metadata(doctype_name: str):
    """API endpoint to get DocType metadata as JSON"""
    if APP_MODE == "production":
        return jsonify({"error": "API access is not available"}), 404
    if not current_connection:
        return jsonify({"error": "No connection established"}), 400

    metadata = current_connection.get_doctype_meta(doctype_name)
    if metadata:
        return jsonify(metadata)
    else:
        return jsonify({"error": f"DocType {doctype_name} not found"}), 404


# New endpoint: Return DocType fields as JSON
@app.route("/api/doctype/<doctype_name>/fields")
def api_doctype_fields(doctype_name):
    """API endpoint to get DocType fields as JSON"""
    if APP_MODE == "production":
        return jsonify({"error": "API access is not available"}), 404
    if not current_connection:
        return jsonify({"error": "No connection established"}), 400

    metadata = current_connection.get_doctype_meta(doctype_name)
    if isinstance(metadata, list):
        return jsonify({"error": f"DocType {doctype_name} not found"}), 404 
    docs = metadata.get("docs", []) if metadata else []
    doctype_doc = docs[0] if docs else {}
    fields = doctype_doc.get("fields", [])
    actual_fields = [
        f
        for f in fields
        if f.get("fieldname")
        and f.get("fieldtype") not in ["Section Break", "Column Break", "HTML"]
    ]
    return jsonify({"fields": actual_fields})


@app.route("/static/swagger/<path:filename>")
def swagger_static(filename):
    if APP_MODE == "production":
        return jsonify({"error": "Not currently available"}), 404
    """Serve swagger static files from swagger"""
    return send_from_directory("static/swagger", filename)


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run()
    app.run()
