from PySide6.QtCore import Qt, QAbstractTableModel


class AutomateTableModel(QAbstractTableModel):
    """A simple table model"""
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._headers = ["Step number", "Description", "Comment"]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._data[0]) if self._data else 0

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return super().headerData(section, orientation, role)

    