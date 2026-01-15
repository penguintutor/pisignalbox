# Automate module for handling automation operations for mainwindow
# This includes the UI wrapper class for the automation view
import os
import sys
import time
from PySide6.QtCore import QTimer, QSize
from PySide6.QtWidgets import QMenu, QDialog, QFileDialog, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QPalette, QColor, QFont, QResizeEvent
from devicemodel import device_model
from eventbus import event_bus

def update_automation_list (self):
    # Update the automation list in the UI
    self.ui.automationList.clear()
    for seq_string in self.automation.get_sequence_strings():
        self.ui.automationList.addItem(seq_string)
