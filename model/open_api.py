import json
from typing import Any, Dict, List, Optional

from erpnext import ERPNextConnection


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

