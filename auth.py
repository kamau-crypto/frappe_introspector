

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import requests


class SessionExpiredError(Exception):
    """Raised when the stored Frappe credentials are expired or revoked."""
    pass


def validate_session(base_url: str, api_key: str, api_secret: str) -> dict:
    """
    Validate stored API key + secret by pinging Frappe.
    Returns {"valid": bool, "reason": str}

    Possible reasons:
        "ok"            — credentials accepted
        "expired"       — Frappe returned 401 or 403 (token revoked/expired)
        "unreachable"   — could not establish a TCP connection
        "timeout"       — request timed out
        "HTTP <N>"      — unexpected status code
    """
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/api/method/frappe.handler.ping",
            headers={
                "Authorization": f"token {api_key}:{api_secret}",
                "Accept": "application/json",
            },
            timeout=5,
        )
        if response.status_code == 200:
            return {"valid": True, "reason": "ok"}
        elif response.status_code in (401, 403):
            return {"valid": False, "reason": "expired"}
        else:
            return {"valid": False, "reason": f"HTTP {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"valid": False, "reason": "unreachable"}
    except requests.exceptions.Timeout:
        return {"valid": False, "reason": "timeout"}
    except Exception as e:
        return {"valid": False, "reason": str(e)}
