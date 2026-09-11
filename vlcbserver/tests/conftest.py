# tests/conftest.py
import pytest
import logging
from pathlib import Path
from vlcbserver.config import Config
from vlcbserver import create_app

BASE_DIR = Path(__file__).resolve().parent


@pytest.fixture
def app():

    cfg = Config(base_dir=BASE_DIR)

    # Create the app using your factory
    config = {}
    config.update({
            # Flask-SQLAlchemy expects a URI string. Uses an f-string to inject the Path.
            'SQLALCHEMY_DATABASE_URI': f"sqlite:///{cfg.DATABASE_PATH}",
            # Disabling this saves memory and suppresses a warning
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            # Log details
            'LOG_PATH' : cfg.LOG_PATH,
            'LOGLEVEL_CONSOLE': cfg.LOGLEVEL_CONSOLE,
            'LOGLEVEL_FILE': cfg.LOGLEVEL_FILE
            })
    app = create_app(config)
    app.config.update({
        "TESTING": True,
    })
    #yield app
    return app