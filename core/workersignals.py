from PySide6.QtCore import QRunnable, Slot, Signal, QObject, QThread, QThreadPool
from PySide6.QtWidgets import QMessageBox



# Helper QObject to hold signals (QRunnable cannot have signals)
class WorkerSignals(QObject):
    notify = Signal(str, str)  # title, message
    notify_wait = Signal(str, str, object)  # title, message, return value
    sequence_status = Signal(int, str)       # status message seq_num and status
    status = Signal(str)       # status message
    finished = Signal(int)   # sequence number
    error = Signal(tuple)
    result = Signal(object)