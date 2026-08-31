# Holds, loads and saves settings
# Owned by MainWindow
import os, sys
import json
from core import DATA_DIR
from pathlib import Path 

class Settings:
    def __init__ (self, parent, setting_file):
        self.parent = parent
        self.data_dir = DATA_DIR
        self.setting_filename = setting_file
        self.settings_dict = {}
        
        self.load_settings()
    
    # Load settings (normally called by constructor)
    # filename can be specified to load alternative file
    def load_settings (self, filename=None):
        if filename == None:
            filename = self.setting_filename
        full_path = self.data_dir / filename
        try:
            with open(full_path, 'r') as data_file:
                self.settings_dict = json.load(data_file)
        except OSError:
            print (f"No settings file '{filename}' using default values")
        
    # Returns True is successful save
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