import pytest
from pathlib import Path
from pyvlcb import VLCB, VLCBFormat, VLCBOpcode
from layout import Layout
from trackview import TrackViewNode
from trackview import track_view_manager

CURRENT_DIR = Path(__file__).parent
DATA_DIR = CURRENT_DIR / "data"
LAYOUT_FILE = "test_layout.json"

@pytest.fixture
def base_layout():
    """Fixture to provide a fresh Layout instance for each test."""
    # Since we removed the class, 'self' no longer exists.
    # If Layout expects a parent object (common in PySide6 GUI architectures), 
    # passing None is usually the correct approach for tests.
    return Layout(None, DATA_DIR, LAYOUT_FILE)

def test_create(base_layout):
    assert track_view_manager is not False

def test_add_track_view_node(base_layout):
    base_layout.add_track_view_node("Point", "Test point 1")
    
    this_node = base_layout.get_node_from_name("Test point 1")
    
    assert this_node.device_type == "TrackView"
    assert this_node.node_type == "Point"
    assert this_node.name == "Test point 1"