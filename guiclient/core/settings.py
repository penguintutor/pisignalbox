# Holds, loads and saves settings
# Owned by MainWindow
import os, sys
import json
from core import DATA_DIR
from pathlib import Path 

class Settings:
    def __init__ (self, parent, defaults_file, setting_file):
        self.parent = parent
        self.data_dir = DATA_DIR
        self.defaults_filename = defaults_file
        self.setting_filename = setting_file
        self.settings_dict = {}

        # Load defaults, then override with more specific values
        self.load_settings(self.defaults_filename)
        self.load_settings(self.setting_filename)
    
    # Load settings (normally called by constructor)
    # filename required
    def load_settings (self, filename):
        if filename == None:
            return
        full_path = self.data_dir / filename
        try:
            with open(full_path, 'r') as data_file:
                # Store as new dict before merging with existing
                new_settings = json.load(data_file)
                self._merge_settings(new_settings)
        except FileNotFoundError:
            print(f"Warning: The file '{filename}' was not found.")
            
        except json.JSONDecodeError as e:
            print(f"Warning: The file '{filename}' is corrupt (Details: {e})")
            
        except PermissionError:
            print(f"Warning: Permission denied when trying to read '{filename}'.")
        
    # Returns True if successful save
    # Defaults to the standard settings file
    def save_settings (self, filename=None):
        self.update_settings ()		# Read in any settings that may have changed
        if filename == None:
            filename = self.setting_filename
        full_path = self.data_dir / filename
        try:
            with open(full_path, 'w') as data_file:
                json.dump(self.settings_dict, data_file, indent=4)
        except OSError:
            print (f"Failed to save settings {full_path}")
            return False
        
    # Update settings before a save
    def update_settings (self):
        # Get enabled_locos
        self.settings_dict['enabledlocos'] = self.parent.get_enabled_locos()
       
    # Many of the settings are available through getters which can handle no data
    # Get the layout filename
    # If new then return default.json
    # May also break if directory changed and no longer matches - so check later
    def get_layout_filename (self):
        if 'layoutfile' in self.settings_dict:
            return self.settings_dict['layoutfile']
        else:
            return "default.json"
    
    # Sets the layout filename and saves the update
    def set_layout_filename (self, filename):
        self.settings_dict['layoutfile'] = filename
        self.save_settings()

    def get_setting(self, setting_str, sub_setting_str=None):
        """Gets a setting from the dict
        if the setting is a dict (eg. statuscolors) and
        sub_setting_str is provided then return the 
        value of the sub_setting_str instead.
        If the setting doesn't exist then return None"""
        setting_value = self.settings_dict.get(setting_str, None)
        if isinstance (setting_value, dict) and sub_setting_str != None:
            return setting_value.get(sub_setting_str, None)
        return setting_value

    def get_url(self):
        """Get's the entire URL this combines the settings
        server.protocol, server.hostname, server.port into a 
        single url formatted string"""
        protocol = self.get_setting("server", "protocol")
        hostname = self.get_setting("server", "hostname")
        port = self.get_setting("server", "port")
        return (f"{protocol}://{hostname}:{port}/")

    def _merge_settings(self, new_settings):
            """ Used by load settings to merge the new entries
            into the existing settings dict. Allows dict to be 
            2 levels deep and merge sub items"""

            for key, value in new_settings.items():
                # Check if the key exists AND the existing value is a dictionary
                if key in self.settings_dict and isinstance(self.settings_dict[key], dict):
                    
                    # If the incoming value is NOT a dictionary, raise an error
                    if not isinstance(value, dict):
                        raise ValueError(
                            f"Type mismatch for setting '{key}': expected a dictionary, "
                            f"but got {type(value).__name__}."
                        )
                    
                    # Both are dictionaries, so merge them
                    self.settings_dict[key].update(value)
                else:
                    # Otherwise, it's a new key or replacing a standard value
                    self.settings_dict[key] = value
                