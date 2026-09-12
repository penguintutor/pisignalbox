# Uses json5 to allow comments in the config file
import json5
from vlcbserver.config import Config


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

