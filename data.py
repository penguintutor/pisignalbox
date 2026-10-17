import json5
# Uses json when updating files that don't need comment - includes "" around keys
from flask import current_app
import json
import logging
from vlcbserver.config import Config

logger = logging.getLogger(__name__)


def get_dirs():
    """ Returns a list of dirs to load from loads in the order that is listed"""
    """ Provides the full path"""
    data_dirs = []
    config = current_app.config
    # Is gui path enabled - if so then load that first
    if config.get("use_gui_settings"):
        # check the path is valid
        full_path = config.get('BASE_DIR') / current_app.config.get("gui_settings_path", "")
        if full_path.is_dir():
            data_dirs.append(full_path)
        else:
            logger.warning (f"Local GUI path is not valid {full_path}")
            
    # If local enabled then use the normal directory
    # However if there is no other directory then use that anyway so as not
    # to try with no directories
    if config.get("use_server_settings") or not data_dirs:
        full_path = config.get("CONFIG_DIR") / "data"
        if full_path.is_dir():
            data_dirs.append(full_path)
        else:
            logger.warning (f"Server data dir path is not valid {full_path}")

    return data_dirs


def get_locos():
    data_dirs = get_dirs()
    for dir in data_dirs:
        # See if there is a locos file and if so load it 
        locos_file =  dir / "locos.json"
        if locos_file.is_file():
            # read in file
            try:
                with open(locos_file, 'r') as f:
                    loco_json = json5.load(f)
            except FileNotFoundError:
                # Not found may not be an error - so use information
                logger.info(f"File {loco_json} not found.")
                continue
            except json.JSONDecodeError:
                logger.warning(f"File {loco_json} is not valid json.")
                continue
            except Exception as e:
                logger.warning(f"Error reading file {loco_json} - {e}")
                continue
            # Iterate over each file and load them as a loco object
            for ind_file in loco_json