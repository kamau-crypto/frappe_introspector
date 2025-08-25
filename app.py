
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()
import requests
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_wtf import FlaskForm
from werkzeug.exceptions import RequestEntityTooLarge
from wtforms import PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import URL, DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload

class ERPNextConnection:
    """Handles connections and API calls to ERPNext instances"""
    
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'token {api_key}:{api_secret}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to ERPNext"""
        try:
            response = requests.get(
                f'{self.base_url}/api/method/frappe.handler.ping',
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return {'success': True, 'message': 'Connection successful'}
            else:
                return {'success': False, 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_doctype_meta(self, doctype: str) -> Optional[Dict]:
        """Get DocType metadata using the working whitelisted method"""
        try:
            response = requests.get(
                f'{self.base_url}/api/method/frappe.desk.form.load.getdoctype',
                params={'doctype': doctype},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('message', {})
            else:
                print(f"Error getting metadata for {doctype}: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception getting metadata for {doctype}: {e}")
            return None
    
    def get_all_doctypes(self) -> List[Dict]:
        """Get all available DocTypes"""
        try:
            response = requests.get(
                f'{self.base_url}/api/resource/DocType',
                params={
                    'fields': '["name","module","custom","is_submittable","is_tree","description"]',
                    'limit_page_length': 0
                },
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            return []
        except Exception as e:
            print(f"Exception getting all DocTypes: {e}")
            return []
    
    def get_doctype_definition(self, doctype: str) -> Optional[Dict]:
        """Get the raw DocType definition"""
        try:
            response = requests.get(
                f'{self.base_url}/api/resource/DocType/{doctype}',
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # print (f"DocType definition for {doctype}: {data}")
                return data.get('data', {})
            return None
        except Exception as e:
            print(f"Exception getting DocType definition for {doctype}: {e}")
            return None

class OpenAPIGenerator:
    def json_schema_to_typescript_interface(self, schema: Dict, interface_name: str = "DocTypeSchema") -> str:
        """Generate TypeScript interface from JSON schema, formatted for display"""
        properties = schema.get('properties', {})
        required = set(schema.get('required', []))
        enums = []
        enum_order = []
        lines = [f"export interface {interface_name} {{"]
        for prop, details in properties.items():
            ts_type = "any"
            if details.get('type') == 'string':
                ts_type = 'string'
            elif details.get('type') == 'integer':
                ts_type = 'number'
            elif details.get('type') == 'number':
                ts_type = 'number'
            elif details.get('type') == 'boolean':
                ts_type = 'boolean'
            elif details.get('type') == 'array':
                item_type = 'any'
                if details.get('items', {}).get('type'):
                    if details['items']['type'] == 'object':
                        item_type = 'Record<string, any>'
                    else:
                        item_type = details['items']['type']
                ts_type = f"{item_type}[]"
            elif details.get('type') == 'object':
                ts_type = 'Record<string, any>'

            # Handle enums
            if 'enum' in details:
                enum_name = f"{prop[0].upper() + prop[1:]}Enum"
                enum_values = details['enum']
                formatted_values = []
                for v in enum_values:
                    if isinstance(v, str):
                        formatted_values.append(f"'{v}'")
                    else:
                        formatted_values.append(str(v))
                enum_def = f"export enum {enum_name} {{ " + ", ".join(formatted_values) + " }"
                enums.append(enum_def)
                enum_order.append(enum_name)
                ts_type = enum_name

            # Optional if not required
            optional = '?' if prop not in required else ''
            lines.append(f"  {prop}{optional}: {ts_type};")
        lines.append("}")
        # Add enums above interface, separated by two newlines
        return "\n\n".join(enums + ["\n".join(lines)])
    def frappe_fields_to_typescript_json_schema(self, fields: List[Dict]) -> Dict:
        """Generate a TypeScript-compatible JSON schema from Frappe fields"""
        schema = {
            'type': 'object',
            'properties': {},
            'required': []
        }
        for field in fields:
            if not field.get('fieldname') or field.get('fieldtype') in ['Section Break', 'Column Break', 'HTML']:
                continue
            fieldname = field['fieldname']
            property_def = self.map_frappe_field_to_openapi(field)
            schema['properties'][fieldname] = property_def
            if field.get('reqd'):
                schema['required'].append(fieldname)
        return schema
    """Generates OpenAPI specifications from ERPNext DocTypes"""
    
    def __init__(self, erpnext_conn: ERPNextConnection):
        self.conn = erpnext_conn
    
    def map_frappe_field_to_openapi(self, field: Dict) -> Dict:
        """Map Frappe field types to OpenAPI schema properties"""
        property_def = {
            'description': field.get('label', field.get('fieldname', ''))
        }
        
        # Add read-only flag
        if field.get('read_only'):
            property_def['readOnly'] = True
        
        # Add default value
        if field.get('default'):
            property_def['default'] = field['default']
        
        # Map field types
        fieldtype = field.get('fieldtype', 'Data')
        
        field_type_mapping = {
            'Data': {'type': 'string'},
            'Small Text': {'type': 'string'},
            'Long Text': {'type': 'string'},
            'Text Editor': {'type': 'string'},
            'Text': {'type': 'string', 'maxLength': 65535},
            'Code': {'type': 'string'},
            'Int': {'type': 'integer'},
            'Float': {'type': 'number', 'format': 'float'},
            'Currency': {'type': 'number', 'format': 'float'},
            'Percent': {'type': 'number', 'format': 'float'},
            'Check': {'type': 'integer', 'enum': [0, 1]},
            'Select': {'type': 'string'},
            'Link': {'type': 'string'},
            'Date': {'type': 'string', 'format': 'date'},
            'Datetime': {'type': 'string', 'format': 'date-time'},
            'Time': {'type': 'string', 'format': 'time'},
            'Password': {'type': 'string', 'format': 'password', 'writeOnly': True},
            'Attach': {'type': 'string', 'format': 'uri'},
            'Attach Image': {'type': 'string', 'format': 'uri'},
            'Table': {'type': 'array', 'items': {'type': 'object'}},
            'JSON': {'type': 'object'},
            'HTML': {'type': 'string'},
            'Signature': {'type': 'string'},
            'Color': {'type': 'string', 'pattern': '^#[0-9A-Fa-f]{6}$'},
            'Barcode': {'type': 'string'},
            'Geolocation': {'type': 'string'}
        }
        
        property_def.update(field_type_mapping.get(fieldtype, {'type': 'string'}))
        
        # Handle Select options
        if fieldtype == 'Select' and field.get('options'):
            options = [opt.strip() for opt in field['options'].split('\n') if opt.strip()]
            if options:
                property_def['enum'] = options
        
        # Handle Link field description
        if fieldtype == 'Link' and field.get('options'):
            property_def['description'] += f" (Links to {field['options']})"
        
        return property_def
    
    def generate_doctype_schema(self, doctype: str, metadata: Dict) -> Dict:
        """Generate OpenAPI schema for a DocType"""
        docs = metadata.get('docs', [])
        if not docs:
            return {}
        
        doctype_doc = docs[0]  # Main DocType document
        fields = doctype_doc.get('fields', [])
        
        schema = {
            'type': 'object',
            'properties': {
                # Standard Frappe document properties
                'name': {'type': 'string', 'description': 'Document ID/name', 'readOnly': True},
                'owner': {'type': 'string', 'description': 'Document owner', 'readOnly': True},
                'creation': {'type': 'string', 'format': 'date-time', 'readOnly': True},
                'modified': {'type': 'string', 'format': 'date-time', 'readOnly': True},
                'modified_by': {'type': 'string', 'readOnly': True},
                'docstatus': {'type': 'integer', 'enum': [0, 1, 2], 'readOnly': True},
                'doctype': {'type': 'string', 'readOnly': True}
            },
            'required': []
        }
        
        # Process fields
        for field in fields:
            if not field.get('fieldname') or field.get('fieldtype') in ['Section Break', 'Column Break', 'HTML']:
                continue
            
            fieldname = field['fieldname']
            property_def = self.map_frappe_field_to_openapi(field)
            schema['properties'][fieldname] = property_def
            
            # Add to required fields if mandatory
            if field.get('reqd'):
                schema['required'].append(fieldname)
        
        return schema
    
    def generate_openapi_spec(self, doctypes: List[str], info: Dict = {}) -> Dict:
        """Generate complete OpenAPI specification"""
        spec = {
            'openapi': '3.0.3',
            'info': {
                'title': info.get('title', 'ERPNext API'),
                'description': info.get('description', 'Auto-generated OpenAPI specification for ERPNext'),
                'version': info.get('version', '1.0.0')
            },
            'servers': [
                {'url': self.conn.base_url, 'description': 'ERPNext Server'}
            ],
            'components': {
                'securitySchemes': {
                    'ApiKeyAuth': {
                        'type': 'apiKey',
                        'in': 'header',
                        'name': 'Authorization',
                        'description': 'Use "token api_key:api_secret"'
                    }
                },
                'schemas': {}
            },
            'security': [{'ApiKeyAuth': []}],
            'paths': {}
        }
        
        for doctype in doctypes:
            print(f"Processing DocType: {doctype}")
            metadata = self.conn.get_doctype_meta(doctype)
            if metadata:
                schema = self.generate_doctype_schema(doctype, metadata)
                if schema:
                    spec['components']['schemas'][doctype] = schema
                    self._add_crud_paths(spec, doctype)
        
        return spec
    
    def _add_crud_paths(self, spec: Dict, doctype: str):
        """Add CRUD paths for a DocType to the OpenAPI spec"""
        collection_path = f'/api/resource/{doctype}'
        item_path = f'/api/resource/{doctype}/{{name}}'
        
        # Collection endpoints (GET, POST)
        spec['paths'][collection_path] = {
            'get': {
                'summary': f'List {doctype} documents',
                'tags': [doctype],
                'parameters': [
                    {'name': 'fields', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'Comma-separated list of fields'},
                    {'name': 'filters', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'JSON string of filters'},
                    {'name': 'limit_start', 'in': 'query', 'schema': {'type': 'integer'}, 'description': 'Starting index'},
                    {'name': 'limit_page_length', 'in': 'query', 'schema': {'type': 'integer'}, 'description': 'Page size'}
                ],
                'responses': {
                    '200': {
                        'description': f'List of {doctype} documents',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'data': {
                                            'type': 'array',
                                            'items': {'$ref': f'#/components/schemas/{doctype}'}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            'post': {
                'summary': f'Create {doctype} document',
                'tags': [doctype],
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {'$ref': f'#/components/schemas/{doctype}'}
                        }
                    }
                },
                'responses': {
                    '200': {
                        'description': f'{doctype} document created',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'data': {'$ref': f'#/components/schemas/{doctype}'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Item endpoints (GET, PUT, DELETE)
        spec['paths'][item_path] = {
            'get': {
                'summary': f'Get {doctype} document',
                'tags': [doctype],
                'parameters': [
                    {'name': 'name', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
                ],
                'responses': {
                    '200': {
                        'description': f'{doctype} document',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'data': {'$ref': f'#/components/schemas/{doctype}'}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            'put': {
                'summary': f'Update {doctype} document',
                'tags': [doctype],
                'parameters': [
                    {'name': 'name', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
                ],
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {'$ref': f'#/components/schemas/{doctype}'}
                        }
                    }
                },
                'responses': {
                    '200': {
                        'description': f'{doctype} document updated'
                    }
                }
            },
            'delete': {
                'summary': f'Delete {doctype} document',
                'tags': [doctype],
                'parameters': [
                    {'name': 'name', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
                ],
                'responses': {
                    '202': {
                        'description': f'{doctype} document deleted'
                    }
                }
            }
        }

# Flask Forms
class ConnectionForm(FlaskForm):
    base_url = StringField('ERPNext URL', validators=[DataRequired(), URL()], 
                          render_kw={"placeholder": "https://your-site.erpnext.com"})
    api_key = StringField('API Key', validators=[DataRequired()],
                         render_kw={"placeholder": "Your API Key"})
    api_secret = PasswordField('API Secret', validators=[DataRequired()],
                              render_kw={"placeholder": "Your API Secret"})

class OpenAPIGenerateForm(FlaskForm):
    doctypes = StringField('DocTypes (comma-separated)', validators=[DataRequired()],
                          render_kw={"placeholder": "Lead,Customer,Item,Sales Order"})
    title = StringField('API Title', default='ERPNext API Documentation')
    version = StringField('API Version', default='1.0.0')
    description = TextAreaField('API Description', 
                               default='Auto-generated OpenAPI specification for ERPNext')

# Global connection object
current_connection = None

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/connect', methods=['GET', 'POST'])
def connect():
    """Connection setup page"""
    form = ConnectionForm()
    
    if form.validate_on_submit():
        global current_connection
        
        try:
            # Test connection
            conn = ERPNextConnection(
                (form.base_url.data or '').strip(),
                (form.api_key.data or '').strip(),
                (form.api_secret.data or '').strip()
            )
            
            result = conn.test_connection()
            if result['success']:
                current_connection = conn
                flash('Connected successfully!', 'success')
                return redirect(url_for('doctypes'))
            else:
                flash(f'Connection failed: {result["message"]}', 'error')
        
        except Exception as e:
            flash(f'Connection error: {str(e)}', 'error')
    
    return render_template('connect.html', form=form)

@app.route('/doctypes')
def doctypes():
    """DocTypes listing page"""
    if not current_connection:
        flash('Please connect to ERPNext first', 'warning')
        return redirect(url_for('connect'))
    
    doctypes_list = current_connection.get_all_doctypes()
    return render_template('doctypes.html', doctypes=doctypes_list)

@app.route('/doctype/<doctype_name>')
def doctype_detail(doctype_name):
    """DocType detail page"""
    if not current_connection:
        flash('Please connect to ERPNext first', 'warning')
        return redirect(url_for('connect'))
    
    metadata = current_connection.get_doctype_definition(doctype_name)
    if not metadata:
        flash(f'Could not load DocType: {doctype_name}', 'error')
        return redirect(url_for('doctypes'))
    
    # Extract useful information
    fields = metadata.get('fields', [])
    actual_fields = [f for f in fields if f.get('fieldname') and f.get('fieldtype') not in ['Section Break', 'Column Break', 'HTML']]

    # Categorize fields
    required_fields = [f for f in actual_fields if f.get('reqd')]
    readonly_fields = [f for f in actual_fields if f.get('read_only')]
    link_fields = [f for f in actual_fields if f.get('fieldtype') == 'Link']

    field_stats = {
        'total': len(actual_fields),
        'required': len(required_fields),
        'readonly': len(readonly_fields),
        'links': len(link_fields)
    }

    # Generate TypeScript-compatible JSON schema
    generator = OpenAPIGenerator(current_connection)
    typescript_json_schema = generator.frappe_fields_to_typescript_json_schema(actual_fields)
    ts_code= generator.json_schema_to_typescript_interface(typescript_json_schema, interface_name=doctype_name + "Schema")

    return render_template('doctype_detail.html', 
                         doctype_name=doctype_name,
                         doctype_doc=ts_code,
                         fields=actual_fields,
                         field_stats=field_stats)

@app.route('/generate-openapi', methods=['GET', 'POST'])
def generate_openapi():
    """Generate OpenAPI specification"""
    if not current_connection:
        flash('Please connect to ERPNext first', 'warning')
        return redirect(url_for('connect'))
    
    form = OpenAPIGenerateForm()
    
    if form.validate_on_submit():
        try:
            doctypes_raw = form.doctypes.data or ''
            doctypes = [dt.strip() for dt in doctypes_raw.split(',') if dt.strip()]
            
            generator = OpenAPIGenerator(current_connection)
            spec = generator.generate_openapi_spec(doctypes, {
                'title': form.title.data,
                'version': form.version.data,
                'description': form.description.data
            })
            
            # Save spec to file for Swagger UI
            os.makedirs('static/swagger', exist_ok=True)
            with open('static/swagger/openapi.json', 'w') as f:
                json.dump(spec, f, indent=2)
            
            flash(f'OpenAPI specification generated for {len(doctypes)} DocTypes!', 'success')
            return redirect(url_for('swagger_ui'))
        
        except Exception as e:
            flash(f'Error generating OpenAPI spec: {str(e)}', 'error')
    
    return render_template('generate_openapi.html', form=form)

@app.route('/swagger-ui')
def swagger_ui():
    """Swagger UI page"""
    return render_template('swagger_ui.html')

@app.route('/api/doctype/<doctype_name>/metadata')
def api_doctype_metadata(doctype_name):
    """API endpoint to get DocType metadata as JSON"""
    if not current_connection:
        return jsonify({'error': 'No connection established'}), 400
    
    metadata = current_connection.get_doctype_meta(doctype_name)
    if metadata:
        return jsonify(metadata)
    else:
        return jsonify({'error': f'DocType {doctype_name} not found'}), 404

# New endpoint: Return DocType fields as JSON
@app.route('/api/doctype/<doctype_name>/fields')
def api_doctype_fields(doctype_name):
    """API endpoint to get DocType fields as JSON"""
    if not current_connection:
        return jsonify({'error': 'No connection established'}), 400

    metadata = current_connection.get_doctype_meta(doctype_name)
    docs = metadata.get('docs', []) if metadata else []
    doctype_doc = docs[0] if docs else {}
    fields = doctype_doc.get('fields', [])
    actual_fields = [f for f in fields if f.get('fieldname') and f.get('fieldtype') not in ['Section Break', 'Column Break', 'HTML']]
    return jsonify({'fields': actual_fields})

@app.route('/static/swagger/<path:filename>')
def swagger_static(filename):
    """Serve swagger static files"""
    return send_from_directory('static/swagger', filename)

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Use watchdog to auto-reload Flask app on file changes
    try:
        import threading
        import time

        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class ReloadHandler(FileSystemEventHandler):
            def __init__(self, restart_func):
                self.restart_func = restart_func
            def on_modified(self, event):
                # Only restart on file modification events for .py files
                if event.is_directory:
                    # made some change
                    return
                if str(event.src_path).endswith('.py'):
                    print(f"Detected change in {event.src_path}, restarting Flask app...")
                    self.restart_func()

        def run_flask():
            app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

        def restart_flask():
            os._exit(3)  # Triggers restart if run with 'flask run' or similar

        event_handler = ReloadHandler(restart_flask)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.abspath('.'), recursive=True)
        observer.start()
        try:
            run_flask()
        finally:
            observer.stop()
            observer.join()
    except ImportError:
        print("watchdog not installed. Run 'pip install watchdog' for auto-reload support.")
        app.run(debug=True, host='0.0.0.0', port=5000)