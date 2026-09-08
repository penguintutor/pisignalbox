## Script for Debugging purposes only
import json
from sqlalchemy import inspect, text
from vlcbserver import create_app
from vlcbserver.core.models import db
import logging
from pathlib import Path

# Adjust this with whatever configuration you pass to create_app
#from config import config  # Or pass your standard config dict

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

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    print(f"\n{'='*20} DATABASE DUMP {'='*20}")
    for table_name in tables:
        print(f"\n[TABLE] {table_name}")
        print("-" * (8 + len(table_name)))

        # Fetch all rows as key-value mappings
        result = (
            db.session.execute(text(f'SELECT * FROM "{table_name}"'))
            .mappings()
            .all()
        )

        if not result:
            print("  (Table is empty)")
            continue

        for i, row in enumerate(result, 1):
            row_dict = dict(row)
            # Convert non-serializable objects (like datetime) to strings for clean display
            formatted = {
                k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v
                for k, v in row_dict.items()
            }
            print(f"  Row {i}: {json.dumps(formatted, indent=4)}")

    print(f"\n{'='*55}\n")