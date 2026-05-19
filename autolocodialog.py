# Dialog for selecting existing / creating new layout
import os
import re
from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFileDialog, 
    QMessageBox, QTableWidget, QTableWidgetItem, QPushButton, 
    QHeaderView, QVBoxLayout, QGridLayout, QFrame, QLabel, QComboBox,
    QWidget, QDialogButtonBox)
from devicemodel import device_model
from eventbus import event_bus
from locoevent import LocoEvent
from settings import Settings
from layout import Layout
from layouts import Layouts
from loco import Loco


class AutoLocoDialog(QDialog):
    
    def __init__(self, parent, loco_list):
        super().__init__(parent)
        self.gui = parent
        self.loco_list = loco_list
        
        self.setWindowTitle("Allocate Locomotive IDs")
        self.resize(600, 300)

        # Do we "share" or "steal" in event of loco already allocated
        #Todo currently only share coded
        self.acquire_share = "share"

        # Data storage
        self.allocate_ids = [item for item in loco_list if item.startswith("ID ")]
        self.all_locos = device_model.get_all_locos()
        self.assignments = {} # Stores {row_index: selected_loco_object}
        
        # UI Storage to access widgets later
        self.row_widgets = [] 

        self.init_ui()
        

        # If receive PLOC then update loco status
        event_bus.loco_event_signal.connect (self.update_locos)
        # Register for app events - used for LocoEvent allocate error etc.
        event_bus.app_event_signal.connect (self.app_event)

        #self.update_dialog ()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Instruction Label
        instruction = QLabel(f"We found {len(self.allocate_ids)} IDs. Please assign a locomotive to each.")
        instruction.setStyleSheet("color: #555; font-style: italic; margin-bottom: 10px;")
        layout.addWidget(instruction)

        # The Grid (The Table)
        self.grid_layout = QGridLayout()
        self.grid_layout.setColumnStretch(1, 1) # Make the middle column expand
        
        # -- Headers --
        headers = ["ID Required", "Assign Locomotive", "Status / Action"]
        for col, text in enumerate(headers):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: bold; border-bottom: 1px solid #ccc; padding: 5px;")
            self.grid_layout.addWidget(lbl, 0, col)

        # -- Rows --
        for i, id_text in enumerate(self.allocate_ids):
            row_idx = i + 1  # Start at row 1 (0 is header)
            
            # Col 1: ID Label
            id_lbl = QLabel(id_text)
            self.grid_layout.addWidget(id_lbl, row_idx, 0)

            # Col 2: Searchable Combobox
            combo = QComboBox()
            combo.setEditable(True)  # Makes it searchable
            combo.setInsertPolicy(QComboBox.NoInsert) # Prevent user adding new random strings
            combo.setPlaceholderText("Select Loco...")
            
            # Add Locos to combo
            combo.addItem("", None) # Empty default
            for loco in self.all_locos:
                combo.addItem(loco.get_display_name(), loco) # Store the object as user data

            # Connect signal
            # Use a lambda that captures the current row index
            combo.currentIndexChanged.connect(lambda index, r=row_idx: self.on_selection_change(r, index))
            
            self.grid_layout.addWidget(combo, row_idx, 1)

            # Col 3: Status Container (Label + Button)
            # We use a container widget so we can easily swap content
            status_container = QWidget()
            status_layout = QVBoxLayout(status_container)
            status_layout.setContentsMargins(0, 0, 0, 0)
            
            status_lbl = QLabel("--")
            status_lbl.setStyleSheet("color: #888;")
            status_layout.addWidget(status_lbl)
            
            self.grid_layout.addWidget(status_container, row_idx, 2)

            # Store references to widgets so we can update them
            self.row_widgets.append({
                "combo": combo,
                "status_container": status_container,
                "status_lbl": status_lbl # Keep ref to default label
            })

        layout.addLayout(self.grid_layout)
        layout.addStretch() # Push everything up

        # 3. Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Disable OK initially
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        
        layout.addWidget(self.button_box)

    def on_selection_change(self, row_idx, combo_index):
        """Called when a user picks a loco from the dropdown."""
        # Adjust index for 0-based list access (row_idx 1 is list item 0)
        list_idx = row_idx - 1
        widgets = self.row_widgets[list_idx]
        combo = widgets["combo"]
        
        selected_loco = combo.currentData() # Retrieve the Loco object

        # Update assignments
        # Don't care if acquired or not just add if loco is selected
        if selected_loco:
            self.assignments[list_idx] = selected_loco
        else:
            if list_idx in self.assignments:
                del self.assignments[list_idx]

        # Add appropriate widgets to the status field
        # moved to separate method
        self._update_loco_status_field(widgets["status_container"], selected_loco)

        self.validate_form()

    def validate_form(self):
        """Check if every row has a selection."""
        all_assigned = len(self.assignments) == len(self.allocate_ids)
        # also check all locos are acquired
        # if all_assigned then check to see they are all acquired
        if all_assigned:
            for row in self.row_widgets:
                # row is a dict of widgets
                # Get loco object for this row
                selected_loco = row["combo"].currentData()
                #print (f"Selected loco {selected_loco} acquired {selected_loco.is_acquired()}")
                # if any are not acquired then set false
                if not selected_loco.is_acquired():
                    all_assigned = False
                    break
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(all_assigned)

    def clear_layout(self, layout):
        """Helper to remove all widgets from a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def get_results(self):
        """Returns a dict mapping ID string -> Loco Object"""
        results = {}
        for idx, loco in self.assignments.items():
            id_str = self.allocate_ids[idx]
            results[id_str] = loco
        return results
    
    def update_locos(self, event):
        """ Called whenever there is a LocoEvent whilst
        this dialog is open. If relates to allocate loco then 
        update the display"""
        #print (f"Loco event {event}")
        if event.event_type == "PLOC":
            print (f"Loco allocated {event.data.get('Loco_id')}")
            self.update_dialog()

    def app_event(self, app_event):
        # If the dialog is closed (not visible) then don't need to 
        # process any events
        if not self.isVisible():
            return
        if app_event.action == "locotaken":
            # Only action if it is the controlloco that is taken
            loco_id = app_event.get_loco_id()
            if loco_id == None:
                return
            # use try in case we don't have a loco yet
            # iterate over all locos and if any match then attempt acquire again
            for loco in self.assignments.values():
                try:
                    if loco_id == loco.get_id():
                        if self.acquire_share == "share":
                            print (f'Warning - address taken attempting share {loco_id}')
                            #self.steal_dialog_signal.emit(loco_id)
                            self.gui.api.start_request(self.gui.api.vlcb.share_loco(loco.loco_id))
                            # Don't need to check others if we've issued share for this loco already
                            break
                        else:
                            print (f"Only share implemented see self.acquire_share")
                except Exception as e:
                    #print (f"Acquire fail for a non automate loco {loco_id}")
                    return

    # Just update the status at the moment
    # do we need to see if there are new locos (only if add new loco button)?
    def update_dialog(self):
        for row in self.row_widgets:
            # row is a dict of widgets
            # Get loco object for this row
            selected_loco = row["combo"].currentData()
            self._update_loco_status_field(row["status_container"], selected_loco)

    def _update_loco_status_field(self, status_container: QWidget, selected_loco: Loco) -> None:
        """ Updates the status field with loco status and buttons as appropriate
        removes existing widget(s) and replaced with new 
        if add button also connect to acquire_pressed
        Does not update assignments
        """

        self.clear_layout(status_container.layout())
        if selected_loco:
            
            if selected_loco.is_acquired():
                # ACTIVE STATE
                lbl = QLabel("✔ Active")
                lbl.setStyleSheet("color: green; font-weight: bold;")
                status_container.layout().addWidget(lbl)
            else:
                # INACTIVE STATE -> Show Warning + Button
                lbl = QLabel("⚠ Not Acquired")
                lbl.setStyleSheet("color: #d68a00; font-weight: bold;")
                status_container.layout().addWidget(lbl)
                
                btn = QPushButton("Acquire")
                btn.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px; padding: 2px 8px;")
                btn.setCursor(Qt.PointingHandCursor)
                # Connect acquire button
                btn.clicked.connect(lambda: self.acquire_pressed(selected_loco))
                status_container.layout().addWidget(btn)
        else:

            lbl = QLabel("--")
            lbl.setStyleSheet("color: #888;")
            status_container.layout().addWidget(lbl)
        # update button enable / disable
        self.validate_form()


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
        # If aleady allocated then say Acquired instead of Acquire
        # Still have ability to press though
        if loco.is_acquired():
            acq_button_text = "Acquired"
        else:
            acq_button_text = "Acquire"
        self.loco_table_buttons.append(QPushButton(acq_button_text))
        
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
        #    self.assignments [] = ""


        self.accept()
        
    def cancel(self):
        self.reject()

    def get_dict (self):
        # temp just convert list to dict
        return {item: item for item in self.locos}

    