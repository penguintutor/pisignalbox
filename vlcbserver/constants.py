# Fixed constants for server config
# These are not expected to change

# Translate stored / IT type roles to railway roles
ROLES ={
        "reader":   "Observer",             # Read Only
        "operator": "Signaller",            # control existing layout
        "update":   "Layout Engineer",      # Can update layout etc.
        "admin":    "Operations Manager"    # All above + user admin
}