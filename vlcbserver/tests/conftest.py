# tests/conftest.py
import pytest
import logging
from pathlib import Path
from vlcbserver import create_app

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "vlcbserver" / "settings"

# These are the config files - fixed filenames
# Future: could have an option to call a different filename but not
# supported at the moment
DEFAULT_SETTINGS = CONFIG_DIR / "defaults.json"
CUSTOM_SETTINGS = CONFIG_DIR / "server.json"

# Database is in the instances directory - holds user details etc.
INSTANCE_DIR = BASE_DIR / 'instances'
DATABASE_PATH = INSTANCE_DIR / 'users.db'

# String for setup command - used to inform user how to add user
SETUP_CMD = "setup/setup_auth.py"

# Future: Consider overriding using config file or environment variables
LOGLEVEL_CONSOLE = logging.WARNING
LOGLEVEL_FILE = logging.INFO

LOG_DIR = BASE_DIR / 'logs'
LOG_PATH = LOG_DIR / 'vlcbserver.log'

@pytest.fixture
def app():
    # Create the app using your factory
    config = {}
    config.update({
            # Flask-SQLAlchemy expects a URI string. Uses an f-string to inject the Path.
            'SQLALCHEMY_DATABASE_URI': f"sqlite:///{DATABASE_PATH}",
            # Disabling this saves memory and suppresses a warning
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            # Log details
            'LOG_PATH' : LOG_PATH,
            'LOGLEVEL_CONSOLE': LOGLEVEL_CONSOLE,
            'LOGLEVEL_FILE': LOGLEVEL_FILE
            })
    app = create_app(config)
    app.config.update({
        "TESTING": True,
    })
    #yield app
    return app