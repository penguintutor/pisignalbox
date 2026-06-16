# UI Loco Package - as UILocoMixin
# Included into MainWindow

# Loco module for handling loco operations for mainwindow
# This includes the UI wrapper class for loco control and the locolist
import os
import sys
import time
from PySide6.QtCore import QTimer, QSize
from PySide6.QtWidgets import QMenu, QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QPushButton
from PySide6.QtGui import QPixmap, QImage, QPalette, QColor, QFont, QResizeEvent
# Delayed loading due to circular import
#from core import device_model, event_bus
from locodialog import LocoDialog
from stealdialog import StealDialog

class UILocoMixin:

    def steal_loco (self):
        self.api.start_request(self.api.vlcb.steal_loco(self.control_loco.get_id()))
        response = self.control_loco.steal_loco ()
        self.ui.locoStatusLabel.setText(response)

    def share_loco (self):
        self.api.start_request(self.api.vlcb.share_loco(self.control_loco.get_id()))
        response = self.control_loco.share_loco ()
        self.ui.locoStatusLabel.setText(response)
        
    # Reset loco selection in GUI and remove references
    def reset_loco (self):
        self.control_loco.reset_loco ()
        self.reset_loco_gui()
        
    # Extract GUI from reset_loco - so can be used from an app event
    def reset_loco_gui (self):
        self.update_kalive()
        # Change combo after reset - that way the post change
        # will not send a release message
        self.ui.locoComboBox.setCurrentIndex(0)
        self.ui.locoStatusLabel.setText("None active")

    # or if loco removed from list in that case defaults to index=0 (Select Loco)
    def loco_change (self, index=0):
        # Change in operation - no longer release old locos
        # Keep for use by automation or to allow quick switch
        # between locos
        # Release old loco
        # session = self.control_loco.get_session()
        # If not session then nothing to release
        ## Do not release uless requested
        #if session != None:
        #    self.api.start_request(self.api.vlcb.release_loco(session))
        #    self.control_loco.release()

        # Check for a valid loco chosen (ie if gone back to 0 then return)
        if index == 0:
            if self.kalive_timer.isActive():
                self.kalive_timer.stop()
            return

        # Get the loco entry
        loco_name = self.ui.locoComboBox.currentText()

        # Get the loco entry
        from core import device_model
        loco = device_model.get_loco_from_name (loco_name)
            
        # If don't get a loco then close
        if loco == None:
            print ("No loco found with name {loco_name}")
            return


        self.control_loco.loco = loco

        self.ui.locoStatusLabel.setText(f"Acquiring {loco_name}")
        #self.control_loco.loco.set_status('rloc', "controller") - done by control_loco.set_status instead
        # Add images and summary
        if "image" in self.control_loco.loco.loco_data and self.control_loco.loco.loco_data['image'] != "":
            self.loco_image = QPixmap(os.path.join(self.dirs['locos'], self.control_loco.loco.loco_data['image']))
        else:
            self.loco_image = QPixmap(os.path.join(self.dirs['locos'], "default.png"))
        self.ui.locoImage.setPixmap(self.loco_image)
        # Scale the image to fit (include minimum size when first loading)
        self.scale_image_to_fit(QSize(280, 180))
        if "summary" in self.control_loco.loco.loco_data:
            self.ui.locoInfoText.setText(self.control_loco.loco.loco_data['summary'])
        else:
            self.ui.locoInfoText.setText("")

        self.api.start_request(self.api.vlcb.allocate_loco(self.control_loco.get_id()))
        self.control_loco.set_status('rloc')

        # Update the functions menu
        self.loco_change_functions(0)
        self.control_loco.function_reset()

    # Update function selected features
    # When combobox / tab selected
    def loco_function_selected (self):
        # get current index, need both tab and position in tab
        tab = self.ui.locoFuncTab.currentIndex()
        combo = self.ui.locoFuncCombo.currentIndex()
        #print (f"Tab {tab}, Combo {combo}")
        func_index = combo + (10 * tab)
        status_text = self.control_loco.function_selected(func_index)
        self.ui.locoFuncButton.setText (status_text)
        
    # Button has been pressed
    def loco_function_pressed (self):
        # Check that button is valid (ie. not "-")
        button_text = self.ui.locoFuncButton.text()
        if button_text == "" or button_text == "-" or button_text == " - ":
            return
        # get current index, need both tab and position in tab
        tab = self.ui.locoFuncTab.currentIndex()
        combo = self.ui.locoFuncCombo.currentIndex()
        #print (f"Tab {tab}, Combo {combo}")
        func_index = combo + (10 * tab)
        #self.control_loco.function_pressed(func_index)
        status = self.control_loco.get_function_status(func_index)
        # If no status then ignore
        if status == None:
            return
        # If trigger then button should be activate:
        if status[1] == "trigger":
            self.loco_func_trigger (func_index)
            # no need to update button as still says activate
        else:
            # if <= F12 then send multiple times (NRMA standard)
            if func_index <= 12:
                self.loco_func_change (func_index, 1-status[0], 3)
            # otherwise send once
            else:
                #self.func_change (func_index, 1-status[0])
                self.loco_func_change (func_index, 1-status[0])
            # Update button
            # perhaps separate functions to what is required
            self.loco_function_selected()
            

    # change value (if need to send multiple then set num_send to number of times
    # Sent every 2 seconds (or change delay) - delay in seconds
    def loco_func_change (self, func_index, value, num_send = 1, delay = 2):
        byte1_2 = self.control_loco.set_function_dfun (func_index, value)
        # If None then cancel
        if byte1_2 == None:
            return
        request = self.api.vlcb.loco_set_dfun(self.control_loco.get_session(), *byte1_2)
        self.api.start_request_repeat (request, num_send, delay)

    # Sends on followed by off (typically 4 seconds later)
    def loco_func_trigger (self, func_index, delay = 4):
        #print (f"Func trigger api {func_index}")
        # Turn on
        byte1_2 = self.control_loco.set_function_dfun (func_index, 1)
        if byte1_2 == None:
            return
        request_on = self.api.vlcb.loco_set_dfun(self.control_loco.get_session(), *byte1_2)
        # Turn off (update value immediately - even though not sent yet, but delay request using single shot timer
        byte1_2 = self.control_loco.set_function_dfun (func_index, 0)
        request_off = self.api.vlcb.loco_set_dfun(self.control_loco.get_session(), *byte1_2)
        
        self.api.start_request_onoff (request_on, request_off, delay)

    # Update the functions list
    # If index is not provided then use current
    # otherrwise set to the index tab
    def loco_change_functions (self, index=None):
        functions = self.control_loco.get_functions()
        if index != None and index >=0 and index <=2:
            self.ui.locoFuncTab.setCurrentIndex(index)
        else:
            index = self.ui.locoFuncTab.currentIndex()

        # Clear current
        self.ui.locoFuncCombo.clear()

        # put functions based on the tabs
        # typically maximum of twenty something  (28 is the maximum officially supported) but some DCC controllers allow more
        # all rest are put on last tab
        start = 0
        end = 10  # end is actually 1 after to fit in with range command
        if index == 1:
            start = 10
            end = 20
        elif index == 2:
            start = 20
            end = len(functions)
            
        if end > len(functions):
            end = len(functions)
            
        for i in range(start, end):
            self.ui.locoFuncCombo.addItem(functions[i])
            
        # Update function selected features
        self.loco_function_selected ()
        
        
    # This is used based on the dial
    def loco_change_speed (self, new_speed):
        # If returns false then loco not active so ignore
        if (self.control_loco.change_speed(new_speed)):
            self.api.start_request(self.api.vlcb.loco_speeddir(self.control_loco.get_session(), self.control_loco.get_speeddir()))
            self.ui.locoStatusLabel.setText ("Ready")
            self.update_lcd()
        else:
            self.ui.locoStatusLabel.setText ("Released")
            
    # Updates the list of locos (both initial and when locos added / removed)
    # Preserves list if already selected
    def update_loco_list (self):
        # save current entry name - set this active if
        current_index = self.ui.locoComboBox.currentIndex()
        current_loco_text = self.ui.locoComboBox.itemText(current_index) if current_index > 0 else None
        
        # Block signals whilst updating
        self.ui.locoComboBox.blockSignals(True)
        
        self.ui.locoComboBox.clear()
        # Readd the default - none selected
        self.ui.locoComboBox.addItem("Select Locomotive")
        # Add all the locos
        from core import device_model
        self.ui.locoComboBox.addItems(device_model.get_enabled_locos())
        
        # Set back to previous entry if still valid
        if current_loco_text:
            # Find the index of the previously selected loco in the new list
            new_index = self.ui.locoComboBox.findText(current_loco_text)
            
            if new_index != -1: # Loco was found
                self.ui.locoComboBox.setCurrentIndex(new_index)
                # no need to update
            else: # Loco was removed
                # Entry changed so call loco_change manually
                self.loco_change()
        # Enable the signal
        self.ui.locoComboBox.blockSignals(False)
                
        # Returns the list of locos - using get name
        #for loco_name in device_model.get_enabled_locos():
        #    self.ui.locoComboBox.addItem(loco_name)
        #for loco_name in self.railway.get_loco_names():
        #    self.ui.locoComboBox.addItem(loco_name)

    def steal_loco_dialog (self):
        steal_dialog = StealDialog(self)
        steal_dialog.open()
        # Ignore the result of the dialog as it will emit own signals


        
    # Update the LCD display based on the speed
    def update_lcd (self):
        # If not in a session show --
        active = self.control_loco.is_active()
        if active == None or active == False or self.control_loco.get_status() == "stop" :
            self.ui.locoSpeedLcd.display("--")
        # If 0 then use string to ensure 0 displayed
        elif self.control_loco.speed_value() == 0:
            self.ui.locoSpeedLcd.display("0")
        else:
            self.ui.locoSpeedLcd.display(self.control_loco.speed_value())
        if self.control_loco.get_direction() == 1:
            self.ui.locoForwardRadio.setChecked(True)
        elif self.control_loco.get_direction() == 0:
            self.ui.locoReverseRadio.setChecked(True)

    # Signal to indicate kalive needs to be checked
    # start / stop as appropriate
    def update_kalive (self):
        #if self.control_loco.is_active():
        from core import device_model
        if device_model.locos_active() > 0:
            if not self.kalive_timer.isActive():
                self.kalive_timer.start()
        elif self.kalive_timer.isActive():
            self.kalive_timer.stop()

    # Keep alive - called every 4 secs
    # Add a keep alive to the send queue
    def keep_alive (self):
        # Check we have a session to send a keep alive (ie. not in process of trying
        # to acquire a new loco
        # Check all locos 
        from core import device_model
        for loco in device_model.get_all_locos():
            if loco.is_active():
                #print (f"Loco {loco.loco_id} is active")
                self.api.start_request(self.api.vlcb.keep_alive(loco.get_session()))
            
    def steal_loco_check (self):
        steal_dialog = QDialog(self)
        steal_dialog.exec_()
        
    def loco_forward (self):
        # disable button if not active
        if self.control_loco.is_active():
            # set forward and check active
            if (self.control_loco.forward()):
                self.api.start_request(self.api.vlcb.loco_speeddir(self.control_loco.get_session(), self.control_loco.get_speeddir()))
                self.update_lcd()
        
    def loco_reverse (self):
        if self.control_loco.is_active():
            # set reverse and check active
            if (self.control_loco.reverse()):
                self.api.start_request(self.api.vlcb.loco_speeddir(self.control_loco.get_session(), self.control_loco.get_speeddir()))
                self.update_lcd()
        
        
    # Emergency stop - current loco
    # To reset need to set speed to 0 on the dial
    def loco_stop (self, msg="STOP!"):
        # If not active then ignore
        if not self.control_loco.is_active():
            return
        # If calling from a clicked then gives False rather than msg
        if msg == False:
            msg = "STOP!"
        # Need to check we have a valid session (although issue stop regardless of speed)
        if (self.control_loco.stop(msg)):
            self.api.start_request(self.api.vlcb.loco_speeddir(self.control_loco.get_session(), self.control_loco.get_speeddir()))
        self.ui.locoStatusLabel.setText (msg)
        self.update_lcd()
        
    # Emergency stop all
    def loco_stop_all (self):
        #self.control_loco.stop_all()
        self.api.start_request(self.api.vlcb.loco_stop_all())
        self.ui.locoStatusLabel.setText ("Stop All!")
        self.update_lcd()


    ''' Methods for loco list '''
    def update_loco_table (self):
        from core import device_model
        locos = device_model.get_all_locos()
        # Reset table and remove buttons 
        self.ui.locoTable.setRowCount(0)
        self.loco_table_list = []
        self.loco_table_buttons = []
        for loco in locos:
            self.add_loco_to_table (loco)

    def add_loco_to_table(self, loco):
        """
        Adds a new row to the table with the loco name and an Acquire button.
        """
        # Get the current number of rows to find the index for the new row
        row = self.ui.locoTable.rowCount()
        self.ui.locoTable.insertRow(row)

        self.loco_table_list.append(loco)

        # Add the Locomotive Name (Column 0)
        # We use QTableWidgetItem for standard strings
        name_item = QTableWidgetItem(loco.get_display_name())
        self.ui.locoTable.setItem(row, 0, name_item)

        # Create the Acquire Button (Column 1)
        self.loco_table_buttons.append(QPushButton("Acquire"))
        
        # Connect the signal 
        # We use a lambda to pass the specific 'loco' object to the handler.
        # Note: 'l=loco' captures the current value of loco. 
        # If you skip this, all buttons will try to acquire the last loco added.
        self.loco_table_buttons[row].clicked.connect(lambda checked=False, l=loco: self.acquire_pressed(l))

        # Insert the widget into the table
        # setCellWidget is required for buttons (setItem is only for text/icons)
        self.ui.locoTable.setCellWidget(row, 1, self.loco_table_buttons[row])

    def acquire_pressed(self, loco):
        """
        Slot to handle the button click
        """
        print(f"Acquiring locomotive: {loco.get_display_name()}")
        # Acquire loco
        self.api.start_request(self.api.vlcb.allocate_loco(loco.loco_id))
        loco.set_status('rloc', "controller")


    def get_button_style(self, color_hex):
        """Returns the stylesheet string with the requested background color."""
        return f"""
            QPushButton {{
                background-color: {color_hex};
                color: white;
                border-radius: 5px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {color_hex}AA; /* Slightly transparent version for hover */
            }}
        """


    def update_loco_status(self, loco_id, status):
        """
        Updates the button color based on the status.
        Status can be: 'acquired', 'stolen', 'released', 'idle'
        """
        if loco_id not in self.loco_buttons:
            print(f"Error: Loco {loco_id} not found in table.")
            return

        btn = self.loco_buttons[loco_id]

        if status == "acquired":
            btn.setText("Acquired")
            btn.setStyleSheet(self.get_button_style("#4CAF50")) # Green
            
        elif status in ["stolen", "released"]:
            btn.setText(status.capitalize()) # Changes text to "Stolen" or "Released"
            btn.setStyleSheet(self.get_button_style("#D32F2F")) # Red
            
        else: # Reset to idle
            btn.setText("Acquire")
            btn.setStyleSheet(self.get_button_style("#78909C")) # Grey

