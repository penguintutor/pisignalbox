from PySide6.QtWidgets import QDial, QAbstractSlider
from PySide6.QtCore import Signal, QTimer

class LocoThrottleDial(QDial):
    # Rate-limited signal specifically for sending commands to the layout bus
    speedChanged = Signal(int)

    def __init__(self, parent=None, tx_interval_ms=100):
        super().__init__(parent)
        self.setWrapping(False)
        self.setMinimum(0)
        self.setMaximum(126)
        self._last_val = self.value()
        self._last_sent_val = self.value()

        # Call on change
        #self.valueChanged.connect(self._queue_speed_update)
        #self.sliderReleased.connect(self._flush_speed_update)

    def setValue(self, val):
        """ This is set elsewhere - based on current speed
        disable triggers whilst updating to stop sending
        additional signals """
        #print (f"Setting value to {val}")
        # Programmatic updates bypass the drag clamp
        self.blockSignals(True)
        clamped = max(self.minimum(), min(self.maximum(), val))
        self._last_val = clamped
        super().setValue(clamped)
        self.blockSignals(False)

    def sliderChange(self, change):
        #print (f"Throttle slider change {change} new_val = {self.value()}")
        # Only trigger on SliderValueChange
        if change == QAbstractSlider.SliderChange.SliderValueChange:
            new_val = self.value()
            span = self.maximum() - self.minimum()

            # block change if > 75% jump (ie. from bottom to top)
            if span > 0 and abs(new_val - self._last_val) > (span * 0.75):
                self.blockSignals(True)
                super().setValue(self._last_val)
                self.blockSignals(False)
                return
            
            self._last_val = new_val
            self.speedChanged.emit(new_val)
        super().sliderChange(change)
        
