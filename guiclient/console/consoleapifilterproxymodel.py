# Proxy model (MVC) from ConsoleAutoTableModel to autoTableView

from PySide6.QtCore import Qt, QSortFilterProxyModel

class ConsoleApiFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.show_all = True  # Checkbox state

    def set_show_all(self, show: bool):
        """Updates the filter state and triggers a re-evaluation."""
        self.show_all = show
        # invalidateFilter() tells the Proxy to re-run filterAcceptsRow on all data
        self.invalidateFilter() 

    def filterAcceptsRow(self, source_row, source_parent):
        """Returns True if the row should be visible, False if it should be hidden."""
        # Placeholder - to allow filtering view in future - for now just return True to show all rows
        # If the checkbox is checked, allow all rows through
        if self.show_all:
            return True

        # Todo Filter here appropriate message
        # that are not included in show all
        # index = self.sourceModel().index(source_row, 4, source_parent)
        #op_code_str = self.sourceModel().data(index, Qt.ItemDataRole.DisplayRole)

        # If it is a DKEEP message, return False (hide it). Otherwise True (show it).
        #return op_code_str != "23 - DKEEP"
        return True