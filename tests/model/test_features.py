
from model.features import feature_marker, monitor_features


def test_monitor_features():
    # When In erpnext mode
    erpnext_flags= monitor_features("erpnext")
    
    assert erpnext_flags["CHAT_MODE"] == False, "Chat mode should be disabled in erpnext mode"
    assert erpnext_flags["CONNECT_TO_INSTANCE"] == True, "Connect to instance should be enabled in erpnext mode"
    assert erpnext_flags["API_DOCS"] == False, "API docs should be disabled in erpnext mode"
    assert erpnext_flags["SWAGGER_UI"] == False, "Swagger UI should be disabled in erpnext mode"
    assert erpnext_flags["FAQ_PAGE"] == False, "FAQ page should be disabled in erpnext mode"
    assert erpnext_flags["AI_ASSISTANT"] == False, "AI assistant should be disabled in erpnext mode"
    assert len(erpnext_flags["AI_ASSISTANTS"]) ==0, "There should be no AI assistants in erpnext mode"
    
    
    # when we are in production mode
    production_flags= monitor_features("production")
    assert production_flags["CHAT_MODE"] == False, "Chat mode should be disabled in production mode"
    assert production_flags["CONNECT_TO_INSTANCE"] == False, "Connect to instance should be disabled in production mode"
    assert production_flags["API_DOCS"] == False, "API docs should be disabled in production mode"
    assert production_flags["SWAGGER_UI"] == False, "Swagger UI should be disabled in production mode"
    assert production_flags["FAQ_PAGE"] == False, "FAQ page should be disabled in production mode"
    assert production_flags["AI_ASSISTANT"] == True, "AI assistant should be enabled in production mode"
    assert len(production_flags["AI_ASSISTANTS"]) ==2
    
    
def test_feature_marker():
    # Test the feature marker function with default badge type
    default_marker = feature_marker()
    assert default_marker, "Default marker should not be empty"
    assert issubclass(type(default_marker), str), "Badge type value should be a string"
    assert "Coming Soon" in default_marker, "Default badge type should be 'coming_soon'"
    
    # Test the feature marker function with custom badge type. For example, "new". It should not 
    # exist
    custom_marker = feature_marker("new")
    assert custom_marker, "Custom marker should not be empty"
    assert issubclass(type(custom_marker), str), "Badge type value should be a string"
    assert "New" not in custom_marker, "Custom badge type should be 'Coming Soon'"
    assert "Coming Soon" in custom_marker, "Custom badge type should default to 'coming_soon' if unknown badge type is provided"