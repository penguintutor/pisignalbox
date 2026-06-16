# UI Loco Package - as UIAutomateMixin
# Included into MainWindow

# Automate module for handling automation operations for mainwindow
# This includes the UI wrapper class for the automation view
import os
import sys
import time
from PySide6.QtCore import QTimer, QSize
from PySide6.QtWidgets import QMenu, QDialog, QFileDialog, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QPalette, QColor, QFont, QResizeEvent
from core import device_model, event_bus
from autolocodialog import AutoLocoDialog

class UIAutomateMixin:

    def update_automation_list (self):
        # Update the automation list in the UI
        self.ui.automationList.clear()
        for seq_string in self.automation.get_sequence_strings():
            self.ui.automationList.addItem(seq_string)


    def run_selected_sequence(self):
        """Triggers the run process in the main window."""

        selected_row = self.ui.automationList.currentRow()
        if selected_row >= 0:
            # First need to check for any unassigned locos (eg. "ID 1") and 
            # assign to a real loco
            loco_list = self.automation.get_locos(selected_row)

            # If loco_list has any non DCC entries
            # Use dialog to get loco ids
            if any(item.startswith("ID ") for item in loco_list):
                auto_loco_dialog = AutoLocoDialog(self, loco_list)
                result = auto_loco_dialog.exec()
                if result == 0:
                    return
                loco_dict = auto_loco_dialog.get_results()
            else:
                loco_dict = {item: item for item in loco_list}


            #print (f"Starting sequence with locos {loco_dict}")
            self.automation.run_sequence(selected_row, loco_dict)
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a rule sequence to run.")