# Class to hold details about the layout / locos etc
# Reads data from layout.json file
# Todo in future add multiple layout files
import json
import os
from trackview import TrackViewNode
from core import device_model
import core.paths as app_paths
from core import event_bus
from events import GuiEvent
from trackview import track_view_manager


# Holds specific information about the layout
# can also be useful for giving friendly names to replace nodeIDs
# layout_file - filename must be provided, but if not exist it will be created without warning

# active is optional (default True)
# if set to false allows Layout to be loaded without replacing current Layout

class Layout():
    def __init__ (self, mainwindow, layout_dir, layout_file, active=True):
        #print (f"Creating Layout dir {layout_dir} file {layout_file}")
        self.active = active
        self.mainwindow = mainwindow
        self.layout_file = layout_file
        self.layout_dir = layout_dir

        # pass self to track_view_manager so that don't need
        # to double register track_view_nodes
        
        # general settings are stored in self.layout_data
        # Objects on the GUI are saved under trackviewnodes
        self.track_view_nodes = []
        # Load the layout from the file
        self.load_file()

        # If this is our active layout
        # Pass self on to TrackViewManager so it can access the
        # nodes from Layout
        if self.active:
            track_view_manager.register_layout(self)

        
    def set_title (self, title):
        # title is required / created when loading file  so no need to check it exists
        self.layout_data['title'] = title
        # perform save whenever title is updates
        self.save_file()
        
    # Title is mandatory, but still have a getter that just returns it for consistancy with set
    def get_title (self):
        return self.layout_data['title']


    # Call without filename to load current layout
    # Add filename to replace the current layout_file
    # Note does not check for existing file - but that would mean a corrupt layouts file
    def load_file (self, layout_filename=None):
        #print (f"Loading file {layout_filename}")
        if layout_filename != None and layout_filename != "":
            self.layout_file = layout_filename
        if self.layout_file != None:
            filename = os.path.join(self.layout_dir, self.layout_file)
            try:
                with open(filename, 'r') as data_file:
                    self.layout_data = json.load(data_file)
            except:
                #print (f"No layout file '{filename}' using default values")
                self.layout_data = {}
        else:
            self.layout_data = {}
        # If no title (eg. new filename - then set)
        # If it's being created through dialog then that should change to new title
        # It it's first run then this title will be created for the default
        if 'title' not in self.layout_data:
            self.layout_data['title'] = "Default Layout"
            
        # Load the trackviewnodes from self.layout_data['trackviewnodes']
        # First reset trackviewnodes so we don't add to the end of existing
        self.track_view_nodes = []
        # If no objects in the layout_data then nothing else to do
        if 'trackviewnodes' not in self.layout_data and "guiobjects" not in self.layout_data:
            print (f"No trackviewnodes {self.layout_data}")
            return
        
        # New format uses track_nodes, old uses gui_objects
        # Can load both, and merge
        track_nodes = self.layout_data.get('trackviewnodes', [])
        gui_objects = self.layout_data.get('guiobjects', [])

        for entry in track_nodes + gui_objects:
            #print (f"Track view node object {entry}")
            if 'object' in entry.keys():
                if entry['object'] == 'gui':
                    #self.layout.trackviewnodes.append(TrackViewNode(self, entry['type'], entry['name'], {}))
                    self.add_track_view_node(entry['type'], entry['name'])
                elif entry['object'] == 'button':
                    track_view_node_name = entry.get('trackviewnode', entry.get("guiobject"))
                    track_view_node_id = self.gui_name_toid(track_view_node_name)
                    self.track_view_nodes[track_view_node_id].add_button(entry['button_type'], entry['settings'], entry['pos'])
                elif entry['object'] == 'label':
                    track_view_node_name = entry.get('trackviewnode', entry.get("guiobject"))
                    track_view_node_id = self.gui_name_toid(track_view_node_name)
                    self.track_view_nodes[track_view_node_id].add_label(entry['label_type'], entry['settings'], entry['pos'])
            
                
    def add_track_view_node (self, device_type, device_name):
        self.track_view_nodes.append(TrackViewNode(self, device_type, device_name, {}))
        # Add to node tree
        #print (f"Adding to node tree {self.layout.trackviewnodes[-1].name}")
        #track_view_manager.add_gui_node(self.track_view_nodes[-1])
        # Note that if this is added before systemmanager then 
        # the signal does not go anywhere - instead loaded by 
        # Initial object scan. This is here is subsequent updates are
        # made to the GUI that need to be updated in the tree etc.
        event_bus.layout_updated_signal.emit (GuiEvent({
            "action": "new_node",
            "node_object": self.track_view_nodes[-1]
        }))
        
    # Labels and buttons are added to trackviewnodes 
    # Here pos is optional so it's moved to the end
    def add_label (self, gui_node_name, label_type, settings, pos=(5,5)):
        gui_node_id = self.gui_name_toid(gui_node_name)
        # check gui node is valid (no reason it shouldn't be)
        if gui_node_id < 0:
            print (f"Invalid gui name {gui_node_name}")
        self.track_view_nodes[gui_node_id].add_label (label_type, settings, pos)
        
    def add_button (self, gui_node_name, button_type, settings, pos=(5,5)):
        gui_node_id = self.gui_name_toid(gui_node_name)
        # check gui node is valid (no reason it shouldn't be)
        if gui_node_id < 0:
            print (f"Invalid gui name {gui_node_name}")
        self.track_view_nodes[gui_node_id].add_button (button_type, settings, pos)
        
    # From name get pos in list
    # used when adding buttons / labels etc.
    def gui_name_toid (self, gui_name):
        for i in range (0, len(self.track_view_nodes)):
            if self.track_view_nodes[i].name == gui_name:
                return i
        # Shouldn't return -1 as gui wouldn't show name that doesn't exist
        return -1
        
        
#         self.node_names = {
#             300: "Solenoid1",
#             301: "Servo1",
#             65535: "CANCAB",		# 0xffff
#             65534: "CANCMD"			# 0xfffe
#             }
#         # 2 dimension node, evid, name
#         self.ev_names = {
#             0: {22: "Solenoid1"},
#             300: {1: "Solenoid01", 2: "Solenoid02"},
#             301: {1: "Servo1"}
#             }

    # For the setters then unless part of a multi-item update then save immediately
    def set_layout_image (self, filename):
        self.layout_data['layoutimage'] = filename
        self.save_file()
        
        
    def get_layout_image (self):
        # check we have an image - if not return default
        # Only checks for a defined entry - can return invalid name if corrupt .json file or file deleted
        if 'layoutimage' in self.layout_data:
            return os.path.join(self.layout_dir, self.layout_data['layoutimage'])
        else:
            return os.path.join(app_paths.RESOURCES_DIR, "nolayout.png")
        
    def get_layout_objs_file (self):
        # Returns filename - file may not exist if this is new
        return self.layout_objs_file
    
    def save_file (self):
        filename = os.path.join(self.layout_dir, self.layout_file)
        
        # Add all gui objects into self.layout_data['trackviewnodes']
        
        # clear out any existing objects
        self.layout_data['trackviewnodes'] = []
        
        for object in self.track_view_nodes:
            self.layout_data['trackviewnodes'].extend(object.get_save_objects())
        
        
        try:
            with open(filename, 'w') as data_file:
                json.dump(self.layout_data, data_file, indent=4)
        except Exception as e:
            print (f"Error saving layout file {filename} {e}")
            
    def gui_object_names (self):
        return_list = []
        for object in self.track_view_nodes:
            return_list.append(object.name)
        return return_list
                   
    # Translation from node_id to friendly name
    # Ideally this should be done within the module, but could be supported here
    # Temporarily disabled
    def node_name (self, node_id):
        return f"Node: {node_id}"
#         #print (f"Node id {node_id}")
#         if (node_id in self.node_names.keys()):
#             #print (f" name {self.node_names[node_id]}")
#             return self.node_names[node_id]
#         else:
#             #print (f" name (from node) Node: {node_id}")
#             return f"Node: {node_id}"
        
    # As with node name - is this needed - need to implement differently
    # EV name normally use en, if not in lookup 
    def ev_name (self, node_id, ev_id, en=None):
        #if (node_id in self.ev_names.keys() and ev_id in self.ev_names[node_id].keys()):
        #    return self.ev_names[node_id][ev_id]
        if en != None:
            return f"{en:#08x}"
        else:
            return f"EV {ev_id}"