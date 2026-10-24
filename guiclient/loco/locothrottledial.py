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

        # Timer to rate-limit outgoing bus commands (100ms = max 10 packets/sec)
        self._tx_timer = QTimer(self)
        self._tx_timer.setSingleShot(True)
        self._tx_timer.setInterval(tx_interval_ms)
        self._tx_timer.timeout.connect(self._emit_pending_speed)

        # Double-layer protection and signal pipeline
        self.actionTriggered.connect(self._on_action_triggered)
        self.valueChanged.connect(self._queue_speed_update)
        self.sliderReleased.connect(self._flush_speed_update)

    def setValue(self, val):
        # Programmatic updates bypass the drag clamp
        clamped = max(self.minimum(), min(self.maximum(), val))
        self._last_val = clamped
        super().setValue(clamped)

    def _on_action_triggered(self, action):
        if action in (
            QAbstractSlider.SliderAction.SliderMove,
            QAbstractSlider.SliderAction.SliderPageStepAdd,
            QAbstractSlider.SliderAction.SliderPageStepSub,
        ):
            proposed = self.sliderPosition()
            span = self.maximum() - self.minimum()

            if span > 0:
                low_zone = self.minimum() + (span * 0.25)
                high_zone = self.maximum() - (span * 0.25)

                # If we were near zero and jumped into the high zone, lock at 0
                if self._last_val <= low_zone and proposed >= high_zone:
                    self.setSliderPosition(self.minimum())
                    self._last_val = self.minimum()
                    return
                # If we were near max and jumped into the low zone, lock at max
                elif self._last_val >= high_zone and proposed <= low_zone:
                    self.setSliderPosition(self.maximum())
                    self._last_val = self.maximum()
                    return
                
                # General safety catch for any massive single-frame jump (> 50%)
                if abs(proposed - self._last_val) > (span * 0.5):
                    self.setSliderPosition(self._last_val)
                    return

            self._last_val = proposed

    def sliderChange(self, change):
        # Safety net: catches any value change that bypassed actionTriggered
        if change == QAbstractSlider.SliderChange.SliderValueChange:
            new_val = self.value()
            span = self.maximum() - self.minimum()
            
            if span > 0 and abs(new_val - self._last_val) > (span * 0.5):
                self.blockSignals(True)
                target = self.minimum() if self._last_val < (self.minimum() + span * 0.25) else self.maximum()
                super().setValue(target)
                self._last_val = target
                self.blockSignals(False)
                return
            
            self._last_val = new_val
            
        super().sliderChange(change)

    def _queue_speed_update(self, val):
        # If the dial hits 0 (Stop), send it immediately without waiting for the timer
        if val == self.minimum() and self._last_sent_val != val:
            self._tx_timer.stop()
            self._last_sent_val = val
            self.speedChanged.emit(val)
            return

        if not self._tx_timer.isActive():
            if val != self._last_sent_val:
                self._last_sent_val = val
                self.speedChanged.emit(val)
                self._tx_timer.start()

    def _emit_pending_speed(self):
        current = self.value()
        if current != self._last_sent_val:
            self._last_sent_val = current
            self.speedChanged.emit(current)
            self._tx_timer.start()

    def _flush_speed_update(self):
        self._tx_timer.stop()
        current = self.value()
        if current != self._last_sent_val:
            self._last_sent_val = current
            self.speedChanged.emit(current)