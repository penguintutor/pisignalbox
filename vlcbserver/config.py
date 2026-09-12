## config.py
## These are constants, but the base dir can be overridden through
# command line or environment variables if required

import os
import logging
from pathlib import Path

class Config:
    def __init__(self, base_dir: Path | str | None = None):
        if base_dir:
            self.BASE_DIR = Path(base_dir).resolve()
        elif "VLCBSERVER_BASE_DIR" in os.environ:
            self.BASE_DIR = Path(os.environ["VLCBSERVER_BASE_DIR"]).resolve()
        else:
            self.BASE_DIR = Path(__file__).resolve().parent.parent

        # Settings directory (all except config.py)
        self.CONFIG_DIR = self.BASE_DIR / "vlcbserver" / "settings"
        self.DEFAULT_SETTINGS = self.CONFIG_DIR / "defaults.json"
        self.CUSTOM_SETTINGS = self.CONFIG_DIR / "server.json"

        # Database is in the instances directory - holds user details etc.
        self.INSTANCE_DIR = self.BASE_DIR / 'instances'
        self.DATABASE_PATH = self.INSTANCE_DIR / 'users.db'

        # String for setup command - used to inform user how to add user
        self.SETUP_CMD = "setup/setup_auth.py"

        # Future: Consider overriding using config file or environment variables
        self.LOGLEVEL_CONSOLE = logging.WARNING
        self.LOGLEVEL_FILE = logging.INFO

        self.LOG_DIR = self.BASE_DIR / 'logs'
        self.LOG_PATH = self.LOG_DIR / 'vlcbserver.log'

        # Allow some environment variables to override 
        # LOG_PATH can be overridden by environment setting 
        env_log_dir = os.environ.get('APP_LOG_DIR', None)
        if env_log_dir:
            self.LOG_PATH = Path(env_log_dir) / 'vlcbserver.log'