# Uses json5 to allow comments in the config file
import json5
# Uses json when updating files that don't need comment - includes "" around keys
import json
import logging
from vlcbserver.config import Config

logger = logging.getLogger(__name__)

def load_settings(default_path, custom_path):
    # Load defaults first
    try:
        with open(default_path, 'r') as f:
            settings = json5.load(f)
    except FileNotFoundError:
        print(f"Critical: '{default_path}' not found. Cannot start without defaults.")
        return {}
    except ValueError as e:
        print(f"Critical: '{default_path}' is not valid JSON5. Error: {e}")
        return {}

    # Check for custom settings and override (using pathlib's .exists())
    if custom_path.exists():
        try:
            with open(custom_path, 'r') as f:
                custom_settings = json5.load(f)
                
            # Merge the dicts, overwriting defaults with custom values
            settings.update(custom_settings)
            
        except ValueError as e:
            print(f"Warning: '{custom_path}' contains invalid JSON5. Ignoring custom overrides. Error: {e}")
            
    return settings


def get_config(cfg):
    " Setups up the config and loads in the settings"
        # Load the settings - using default filenames
    # could update to use commandline filenames in future if required
    config = load_settings(cfg.DEFAULT_SETTINGS, cfg.CUSTOM_SETTINGS)

    # Add paths to config if required elsewhere
    config.update({
        'BASE_DIR': cfg.BASE_DIR,
        'CONFIG_DIR': cfg.CONFIG_DIR,
        'SERVER_JSON': cfg.CUSTOM_SETTINGS,
        # Flask-SQLAlchemy expects a URI string. Uses an f-string to inject the Path.
        'SQLALCHEMY_DATABASE_URI': f"sqlite:///{cfg.DATABASE_PATH}",
        # Disabling this saves memory and suppresses a warning
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        # Log details
        'LOG_PATH' : cfg.LOG_PATH,
        'LOGLEVEL_CONSOLE': cfg.LOGLEVEL_CONSOLE,
        'LOGLEVEL_FILE': cfg.LOGLEVEL_FILE
        })

    return config

def cfg_checks(cfg):
    """ These are checks run during server startup. If 
    these are not configured and don't exist """

    # Check the database exists
    # Doesn't check a user - that comes later in the create_app
    if not cfg.DATABASE_PATH.exists():
        print("ERROR: The database file does not exist.")
        print(f"Please run the setup step {cfg.SETUP_CMD} before starting the app.")
        # If failed then cancel application - returning False will result in sys.exit
        return False
        

    # Create the log dir if not already exist - and it's local (not overridden with /var/log etc.)
    if cfg.LOG_DIR == cfg.BASE_DIR / 'logs':
        cfg.LOG_DIR.mkdir(exist_ok=True)

    # If checks passed then return true
    return True

""" Update the settings in server.json """
""" Any existing entries in server.json are maintained unless included
in the new settings in which case replaced with new settings"""
# Sets the settings into both current_app and then saves into server.json
# If custom directory is set then it updates that one, if not then default
def update_server_settings(new_settings):
    # Import current_app here as other functions run before current_app set
    from flask import current_app

    # merge into current app first
    # Note if fails then they are still updated locally just save fails
    current_app.config.update(new_settings)

    custom_path = current_app.config.get("SERVER_JSON")
    # Load the current custom settings
    if custom_path.exists():
        try:
            with open(custom_path, 'r') as f:
                custom_settings = json5.load(f)
                
        except ValueError as e:
            logger.warning(f"Warning: '{custom_path}' contains invalid JSON5. Read / Update failed. Error: {e}")
            return False

        # Merge the dicts, overwriting values loaded from custom settings
        custom_settings.update(new_settings)

    # If not then create new file with new_settings
    else:
        custom_settings = new_settings

    # Write the settings back 
    # Note that this will lose any comments - saved as standard json
    try:
        with open(custom_path, 'w') as f:
            json.dump(custom_settings, f, indent=4)

    except Exception as e:
        logger.warning (f"Error Saving custom server settings file {custom_path} {e}")
        return False

    return True
