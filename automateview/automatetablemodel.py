from PySide6.QtCore import Qt, QAbstractTableModel


class AutomateTableModel(QAbstractTableModel):
    """A simple dummy model just so you can test the table view immediately."""
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._data[0]) if self._data else 0

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        return None