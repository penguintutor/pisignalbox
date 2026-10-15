# Imports other libraries that are shared across the application

from pyvlcb import VLCB

# Create a singleton instance of the VLCB so it can be used
# across all different routes - rather than having to create multiple 
# instances
# Note this uses default can_id - if need alternative then that
# can be updated in app_config()
vlcb = VLCB()