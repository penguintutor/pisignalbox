# Dialog for selecting existing / creating new layout
import os
import re
from pathlib import Path
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFileDialog, QMessageBox
from PySide6.QtUiTools import QUiLoader
from devicemodel import device_model
from settings import Settings
from layout import Layout
from layouts import Layouts


class AutoLocoDialog(QDialog):
    
    def __init__(self, parent, locos):
        super().__init__(parent)
        self.gui = parent
        self.locos = locos
        
        self.resize(300, 220)
        
        self.setModal(True)
        loader = QUiLoader()
        basedir = os.path.dirname(__file__)
        self.ui = loader.load(os.path.join(basedir, "autolocodialog.ui"), None)
        self.setWindowTitle("Allocate locos")
        self.setLayout(self.ui.layout())
        
        # handle button clicks
        self.ui.buttonBox.accepted.connect (self.accept_click)
        self.ui.buttonBox.rejected.connect (self.cancel)

        self.update_dialog ()

    def update_dialog(self):
        

    
    def accept_click (self):

        self.accept()
        
    def cancel(self):
        self.reject()

    def get_dict (self):
        # temp just convert list to dict
        return {item: item for item in self.locos}

