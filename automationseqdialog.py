""" Dialog for creating a new AutomationSequence
or 
editing an existing AutomationSequence

"""


import sys
import copy
import re
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QHBoxLayout, QWidget, QMessageBox,
    QListWidget, QFormLayout, QLineEdit, QSpinBox 
)
from PySide6.QtCore import Qt
from automationrule import AutomationRule
from automationsequence import AutomationStep, AutomationSequence
from automationstepdialog import AutomationStepDialog

class AutomationSeqDialog(QDialog):
    def __init__(self, parent, sequence=None):
        super().__init__(parent)
        self.parent = parent
        self.mainwindow = self.parent.mainwindow
        self.setWindowTitle("Automation Sequence")
        self.resize(400, 450)
        self.sequence = sequence # For editing, if passed
        self.seq_data = {}
        self.steps = [] # Stores list of AutomationSteps (as dicts) - When turned into sequence these become objects
        self.labels = [] # List of labels in the sequence - used to pass to step dialog
        
        self._setup_ui()
        if sequence != None:
            self.load_sequence(sequence)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Title and Loco Count
        title_layout = QFormLayout()
        self.title_input = QLineEdit()
        title_layout.addRow("Sequence Title:", self.title_input)
        main_layout.addLayout(title_layout)

        main_layout.addWidget(QLabel("Automation Steps"))
        
        # Step List (for displaying the steps)
        self.steps_list = QListWidget()
        main_layout.addWidget(self.steps_list)

        # Move sequence button
        step_move_layout = QHBoxLayout()
        self.move_up_button = QPushButton("Move Up")
        self.move_down_button = QPushButton("Move Down")
        step_move_layout.addWidget(self.move_up_button)
        step_move_layout.addWidget(self.move_down_button)
        main_layout.addLayout(step_move_layout)

        # Controls for Steps
        step_control_layout = QHBoxLayout()
        self.add_step_button = QPushButton("Add Step")
        self.edit_step_button = QPushButton("Edit Step")
        self.remove_step_button = QPushButton("Remove Step")
        step_control_layout.addWidget(self.add_step_button)
        step_control_layout.addWidget(self.edit_step_button)
        step_control_layout.addWidget(self.remove_step_button)
        main_layout.addLayout(step_control_layout)
        
        # Buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("Save Sequence")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.save_sequence)
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        main_layout.addLayout(button_box)
        
        # Connections
        self.move_up_button.clicked.connect(self.move_up_step)
        self.move_down_button.clicked.connect(self.move_down_step)
        self.add_step_button.clicked.connect(self.add_edit_step)
        self.edit_step_button.clicked.connect(lambda: self.add_edit_step(edit=True))
        self.remove_step_button.clicked.connect(self.remove_step)
        # Connect the double-click signal
        # We use 'item' to catch the QListWidgetItem argument sent by the signal, 
        # but we ignore it and just call your existing method.
        self.steps_list.itemDoubleClicked.connect(lambda item: self.add_edit_step(edit=True))

    
    def move_up_step(self):
        """ Moves the selected entry up one

        """
        # Get the currently selected row
        current_row = self.steps_list.currentRow()

        # Check if an item is selected AND it's not already at the top (index 0)
        if current_row <= 0:
            return

        target_row = current_row - 1

        # PAUSE UI UPDATES: Tell the widget to stop redrawing temporarily
        self.steps_list.setUpdatesEnabled(False)

        # Update the underlying Python list (self.steps)
        # .pop() removes and returns the item, which we then insert at the new index
        step_data = self.steps.pop(current_row)
        self.steps.insert(target_row, step_data)

        #  Update the QListWidget (self.steps_list)
        # takeItem removes the QListWidgetItem from the widget so we can place it elsewhere
        item = self.steps_list.takeItem(current_row)
        self.steps_list.insertItem(target_row, item)

        # Keep the moved item selected so the user can keep clicking "Up"
        
        self.steps_list.clearSelection()          # Clear any lingering background selection
        item.setSelected(True)                    # Explicitly flag the item as selected
        self.steps_list.setCurrentItem(item)      # Set it as the active item

        # Refresh the numbered labels while the UI is still paused
        self.update_step_numbers()

        # RESUME UI UPDATES: Tell the widget it is allowed to draw again
        self.steps_list.setUpdatesEnabled(True)

        self.steps_list.setFocus()                # Return focus to the list so the highlight is active

    def move_down_step(self):
        """ Moves the selected entry down one

        """
        # Get the currently selected row
        current_row = self.steps_list.currentRow()

        # Check if an item is selected AND it's not already at the bottom
        # len(self.steps) - 1 gives us the index of the very last item in the list
        if current_row < 0 or current_row >= len(self.steps) - 1:
            return

        target_row = current_row + 1

        # PAUSE UI UPDATES: Tell the widget to stop redrawing temporarily
        self.steps_list.setUpdatesEnabled(False)

        # Update the underlying Python list (self.steps)
        step_data = self.steps.pop(current_row)
        self.steps.insert(target_row, step_data)

        # Update the QListWidget (self.steps_list)
        item = self.steps_list.takeItem(current_row)
        self.steps_list.insertItem(target_row, item)

        # Keep the moved item selected so the user can keep clicking "Down"
        self.steps_list.clearSelection()          # Clear any lingering background selection
        item.setSelected(True)                    # Explicitly flag the item as selected
        self.steps_list.setCurrentItem(item)      # Set it as the active item

        # Refresh the numbered labels while the UI is still paused
        self.update_step_numbers()

        # RESUME UI UPDATES: Tell the widget it is allowed to draw again
        self.steps_list.setUpdatesEnabled(True)

        self.steps_list.setFocus()                # Return focus to the list so the highlight is active

    def update_step_numbers(self):
        """Updates the visual text of all items to match their current index."""
        for i in range(self.steps_list.count()):
            # Get the visual item from the UI
            item = self.steps_list.item(i)
            
            # Get the corresponding data from your internal list
            step_data = self.steps[i]
            
            # Reapply the text format with the new position (i + 1)
            item.setText(f"Step {i+1} ({step_data['name']})")

    # Refreshes the list widget with the current steps
    # Also update the labels list
    def _update_steps_list(self):
        #print ("Loading steps into list")
        self.steps_list.clear()
        self.labels = []
        for i, step in enumerate(self.steps):
            if step.get("type") == "Label":
                self.labels.append(step.get("data", {}).get("labelid", ""))
            self.steps_list.addItem(f"Step {i+1} ({step['name']})")
        
    # Load the details from the sequence
    def load_sequence(self, sequence):
        info = sequence.get_info()
        self.steps = []
        # title, numlocos
        self.title_input.setText(info["title"])
        
        # copy steps by converting back to dict as though created
        # this protects the current (if cancel is pressed)
        # and ensures a edit is similar to a new
        for step in sequence.get_steps():
            self.steps.append(step.to_dict())
        
        self._update_steps_list()


    # Opens a sub-dialog to create or edit an AutomationStep.
    def add_edit_step(self, edit=False):
        current_step = None
        current_index = -1
        if edit:
            current_index = self.steps_list.currentRow()
            if current_index < 0:
                QMessageBox.warning(self, "Error", "Please select a step to edit.")
                return
            current_step = self.steps[current_index]

        num_locos = self._calc_locos()

        # Use a sub-dialog (StepCreationDialog) for rule building
        dialog = AutomationStepDialog(self, num_locos, self.labels, current_step)
        if dialog.exec() == QDialog.Accepted:
            new_step = dialog.get_step()
            #print (f"New/Edited step: {new_step}")
            if edit:
                self.steps[current_index] = new_step
            else:
                self.steps.append(new_step)
            self._update_steps_list()

    def remove_step(self):
        selected_row = self.steps_list.currentRow()
        if selected_row >= 0:
            del self.steps[selected_row]
            self._update_steps_list()
        else:
            QMessageBox.warning(self, "Error", "Please select a step to remove.")

    def save_sequence(self):
        """Finalizes the sequence creation and accepts the dialog."""
        title = self.title_input.text().strip()
        #num_locos = self.num_locos_spinbox.value()

        if not title:
            QMessageBox.warning(self, "Error", "Please enter a sequence title.")
            return

        if not self.steps:
            QMessageBox.warning(self, "Error", "The sequence must contain at least one step.")
            return
        
        num_locos = self._calc_locos()

        self.seq_data = {"title": title, "steps": self.steps, "settings": {'num_locos': num_locos}}
        super().accept()

    # Returns a dict with seq_data
    def get_sequence(self):
        return self.seq_data
    
    def _calc_locos(self):
        num_locos = 0
        for step in self.steps:
            if step.get("type") == "Loco":
                loco_id_str = step.get("data", {}).get("locoid", "")
                
                # Regex looks for "ID " followed by one or more digits (\d+)
                match = re.match(r"ID (\d+)", str(loco_id_str))
                
                if match:
                    loco_id = int(match.group(1))
                else:
                    continue

                if loco_id > num_locos:
                    num_locos = loco_id 
        return num_locos
        