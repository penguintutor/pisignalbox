from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtGui import QColor


class AutomateTableModel(QAbstractTableModel):
    """A simple table model"""
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._headers = ["Step number", "Description", "Comment"]
        # selected tracks which line is currently active - highlighted
        # when changes can remove highlighting without 
        self._selected = 0
        self._selected_color = QColor("#d0e8ff")

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._data[0]) if self._data else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        # Handle text display
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        # Handle background colour
        if role == Qt.BackgroundRole and index.row() == self._selected:
            return self._selected_color
        return None

    def set_selected(self, row):
        """Highlights the specified row and removes the highlight from the previous one."""
        old_row = self._selected
        self._selected= row

        # Tell the view to redraw the old row to remove its background color
        if old_row is not None and 0 <= old_row < self.rowCount():
            top_left = self.index(old_row, 0)
            bottom_right = self.index(old_row, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.BackgroundRole])

        # Tell the view to redraw the new row to apply the pale blue color
        if self._selected is not None and 0 <= self._selected < self.rowCount():
            top_left = self.index(self._selected, 0)
            bottom_right = self.index(self._selected, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.BackgroundRole])

    def clear_selected(self):
        """Removes the highlight from the table."""
        self.set_selected(None)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return super().headerData(section, orientation, role)

    