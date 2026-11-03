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
from core import event_bus
from .locomanager import loco_manager
from .locodialog import LocoDialog
from .stealdialog import StealDialog

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
        # Disable keep alive - moved to the server
        #self.update_kalive()
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
        ## Do not release unless requested
        #if session != None:
        #    self.api.start_request(self.api.vlcb.release_loco(session))
        #    self.control_loco.release()

        # Keep Alive is now handled by the server
        # Don't release as that would also release from web app
        # Todo in future could release but track separately who has requested loco
        # Although only a minor inconvenience - 
        # Esp if the server becomes the main controller
        # Check for a valid loco chosen (ie if gone back to 0 then return)
        if index == 0:
        #    if self.kalive_timer.isActive():
        #        self.kalive_timer.stop()
            return

        # Get the loco entry
        loco_name = self.ui.locoComboBox.currentText()

        # Get the loco entry
        loco = loco_manager.get_loco_from_name (loco_name)
            
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

        # Updated to use new loco client api
        #self.api.start_request(self.api.vlcb.allocate_loco(self.control_loco.get_id()))
        data_dict = {
            "request_type": "loco",
            "cmd": "acquire",
            "loco_id": self.control_loco.get_id()
        }
        self.api.start_api_request(data_dict)
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
        
    # Button has been clicked (ie. latch toggle operation)
    def loco_function_clicked (self):
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
        # If it's not a latch then ignore 
        if status == None or status[1] != "latch":
            return
        self.loco_func_change (func_index, 1-status[0])
        # Update button
        # perhaps separate functions to what is required
        self.loco_function_selected()

    # Button is pushed down - if trigger then send set signal
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
        # If it's not a trigger then ignore 
        if status == None or status[1] != "trigger":
            return
        # If trigger then button should be activate:
        self.loco_func_change (func_index, 1)

    # Button is relased down - if trigger then send unset signal
    def loco_function_released (self):
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
        # If it's not a trigger then ignore 
        if status == None or status[1] != "trigger":
            return
        # If trigger then button should be activate:
        self.loco_func_change (func_index, 0)

    # change value - only send once, the controller handles any resends
    def loco_func_change (self, func_index, value):
        # Update our local reference
        self.control_loco.set_function (func_index, value)
        data_dict = {
            "request_type": "loco",
            "cmd": "function",
            "loco_id": self.control_loco.get_id(),
            "function_index": func_index,
            "function_value": value
        }
        self.api.start_api_request(data_dict)


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
            # Replaces above request with new API request
            data_dict = {
                    "request_type": "loco",
                    "cmd": "set_speed",
                    "loco_id": self.control_loco.get_id(),
                    "speed": new_speed,
                    "direction": self.control_loco.loco.direction
                }
            self.api.start_api_request(data_dict)
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
        self.ui.locoComboBox.addItems(loco_manager.get_enabled_locos())
        
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
                

    def steal_loco_dialog (self):
        steal_dialog = StealDialog(self)
        steal_dialog.open()
        # Ignore the result of the dialog as it will emit own signals


    def update_controller_pos (self):
        active = self.control_loco.is_active()
        # Only change if active
        if active:
            # get current speed from loco
            speed = self.control_loco.speed_value()
            #print (f"UI Loco setting throttle {speed}")
            self.ui.locoDial.setValue(speed)
        # Update lcd even if not active as that sets --
        self.update_lcd()

        
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
        if (self.control_loco.stop()):
            self.api.start_request(self.api.vlcb.loco_speeddir(self.control_loco.get_session(), self.control_loco.get_speeddir()))
        self.ui.locoStatusLabel.setText (msg)
        self.update_lcd()
        
    # Emergency stop all
    def loco_stop_all (self):
        self.api.start_request(self.api.vlcb.loco_stop_all())
        self.ui.locoStatusLabel.setText ("Stop All!")
        self.update_lcd()


    ''' Methods for loco list '''
    def update_loco_table (self):
        locos = loco_manager.get_all_locos()
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
        # Using new api format
        data_dict = {
            "request_type": "loco",
            "cmd": "acquire",
            "loco_id": loco.loco_id
        }
        self.api.start_api_request(data_dict)
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

