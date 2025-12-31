from PySide6.QtCore import QRunnable, Slot, Signal, QObject, QThread, QThreadPool
from PySide6.QtWidgets import QMessageBox



# Helper QObject to hold signals (QRunnable cannot have signals)
class WorkerSignals(QObject):
    notify = Signal(str, str)  # title, message
    status = Signal(str)       # status message
    finished = Signal(int)   # sequence number
    error = Signal(tuple)
    result = Signal(object)