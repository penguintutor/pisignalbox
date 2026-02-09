# Dialog for selecting existing / creating new layout
import os
import re
from pathlib import Path
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
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

        # Get the header object
        header = self.ui.locoTable.horizontalHeader()
        # Set Column 0 (Name) to fill all available empty space
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        # Set Column 1 (Button) to shrink exactly to the size of the button
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        
        # handle button clicks
        self.ui.buttonBox.accepted.connect (self.accept_click)
        self.ui.buttonBox.rejected.connect (self.cancel)

        self.update_dialog ()

    def update_dialog(self):
        locos = device_model.get_all_locos()
        # Reset table and remove buttons 
        self.ui.locoTable.setRowCount(0)
        self.loco_table_list = []
        self.loco_table_buttons = []
        for loco in locos:
            self.add_loco_to_table (loco)

    def add_loco_to_table(self, loco):
        """
        Adds a new row to the table with the loco name and an Acquire button.
        """
        # Get the current number of rows to find the index for the new row
        row = self.ui.locoTable.rowCount()
        self.ui.locoTable.insertRow(row)

        self.loco_table_list.append(loco)

        # Add the Locomotive Name (Column 0)
        # We use QTableWidgetItem for standard strings
        name_item = QTableWidgetItem(loco.get_display_name())
        self.ui.locoTable.setItem(row, 0, name_item)

        # Create the Acquire Button (Column 1)
        self.loco_table_buttons.append(QPushButton("Acquire"))
        
        # Connect the signal (The tricky part!)
        # We use a lambda to pass the specific 'loco' object to the handler.
        # Note: 'l=loco' captures the current value of loco. 
        # If you skip this, all buttons will try to acquire the last loco added.
        self.loco_table_buttons[row].clicked.connect(lambda checked=False, l=loco: self.acquire_pressed(l))

        # Insert the widget into the table
        # setCellWidget is required for buttons (setItem is only for text/icons)
        self.ui.locoTable.setCellWidget(row, 1, self.loco_table_buttons[row])

    def acquire_pressed(self, loco):
        """
        Slot to handle the button click
        """
        print(f"Acquiring locomotive: {loco.get_display_name()}")
        # Aquire loco
        self.gui.api.start_request(self.gui.api.vlcb.allocate_loco(loco.loco_id))
        loco.set_status('rloc', "controller")

    
    def accept_click (self):

        self.accept()
        
    def cancel(self):
        self.reject()

    def get_dict (self):
        # temp just convert list to dict
        return {item: item for item in self.locos}

    