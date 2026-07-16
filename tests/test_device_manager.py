import unittest

import os

from pyvlcb import VLCB, VLCBFormat, VLCBOpcode
from loco import Loco
from trackview import TrackViewNode
from device import device_manager
from loco import loco_manager
                
## Tests for DeviceModel
# The DeviceModel is created as a singleton known as device_manager
class TestDeviceManager(unittest.TestCase):
    def test_create(self):
        #print ("Testing device model")
        self.assertTrue(device_manager != False)

    def test_create_locomanager(self):
        self.assertTrue(loco_manager != False)
        
    def test_load_locos (self):
        #print ("Test load locos")
        basedir = os.path.dirname(__file__)
        test_dir = os.path.join(basedir, "data")
        locos_file = os.path.join(test_dir, "locos.json")
        #print (f"Loading locos file {test_dir} : {locos_file}")
        loco_manager.load_locos (test_dir, locos_file)
        #print ("Getting all locos")
        all_locos = loco_manager.get_all_locos()
        #print (f"Locos {all_locos}")
        #print (f"Loco 0 {all_locos[0].loco_name}")
        self.assertTrue(all_locos[0].loco_name == "5190 Prairie")
        

                
                
if __name__ == '__main__':
    unittest.main()