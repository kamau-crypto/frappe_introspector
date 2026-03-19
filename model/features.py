# OFFLINE CHAT FEATURES
# 1. Local LLM Integration: Integrate a local LLM (like Ollama) to allow users to interact with their ERPNext data.
# 2. Contextual Understanding: Enable the LLM to understand the context of the user's queries based on the metadata and structure of their ERPNext instance.
# 3. Interactive Q&A: Allow users to ask questions about their ERPNext data and receive accurate and relevant answers based on the metadata and structure of their instance.
# 4. Data Visualization: Provide visual representations of the data and metadata to help users better understand their ERPNext instance.


# ERPNEXT MODE
# APP MMODE: "erpnext"




# PRODUCTION MODE
# APP MODE: "production"




def monitor_features(app_mode):
    """Monitor and manage feature flags based on the application mode."""
 
    FEATURE_STATE= {
        "OPEN_API DOCS": False,
        "SWAGGER_UI": False,
        "THEME_TOGGLE": True,
        "CONNECT_TO_INSTANCE": True,
        "PRODUCTION_ASSETS_READY": True,
        "FAQ_PAGE": False,
        "AI_ASSISTANT": True,
        "CHAT_MODE": False,
        "DOCTYPE_FILTERING": True,
        "RATE_LIMITING": True,
    }
        
    ERPNEXT_FLAGS = {
        "CHAT_MODE": False,
        "CONNECT_TO_INSTANCE": True,
        "API_DOCS":False,
        "SWAGGER_UI": False,
        "FAQ_PAGE": False,
        "AI_ASSISTANT":False,
        "AI_ASSISTANTS": [],
    }
    
    PRODUCTION_FLAGS={
    "CHAT_MODE": False,
    "API_DOCS": False,
    "SWAGGER_UI": False,
    "CONNECT_TO_INSTANCE": False,
    "FAQ_PAGE": False,
    "AI_ASSISTANT": True,
    "AI_ASSISTANTS": ["Claude", "ChatGPT"],
    }
    
    if app_mode == "erpnext":
        return ERPNEXT_FLAGS
    elif app_mode == "production":
        return PRODUCTION_FLAGS
    else:
        raise ValueError(f"Unknown MODE: {app_mode}")

def feature_marker(badge_type: str = "coming_soon") -> str:
    """Marker function that checks the feature flags and returns a feature marker html template to
    be rendered in the frontend. This can be used to conditionally display a message or badge
    indicating that a feature is in development or not available in the current mode.

    Args:
        badge_type: Either 'coming_soon' or 'erpnext_mode'.

    Returns:
        An HTML string for the badge, safe to render with |safe in Jinja2.
    """
    badges = {
        "coming_soon": (
            '<span class="feature-badge feature-badge--coming-soon">'
            '<i class="fas fa-clock"></i>'
            '&nbsp;Coming Soon'
            '</span>'
        ),
        "erpnext_mode": (
            '<span class="feature-badge feature-badge--erpnext">'
            '<i class="fas fa-plug"></i>'
            '&nbsp;ERPNext Mode'
            '</span>'
        ),
    }
    return badges.get(badge_type, badges["coming_soon"])

