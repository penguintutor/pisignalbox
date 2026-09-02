# logging_config.py
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from flask import request
from flask_login import current_user

def log_http_request(response):
    """The HTTP logging callback"""
    if request.path.startswith('/static/'):
        return response
        
    user_identity = current_user.username if current_user.is_authenticated else "Anonymous"
    log_message = f"{request.remote_addr} - {user_identity} - {request.method} {request.path} - {response.status_code}"
    
    if response.status_code >= 400:
        logging.warning(log_message)
    else:
        logging.info(log_message)
        
    return response

def setup_logging(app):
    # Default to local 'logs' folder, but allow override via environment variable
    log_path = app.config['LOG_PATH']
    console_level = app.config['LOGLEVEL_CONSOLE']
    file_level = app.config['LOGLEVEL_FILE']
       
        
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    root_logger.setLevel(file_level)
    
    if not root_logger.handlers:
        # Console output (catches local terminal, Docker, and systemd)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        # Set the log level for console here
        console_handler.setLevel(console_level)
        root_logger.addHandler(console_handler)

        # File output (Only activate if we aren't in a container/systemd setup that disables it)
        if os.environ.get('DISABLE_FILE_LOGGING') != 'true':
            file_handler = RotatingFileHandler(
                log_path, maxBytes=10485760, backupCount=5
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    app.after_request(log_http_request)