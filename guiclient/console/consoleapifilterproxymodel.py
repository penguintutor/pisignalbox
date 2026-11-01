# Proxy model (MVC) from ConsoleAutoTableModel to autoTableView

from PySide6.QtCore import Qt, QSortFilterProxyModel

class ConsoleApiFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.show_all = False  # Checkbox state - default is false

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

        # Filter responses unless show all
        # check type VLCB and command read
        index_type = self.sourceModel().index(source_row, 2, source_parent)
        type_val = self.sourceModel().data(index_type, Qt.ItemDataRole.DisplayRole)
        index_command = self.sourceModel().index(source_row, 3, source_parent)
        command_val = self.sourceModel().data(index_command, Qt.ItemDataRole.DisplayRole)

        if type_val == "VLCB" and command_val == "read":
            return False
        # Otherwise show
        return True