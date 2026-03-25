import json
import os
from typing import Any

from flask import flash, redirect, url_for

from model.erpnext import ERPNextConnection
from model.redis.cache import cache_result


@cache_result(key_prefix="doctype", ttl=300)
def _load_doctype_details(doctype_name, APP_MODE, current_connection):
    """ A helper function to load the doctype details from the redis cache if they exist, the file, or the ERPNext instance."""
    if APP_MODE == "production":
        # In production mode, read from the static file instead of making API calls
        if os.path.exists(f"./public/doctype/{doctype_name}.json"):
            with open(f"./public/doctype/{doctype_name}.json", "r") as f:
                return json.load(f)
        else:
            # flash("DocType {doctype_name} not found", "warning")
            # return redirect(url_for("index"))
            return None
    else:
        if not current_connection:
            # flash("Please connect to ERPNext first", "warning")
            # return redirect(url_for("connect"))
            return None
        return  current_connection.get_doctype_definition(doctype_name)
    
@cache_result(key_prefix="doctype_list", ttl=300)
def _load_doctype_list(APP_MODE, current_connection: 
    ERPNextConnection | None, module: str | None = None)-> Any | None:
    """ A helper function to load the list of doctypes from the redis cache if they exist, the file, or the ERPNext instance."""
    
    if APP_MODE == "production":
         # In production mode, read from the static file instead of making API calls
        if os.path.exists("./public/doctypes_list.json"):
            with open("./public/doctypes_list.json", "r") as f:
                return json.load(f)
        else:
            return None
    else:
        if not current_connection:
            return None
        return current_connection.get_all_doctypes(module)
