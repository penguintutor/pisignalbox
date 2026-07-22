from pyvlcb import VLCB, VLCBFormat, VLCBOpcode
from loco import Loco
from trackview import TrackViewNode
from device import device_manager

def test_opcode_format():
    # Check each of the format entries exist in the field_formats dictionary
    for opcode, opcode_data in VLCBOpcode.opcodes.items():
        
        if opcode_data['format'] == "":
            continue
            
        field_codes = opcode_data['format'].split(',')
        for this_code in field_codes:
            # 'in dict' checks the keys automatically
            assert this_code in VLCBOpcode.field_formats