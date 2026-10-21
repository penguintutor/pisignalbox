# Fixed constants for server config
# These are not expected to change

# Translate stored / IT type roles to railway roles
ROLES ={
        "reader":   "Observer",             # Read Only
        "operator": "Signaller",            # control existing layout
        "update":   "Layout Engineer",      # Can update layout etc.
        "admin":    "Operations Manager"    # All above + user admin
}

# Lists of which roles have appropriate permission
OPERATOR_ROLES = ["operator", "update", "admin"]

# These are constant as not currently configurable
# possibility to include as configuration option in future

# How to handle ERR loco in use when by a different CBUS
# controller - eg. handset. 
# Currently just use share, consider option for steal or prompt 
# in future
STEAL_SHARE_LOCO = "share"