import unittest

import os

from pyvlcb import VLCB, VLCBFormat, VLCBOpcode
from trackview import TrackViewNode
from trackview import track_view_manager
                
## Tests for DeviceModel
# The DeviceModel is created as a singleton known as track_view_manager
class TestDeviceManager(unittest.TestCase):
    def test_create(self):
        #print ("Testing device model")
        self.assertTrue(track_view_manager != False)


        
    def test_add_gui_node (self):
        # Node needs to be added through Layout
        gui_objects = []
        gui_objects.append(TrackViewNode(None, "Point", "Test point 1", 0, {}))
        track_view_manager.add_gui_node(gui_objects[-1])
        # Retrieve the gui_node
        this_node = track_view_manager.get_gui_node(0)
        self.assertTrue(this_node.device_type == "Gui")
        self.assertTrue(this_node.object_type == "Point")
        self.assertTrue(this_node.name == "Test point 1")
        # Also test using get_type_node
        this_node_type = track_view_manager.get_type_node ("Test point 1")
        #print (f"Node type is {this_node_type}")
        self.assertTrue(this_node_type == this_node.device_type)
        

                
                
if __name__ == '__main__':
    unittest.main()