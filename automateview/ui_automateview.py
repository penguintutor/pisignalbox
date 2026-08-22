from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableView, QTabBar
from PySide6.QtCore import QAbstractTableModel
from PySide6.QtWidgets import QAbstractItemView
from automateview import AutomateTableModel


class UIAutomateViewMixin:
    """
    Mixin to manage dynamically created Automation Sequence tabs.
    Requires self.ui.PanelTabs.

    tabs are created, destroyed and added to PanelTabs as required. 
    The sequence_id is the index entry in automation manager

    Various parts are stored in the _active_sequences including the QWidget 
    within the tab, but the tab itself is not - that can be obtained using
    _sequence_to_tab_index which uses indexOf based on the QWidget
    see _enable_tab_close for an example

    
    """
    

    def _sequence_to_tab_index (self, sequence_id):
        # Lookup the Qwidget
        widget = self._active_sequences[sequence_id]['widget']
        # Find the index of widget in the tab_bar
        tab_index = self.ui.PanelTabs.indexOf(widget)
        # returns -1 if not found - instead return None

        if tab_index < 0:
            return None
        return tab_index
        

    def _enable_tab_close(self, tab_index, enable=False):
        """ Enable / Disable close tab from a tab
        By default they start enabled.
        Disable for tab 0 (never close the signal box tab)
        Disable can be used to disable tab close whilst a sequence running
        """
        # Access the underlying QTabBar
        tab_bar = self.ui.PanelTabs.tabBar()

        # Remove the close button from the permanent tab at index 0.
        # Depending on the OS and theme, the close button might be on the right or left. 
        # Setting both to None guarantees it disappears everywhere.
        #tab_bar.setTabButton(0, QTabBar.RightSide, None)
        #tab_bar.setTabButton(0, QTabBar.LeftSide, None)
        close_button = tab_bar.tabButton(tab_index, QTabBar.RightSide)
        if close_button:
            if enable == True:
                close_button.show()
            else:
                close_button.hide()

    def setup_automate_tabs(self):
        """Initializes tab behavior and the sequence registry."""
        # Allow tabs closure (used by automation)
        # But then disable
        self.ui.PanelTabs.setTabsClosable(True)
        ## We allow manual closing by the user clicking 'X'
        self.ui.PanelTabs.tabCloseRequested.connect(self._manual_tab_close)

        self._enable_tab_close (0, False)
        
        # Registry to map sequence_id -> {'widget': QWidget, 'model': QAbstractTableModel}
        self._active_sequences = {}

    def start_sequence_tab(self, sequence_id: str, tab_title: str, description: str, id_str: str, model: QAbstractTableModel):
        """
        Creates a tab for a new automation sequence and registers it.
        """
        if sequence_id in self._active_sequences:
            print(f"Warning: Sequence {sequence_id} is already running.")
            return

        tab_title_string = f"Auto: {tab_title}"

        new_tab = QWidget()
        # Optional: store the sequence ID on the widget itself as a property
        new_tab.setProperty("sequence_id", sequence_id) 
        
        layout = QVBoxLayout(new_tab)

        if description:
            description_string = f"Automation Sequence: <span style='font-weight: bold;'>{description}</span>"
            label = QLabel(description_string)
            layout.addWidget(label)

        if id_str:
            id_string = f"ID: <span style='font-weight: bold;'>{id_str}</span"
            id_label = QLabel(id_string)
            layout.addWidget(id_label)

        # Initially set to blank - will be updated to Status: Starting
        status_string = "Status:"
        status_label = QLabel(status_string)
        layout.addWidget(status_label)

        table_view = QTableView()
        table_view.setModel(model)
        table_view.verticalHeader().setVisible(False)
        layout.addWidget(table_view)

        # Register the widgets BEFORE adding to the UI
        # Save the things we may need to change in future
        # Alternative ways of doing this through setting object names
        # but this is a fast and simple way to implement
        self._active_sequences[sequence_id] = {
            'widget': new_tab,
            'status_label': status_label,
            'model': model,
            'table_view': table_view
        }

        # Add to the tab widget
        index = self.ui.PanelTabs.addTab(new_tab, tab_title_string)
        self.ui.PanelTabs.setCurrentIndex(index)
        # Set initial status to Starting
        self.update_automation_status (sequence_id, "starting")


    def update_automation_status (self, sequence_id: str, status: str):
        """ Updates the status entry"""
        # Check that sequence_id is valid (could have been destroyed)
        if sequence_id not in self._active_sequences: 
            return
        # If it's running then hide the close button on the tab
        if status == "running":
            # get index of the tab with the sequence
            index = self._sequence_to_tab_index(sequence_id)
            if index != None:
                self._enable_tab_close (index, False)
        # If stopped or finished then enable close button
        elif status == "stopped" or status == "finished":
            # get index of the tab with the sequence
            index = self._sequence_to_tab_index(sequence_id)
            if index != None:
                self._enable_tab_close (index, True)
        ## Set the status message
        # Is there a colour in the settings we want to display this as (if not then use normal text colour)
        status_color = self.settings.get_setting("statuscolors", status)
        if status_color != None:
            # use html span to set colour
            formatted_status = f"Status: <span style='color: {status_color}; font-weight: bold;'>{status}</span>"
        else:
            formatted_status = f"Status: <span style='font-weight: bold;'>{status}</span>"
        self._active_sequences[sequence_id]['status_label'].setText(formatted_status)


    def get_sequence_model(self, sequence_id: str) -> QAbstractTableModel:
        """
        Retrieves the model for a running sequence so you can update data.
        """
        if sequence_id in self._active_sequences:
            return self._active_sequences[sequence_id]['model']
        return None

    def close_sequence_tab(self, sequence_id: str):
        """
        Triggered by a signal when a sequence finishes. 
        Safely finds the tab's current index and removes it.
        """
        if sequence_id not in self._active_sequences:
            return

        # Retrieve the widget from our registry
        widget = self._active_sequences[sequence_id]['widget']
        
        # Ask Qt for the CURRENT index of this specific widget
        current_index = self.ui.PanelTabs.indexOf(widget)
        
        if current_index != -1:
            self.ui.PanelTabs.removeTab(current_index)
            widget.deleteLater()
            
        # Clean up our registry
        del self._active_sequences[sequence_id]

    def _manual_tab_close(self, index: int):
        """
        Handles the event where a user manually clicks the 'X' on a tab.
        """
        if index == 0:
            print("Cannot close the primary Track View tab.")
            return

        widget = self.ui.PanelTabs.widget(index)
        if widget is not None:
            # Check if this tab belongs to an automation sequence
            seq_id = widget.property("sequence_id")
            
            if seq_id and seq_id in self._active_sequences:
                # Optionally: Send a signal to your thread here to abort the sequence!
                # e.g., self.abort_sequence_signal.emit(seq_id)
                del self._active_sequences[seq_id]

            self.ui.PanelTabs.removeTab(index)
            widget.deleteLater()


    def create_automation_tab(self, sequence_id, sequence):
        """Slot to test our UIAutomateViewMixin functionality."""

        data = sequence.get_step_data()                
        model = AutomateTableModel(data)
        
        title = sequence.get_short_title()
        description = sequence.get_title()
        id_string = f"{sequence_id}"
        
        # Register and create the tab
        self.start_sequence_tab(
            sequence_id=sequence_id,
            tab_title=title,
            description=description,
            id_str=id_string,
            model=model
        )


    def update_automation_position(self, sequence_id, index):
        #print (f"Active sequences {self._active_sequences}")
        #print (f"Running Sequence {sequence_id}, {index}")
        self.select_and_scroll(sequence_id, index)


    def select_and_scroll(self, sequence_id, row):
        """selects a row by highlighting and scrolls to that row"""
        # Check that sequence_id is valid (could have been destroyed)
        if sequence_id not in self._active_sequences: 
            return
        # Update the model to highlight the row
        self._active_sequences[sequence_id]['model'].set_selected(row)
        
        # Generate a QModelIndex for the row (column 0 is fine)
        index = self._active_sequences[sequence_id]['model'].index(row, 0)
        
        # Command the view to scroll to that index
        # Options are 
        #   EnsureVisible: If the row is already visible on the screen, it does nothing. If it's off-screen, it scrolls just enough to bring it into view.
        #   PositionAtCenter: Always scrolls the table so the highlighted row is exactly in the middle of the view.
        #   PositionAtTop: Always scrolls so the highlighted row is the very first row at the top of the table.
        #   PositionAtBottom: Always scrolls so the highlighted row is at the very bottom of the table.
        self._active_sequences[sequence_id]['table_view'].scrollTo(index, QAbstractItemView.EnsureVisible)


    def _simulate_thread_finished(self, sequence_id: str):
        """Simulates the slot that catches your thread's completion signal."""
        print(f"Sequence {sequence_id} complete. Cleaning up tab.")
        self.close_sequence_tab(sequence_id)