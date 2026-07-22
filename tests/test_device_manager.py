import os

from pyvlcb import VLCB, VLCBFormat, VLCBOpcode
from loco import Loco
from trackview import TrackViewNode
from device import device_manager
from loco import loco_manager

def test_create():
    assert device_manager is not False

def test_create_locomanager():
    assert loco_manager is not False
    
def test_load_locos():
    basedir = os.path.dirname(__file__)
    test_dir = os.path.join(basedir, "data")
    locos_file = os.path.join(test_dir, "locos.json")
    
    loco_manager.load_locos(test_dir, locos_file)
    
    all_locos = loco_manager.get_all_locos()
    
    assert all_locos[0].loco_name == "5190 Prairie"