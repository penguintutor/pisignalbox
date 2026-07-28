from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableView, QTabBar
from PySide6.QtCore import QAbstractTableModel

class UIAutomateViewMixin:
    """
    Mixin to manage dynamically created Automation Sequence tabs.
    Requires self.ui.PanelTabs.
    """
    
    def setup_automate_tabs(self):
        """Initializes tab behavior and the sequence registry."""
        # Todo - don't allow tab closure if still running
        self.ui.PanelTabs.setTabsClosable(True)
        ## We still allow manual closing by the user clicking 'X'
        self.ui.PanelTabs.tabCloseRequested.connect(self._manual_tab_close)

        # Access the underlying QTabBar
        tab_bar = self.ui.PanelTabs.tabBar()
        # Remove the close button from the permanent tab at index 0.
        # Depending on the OS and theme, the close button might be on the right or left. 
        # Setting both to None guarantees it disappears everywhere.
        tab_bar.setTabButton(0, QTabBar.RightSide, None)
        tab_bar.setTabButton(0, QTabBar.LeftSide, None)
        
        # Registry to map sequence_id -> {'widget': QWidget, 'model': QAbstractTableModel}
        self._active_sequences = {}

    def start_sequence_tab(self, sequence_id: str, tab_title: str, description: str, model: QAbstractTableModel):
        """
        Creates a tab for a new automation sequence and registers it.
        """
        if sequence_id in self._active_sequences:
            print(f"Warning: Sequence {sequence_id} is already running.")
            return

        new_tab = QWidget()
        # Optional: store the sequence ID on the widget itself as a property
        new_tab.setProperty("sequence_id", sequence_id) 
        
        layout = QVBoxLayout(new_tab)

        if description:
            label = QLabel(description)
            layout.addWidget(label)

        table_view = QTableView()
        table_view.setModel(model)
        layout.addWidget(table_view)

        # Register the widgets BEFORE adding to the UI
        self._active_sequences[sequence_id] = {
            'widget': new_tab,
            'model': model
        }

        # Add to the tab widget
        index = self.ui.PanelTabs.addTab(new_tab, tab_title)
        self.ui.PanelTabs.setCurrentIndex(index)

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