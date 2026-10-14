import json5
# Uses json when updating files that don't need comment - includes "" around keys
import json
from flask import current_app
import logging
from vlcbserver.config import Config
from vlcbserver.vlcb_bridge import send_data
from vlcbserver.railway.loco.loco import Loco

logger = logging.getLogger(__name__)


####################################################
# Shares data between mainThread (USB handlder)
# and flaskThread (web app)
# mainThread can read/write, flaskThread = read-only
####################################################




class LocoManager ():
    def __init__ (self):
        # objects are internal. They must not be accessed directly by flask
        # Uses dict (in gui a list was used)
        # dict ensures don't end up with duplicates and makes finding easier
        # when dealing with simultaneous updates
        self._locos = {}
        # Uses as snapshot (shallow copy) of the dict so as to avoid problems
        # when updated - this still points to the same underlying data as self._locos
        # this should be used whenever iterating over the locos
        self._snapshot = {}



    ####################################################
    # Mainthread only - updates data
    ####################################################


    def load_locos(self, data_dirs):
        """ Designed to run during application start to load all locos"""
        for dir in data_dirs:
            # See if there is a locos file and if so load it 
            locos_file =  dir / "locos.json"
            if locos_file.is_file():
                # read in main locos json file
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
                # join "locos" to the data dir loaded
                loco_dir = dir / "locos"
                for loco_filename in loco_json:
                    #print (f"Loading file {loco_filename}")
                    # Load the files here
                    try:
                        full_path = loco_dir / loco_filename
                        # Loco key is the filename (no path) with .json stripped
                        loco_ref = loco_filename.removesuffix('.json')
                        self.add_loco(loco_ref, Loco.from_file(loco_ref, full_path))
                    except Exception as e:
                        logger.warning (f"Error loading {full_path} - {e}")
                        continue

                    


    def add_loco (self, loco_key, loco_obj):
        if loco_key in self._locos:
            # Add info that overwriting
            logger.info(f"Duplicate loco found - using local copy {loco_key}")
        # Add / replace existing
        self._locos[loco_key] = loco_obj

        # This is included on any method that updates the dict (add / remove)
        # Not required when updating the existing 
        self._snapshot = self._locos.copy()

    def remove_loco(self, loco_key):
        """Called by mainthread to remove a loco."""
        if loco_key in self._locos:
            del self._locos[loco_key]
            self._snapshot = self._locos.copy()



    ####################################################
    # Public - read / thread safe updates vi mesg queue
    ####################################################

    def get_locos_list (self):
        """ Return a list of loco objects"""
        return list(self._snapshot.values())

    def get_all_loco_objects_dict(self):
        # .copy() gives the  a safe dict 
        # can loop over without accidentally modifying your snapshot.
        return self._snapshot.copy()

    def get_list_loco_names(self):
        """Returns a list like: [{'id': 'mallard_a4', 'name': 'Mallard'}, ...]
        useful for creating pull down menu i, web page
        """
        return [
            {"loco_ref": loco_key, "name": loco_obj.loco_name}
            for loco_key, loco_obj in self._snapshot.items()
        ]


    def get_loco_details_dict (self, loco_id):
        """ get details for specified loco - returns in dict format
        used by loco_details """
        if loco_id in self._locos:
            return self._locos[loco_id].get_details_dict()

        else:
            return {
                "name": "N/A", 
                "image_url": "/loco/image/notfound", 
                "title": "Invalid loco selected",
                "description": "N/A"
            }



# Module level singleton
loco_manager = LocoManager()