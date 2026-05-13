# Proxy model (MVC) from ConsoleVLCBTableModel to vlcbTableView

from PySide6.QtCore import Qt, QSortFilterProxyModel

class ConsoleVLCBFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.show_keep_alive = True  # Checkbox state

    def set_show_keep_alive(self, show: bool):
        """Updates the filter state and triggers a re-evaluation."""
        self.show_keep_alive = show
        # invalidateFilter() tells the Proxy to re-run filterAcceptsRow on all data
        self.invalidateFilter() 

    def filterAcceptsRow(self, source_row, source_parent):
        """Returns True if the row should be visible, False if it should be hidden."""
        # If the checkbox is checked, allow all rows through
        if self.show_keep_alive:
            return True

        # Otherwise, check the Op Code (Column 1)
        # Note: We must fetch the data from the SOURCE model
        index = self.sourceModel().index(source_row, 1, source_parent)
        op_code_str = self.sourceModel().data(index, Qt.ItemDataRole.DisplayRole)

        # If it is a DKEEP message, return False (hide it). Otherwise True (show it).
        return op_code_str != "23 - DKEEP"