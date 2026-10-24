from PySide6.QtWidgets import QDial

class LocoThrottleDial(QDial):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWrapping(False)
        self.setMinimum(0)
        self.setMaximum(126)  # Standard 128-step DCC range (0-126)
        self._last_val = self.value()

    def setValue(self, val):
        # Programmatic updates (e.g., emergency stop button or external cab sync)
        # bypass the drag clamp
        self._last_val = max(self.minimum(), min(self.maximum(), val))
        super().setValue(self._last_val)

    def sliderChange(self, change):
        if change == QDial.SliderChange.SliderValueChange:
            new_val = self.value()
            span = self.maximum() - self.minimum()
            
            # Limit maximum instantaneous change to 20% of the dial range.
            # This blocks both bottom-dead-zone crossovers AND accidental clicks
            # on the opposite side of the dial face.
            max_jump = max(1, int(span * 0.20))
            
            if abs(new_val - self._last_val) > max_jump:
                self.blockSignals(True)
                # If we were already near the bottom or top, snap cleanly to the end-stop
                if self._last_val < (self.minimum() + max_jump):
                    target = self.minimum()
                elif self._last_val > (self.maximum() - max_jump):
                    target = self.maximum()
                else:
                    target = self._last_val
                
                super().setValue(target)
                self._last_val = target
                self.blockSignals(False)
                return
            
            self._last_val = new_val
            
        super().sliderChange(change)