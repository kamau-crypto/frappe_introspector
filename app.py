import json
import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from flask import (Flask, Response, flash, g, jsonify, make_response, redirect,
                   render_template, request, send_from_directory, session,
                   stream_with_context, url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import FlaskForm
from ollama import Message
from wtforms import PasswordField, StringField, TextAreaField
from wtforms.validators import URL, DataRequired

from model.ai import AIChat
from model.auth import SessionExpiredError, validate_session
from model.db import AIChatDB
from model.doctype import _load_doctype_details, _load_doctype_list
from model.erpnext import ERPNextConnection
from model.features import feature_marker, monitor_features
from model.open_api import OpenAPIGenerator
from model.redis.cache import cache_result
from model.redis.connect import get_redis_client

load_dotenv()

ERPNEXT_URL = os.environ.get("ERPNEXT_URL", "http://127.0.0.1:8000")
ERP_API_KEY = os.environ.get("ERP_API_KEY", None)
ERP_API_SECRET = os.environ.get("ERP_API_SECRET", None)
APP_MODE = os.environ.get("MODE", "erpnext")  # "erpnext" or "production"

app = Flask(__name__)
app.jinja_env.globals["feature_marker"] = feature_marker
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "erpnextinspectorsecretkey")
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1MB max file upload
app.config["APP_MODE"] = APP_MODE


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
#  Replace this with a redis consistent cache in the future if needed for scalability across multiple workers or instances.
current_connection: Optional["ERPNextConnection"] = None

_NO_AUTH_ROUTES = {"connect", "index", "static", "disconnect"}


limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "60 per hour"],
    storage_uri="redis://localhost:6379",
    storage_options={"socket_connect_timeout": 30},
    strategy="sliding-window-counter",
)



@app.before_request
def restore_or_validate_session():
    """
    Before every request (except connect / static):
    1. Rebuild ERPNextConnection from the Flask session if the global is missing.
    2. Validate the stored credentials are still accepted by Frappe.
    3. If expired or missing, flash a message and redirect to /connect.
    """
    # Get the redis client
    g.redis = get_redis_client()
    if APP_MODE == "production":
        # In production mode, skip all the authentication and session checks
        app.config["FEATURE"] = monitor_features(APP_MODE)
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
        current_connection = ERPNextConnection(base_url, api_key, api_secret, APP_MODE)

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
    if APP_MODE == "production":
        flash("Connection setup is not available in production mode.", "warning")
        return redirect(url_for("index"))
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
            conn = ERPNextConnection(base_url, api_key, api_secret, APP_MODE)
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



@app.route("/doctypes", methods=["GET"])
@limiter.limit("10/minute", override_defaults=False)
def doctypes():
    """DocTypes listing page"""
    module= request.args.get("module", None)
    
    doc_list= _load_doctype_list(APP_MODE, current_connection, module)
    if APP_MODE == "production":
         # In production mode, read from the static file instead of making API calls
        if not doc_list:
            flash("Invalid Operations.", "warning")
            return redirect(url_for("index"))
    else:
        if not current_connection and not doc_list:
            flash("Please connect to ERPNext first", "warning")
            return redirect(url_for("connect"))
    print("doc_list", isinstance(doc_list, str))
    # doctypes_list = doc_list.get("data", []) if doc_list else []
    doctypes_list = doc_list if doc_list else []
    return render_template("doctypes.html", doctypes=doctypes_list, module=module)

@app.route("/doctype/<doctype_name>")
@limiter.limit("1/second", override_defaults= False)
def doctype_detail(doctype_name):
    """DocType detail page"""
    metadata= _load_doctype_details(doctype_name, APP_MODE, current_connection)
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
@limiter.limit("0/minute", override_defaults=False)
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

@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    # API routes get a JSON response; page routes get the HTML template.
    if request.path.startswith("/api/"):
        return make_response(jsonify(error=f"Too Many Requests"), 429)
    return make_response(render_template("rate_limit.html", request_limit=e), 429)

@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run()
