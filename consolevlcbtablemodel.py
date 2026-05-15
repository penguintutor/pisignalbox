# Table model used by the console for VLCB log entries

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

class ConsoleVLCBTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        # This is for data only - UI is handled differently
        self._log_data = []  
        self._headers = ["Timestamp", "Direction", "Data", "CAN ID", "Op Code", "Data String", "Description"]

    def add_log_entry(self, log_details):
        new_row_index = len(self._log_data)
        
        # Announce that a new row is about to be inserted
        self.beginInsertRows(QModelIndex(), new_row_index, new_row_index)
        
        # Add to Python data
        self._log_data.append(log_details)
        
        # Update by Announcing that the insertion is complete
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()):
        return len(self._log_data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """The View calls this function whenever it needs to draw a specific cell."""
        if not index.isValid():
            return None

        # Handle the alignment for specific columns
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() in (1, 3):
                return Qt.AlignmentFlag.AlignCenter
            
            # Default alignment for all other columns
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        # DisplayRole is triggered when the View asks for the text to display
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()

            return self._log_data[row][col]
            
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """Provides the column headers."""
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None