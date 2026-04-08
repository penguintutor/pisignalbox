# Layout module for handling layout operations for mainwindow
# This includes the UI wrapper class for the layout view
# Also includes dialogs for editing layout objects
import shutil
import os
import sys
import time
from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtWidgets import QMenu, QDialog, QFileDialog, QMessageBox, QColorDialog
from PySide6.QtGui import QPixmap, QImage, QPalette, QColor, QFont, QResizeEvent
from PySide6.QtUiTools import QUiLoader
from devicemodel import device_model
from eventbus import event_bus
from imageexistdialog import ImageExistDialog
from layoutdialog import LayoutDialog

def change_layout_dialog (self):
    layout_dialog = LayoutDialog(self, self.data_dir, self.dirs['layouts'], self.files['layouts'], self.settings)
    result = layout_dialog.exec()
    # If not changed then ignore
    if result != 1:
        return    
        
    # Get the new Layout filename
    new_filename = layout_dialog.selected_layout
    self.railway.load_file(new_filename)
    
    self.ui.layoutDisplayLabel.set_layout(self, self.railway)
    # Update the layout display
    # Includes load layout background image
    # and UI objects
    self.ui.layoutDisplayLabel.update()

# Get a new image name then pass to the layoutDisplay
def change_layout_image_dialog (self):
    file_dialog = QFileDialog(self,
                    caption="Select Background Image",
                    directory=self.dirs['layouts'],
                    filter="Images (*.png *.jpg *.jpeg *.bmp)",
                    fileMode=QFileDialog.FileMode.ExistingFile
                    )

    # Get filename
    if file_dialog.exec():
        selected_file = file_dialog.selectedFiles()[0]
        
        filename = os.path.basename(selected_file)
        
        # Is the file in the layoutdir then move on to
        # updating in the layout - but if it's not then we need to copy (perhaps)
        if not self.is_datadir(selected_file, 'layouts'):
            # if not then copy it there (if exist check overwrite with user first)
            new_path = os.path.join(self.dirs['layouts'], filename)
            # If it's not existing just copy
            if not (os.path.exists(new_path)):
                shutil.copyfile (selected_file, new_path)
            # File is not in layouts directory and already matching file
            # Create new dialog to get confirmation / new filename
            else:
                exist_dialog = ImageExistDialog (self, self.dirs['layouts'])
                if exist_dialog.exec() == QDialog.Accepted:
                    # Handle dialog response here
                    # saved in self.dialog.action
                    if exist_dialog.action == "overwrite":
                        # copy over existing
                        shutil.copyfile (selected_file, new_path)
                    elif exist_dialog.action == "existing":
                        # nothing to do just use the existing
                        pass
                    # For new file to be selected then we should have already checked
                    # that the filename is valid
                    elif exist_dialog.action == "save":
                        new_filename = exist_dialog.ui.filenameEdit.text()
                        new_path = os.path.join(self.dirs['layouts'], new_filename)
                        #print (f"Copying {selected_file} to {new_path}")
                        shutil.copyfile (selected_file, new_path)
                        filename = new_filename
                    else:
                        # Unknown state
                        return
                # Most likely cancel pressed just ignore
                else:
                    return
        # Reach here then filename is valid    
        # Save it into layout (includes a save)
        self.railway.set_layout_image (filename)
        
        # Tell layout display to update
        self.ui.layoutDisplayLabel.load_image()


# Toggles between layout edit and control mode
# or provide mode to switch to that mode (control / edit)
def layout_edit (self, mode="toggle"):
    #print (f"Changing {mode} - {self.ui.layoutDisplayLabel.mode}")
    # if set is not valid then defaults to control (not expected)
    # If called from menu then mode will be False
    if mode == "toggle" or mode == False:
        if self.ui.layoutDisplayLabel.mode == "control":
            self.ui.layoutDisplayLabel.mode = "edit"
        else:
            self.ui.layoutDisplayLabel.mode = "control"
    elif mode == "edit":
        self.ui.layoutDisplayLabel.mode = "edit"
    else:
        self.ui.layoutDisplayLabel.mode = "control"
    # Change layoutdisplay mode
    if self.ui.layoutDisplayLabel.mode == "edit":
        self.ui.actionLayoutEdit.setText("Layout Control")
        #self.ui.menuEditLayout.setVisible(True)
        self.ui.menuEditLayoutAction.setVisible(True)
    else:
        self.ui.actionLayoutEdit.setText("Layout Edit")
        #self.ui.menuEditLayout.setVisible(False)
        self.ui.menuEditLayoutAction.setVisible(False)
        # When switching back to control from edit then save config
        self.railway.save_file()

def edit_dialog_layoutbutton (self, loader, filepath):
    """ Dialog for creating and editing Layout Buttons
    """
    # Current object - for easy ref
    button = self.selected_node
    gui_obj = button.parent
    # Load the dialog
    self.edit_gui_dialog = loader.load(filepath, self)
    self.edit_gui_dialog.devNameText.setText (gui_obj.name)
    self.edit_gui_dialog.buttonNameText.setText (button.get_long_name())
    # buttonTypeCombo is a combo box
    # Set text to current value will set selection default - use True to capitalize
    self.edit_gui_dialog.buttonTypeCombo.setCurrentText(button.get_type_str(True))
    ## Set size
    self.edit_gui_dialog.buttonSizeXBox.setValue(button.size[0])
    self.edit_gui_dialog.buttonSizeYBox.setValue(button.size[1])
    # If it's a circle then only one dimension so hide Y
    if button.get_type_str(True) == "Circle":
        self.edit_gui_dialog.buttonSizeYBox.hide()
    else:
        self.edit_gui_dialog.buttonSizeYBox.show()
    self.edit_gui_dialog.valueBox.setValue(button.click_value)
    # Set colors
    color_palette = self.edit_gui_dialog.colorUnknownButton.palette()
    color_palette.setColor(QPalette.Button, QColor(button.button_colors[0]))
    self.edit_gui_dialog.colorUnknownButton.setPalette(color_palette)
    self.edit_gui_dialog.colorUnknownButton.setAutoFillBackground(True)
    # On
    color_palette = self.edit_gui_dialog.colorOnButton.palette()
    color_palette.setColor(QPalette.Button, QColor(button.button_colors[1]))
    self.edit_gui_dialog.colorOnButton.setPalette(color_palette)
    self.edit_gui_dialog.colorOnButton.setAutoFillBackground(True)
    # Off
    color_palette = self.edit_gui_dialog.colorOffButton.palette()
    color_palette.setColor(QPalette.Button, QColor(button.button_colors[2]))
    self.edit_gui_dialog.colorOffButton.setPalette(color_palette)
    self.edit_gui_dialog.colorOffButton.setAutoFillBackground(True)
    
    # Add a listener for change to typeComboBox
    self.edit_gui_dialog.buttonTypeCombo.currentIndexChanged.connect(self.button_type_change)
    # Listener for the color pickers
    self.edit_gui_dialog.colorUnknownButton.clicked.connect(self.color_picker_unknown)
    self.edit_gui_dialog.colorOnButton.clicked.connect(self.color_picker_on)
    self.edit_gui_dialog.colorOffButton.clicked.connect(self.color_picker_off)
    
    result = self.edit_gui_dialog.exec()
    
    if result == QDialog.Accepted:
        object_type = self.edit_gui_dialog.buttonTypeCombo.currentText()
        # check for each value
        button.set_type_str (object_type)
        
        size = [0,0]
        size[0] = self.edit_gui_dialog.buttonSizeXBox.value()
        if object_type == "Circle":
            size[1] = size[0]
        else:
            size[1] = self.edit_gui_dialog.buttonSizeYBox.value()
        
        value = self.edit_gui_dialog.valueBox.value()
        # Num states must be a sensible number 2 to 100
        # The dialog should only allow that anyway
        if value >= 0 and value <= 100:
            button.click_value = value
            
        # Get the colours
        # Get the button's current palette
        current_palette = self.edit_gui_dialog.colorUnknownButton.palette()
        # Get the color for the button role
        button_color = current_palette.color(QPalette.Button)
        # Convert the QColor object to a hex string
        button.button_colors[0] = button_color.name()
        # On button
        current_palette = self.edit_gui_dialog.colorOnButton.palette()
        # Get the color for the button role
        button_color = current_palette.color(QPalette.Button)
        # Convert the QColor object to a hex string
        button.button_colors[1] = button_color.name()
        # Off button
        current_palette = self.edit_gui_dialog.colorOffButton.palette()
        # Get the color for the button role
        button_color = current_palette.color(QPalette.Button)
        # Convert the QColor object to a hex string
        button.button_colors[2] = button_color.name()


## Setup Dialog for appropriate object type
def edit_dialog_guiobject (self, loader, filepath):
    """ Setup dialog for add / edit GUI object  (device)
    """
    # Current object - for easy ref
    gui_obj = self.selected_node
    # Load the dialog
    self.edit_gui_dialog = loader.load(filepath, self)
    #print (f"Dialog {self.edit_gui_dialog} - {self.edit_gui_dialog.findChildren(QLineEdit)}")
    self.edit_gui_dialog.devNameEdit.setText (gui_obj.name)	# On other dialogs this is devNameText (cannot edit)
    # devTypeCombo is a combo box
    # Set text to current value will set selection default - use True to capitalize
    self.edit_gui_dialog.devTypeCombo.setCurrentText(gui_obj.get_type_str(True))
    self.edit_gui_dialog.numStatesBox.setValue(gui_obj.num_states)
    result = self.edit_gui_dialog.exec()
    
    if result == QDialog.Accepted:
        # check for each value
        gui_obj.set_name (self.edit_gui_dialog.devNameEdit.text())
        gui_obj.set_type_str ( self.edit_gui_dialog.devTypeCombo.currentText() )
        num_states = self.edit_gui_dialog.numStatesBox.value()
        # Num states must be a sensible number 2 to 100
        # The dialog should only allow that anyway
        if num_states > 1 and num_states <= 100:
            gui_obj.num_states = num_states



# If the button type combobox changes then change the visibility of the Y selector
def button_type_change (self):
    if self.edit_gui_dialog.buttonTypeCombo.currentText() == "Circle":
        self.edit_gui_dialog.buttonSizeYBox.hide()
    else:
        self.edit_gui_dialog.buttonSizeYBox.show()

    
# Only single colour for label so call directly
# Still use same generic set_button_color to  update the color
def color_picker_label (self):
    button = self.edit_gui_dialog.colorButton
    current_color = button.palette().color(QPalette.Button)
    #print (f"Current color {current_color}")
    # Open the color picker dialog and wait for user selection
    # Pass the current button color as the initial color
    #color = QColorDialog.getColor(current_color, self.edit_gui_dialog)
    # Using enhanced color picker (possible bug with the above simplified method)
    # possible bug in hsv val setting - so set manually to 255
    # dont know why bug here but not in the other color pickers
    hue, sat, val, alpha = current_color.getHsvF()
    current_color.setHsvF(hue, sat, 1, alpha)
    color_dialog = QColorDialog(current_color, self.edit_gui_dialog)
    #color_dialog.setOptions(QColorDialog.ShowAlphaChannel)
    if color_dialog.exec() == QDialog.Accepted:
        color = color_dialog.selectedColor()
        # Check if a valid color was selected (the user didn't cancel)
        if color.isValid():
            # Update the button's palette with the new color
            self.set_button_color(button, color)


def color_picker_dialog(self, button_type):
    if button_type == "on":
        button = self.edit_gui_dialog.colorOnButton
    elif button_type == "off":
        button = self.edit_gui_dialog.colorOffButton
    else:
        button = self.edit_gui_dialog.colorUnknownButton
    # Get the current color of the button to use as the initial color
    current_color = button.palette().color(QPalette.Button)
    
    # Open the color picker dialog and wait for user selection
    # Pass the current button color as the initial color
    color = QColorDialog.getColor(current_color, self.edit_gui_dialog)
    
    # Check if a valid color was selected (the user didn't cancel)
    if color.isValid():
        # Update the button's palette with the new color
        self.set_button_color(button, color)

def set_button_color(self, button, color):
    # Get the button's current palette
    palette = button.palette()
    
    # Set the button background color
    palette.setColor(QPalette.Button, color)
    
    # If the background is dark, set the text color to white for contrast
    if color.lightnessF() < 0.5:
        palette.setColor(QPalette.ButtonText, QColor("white"))
    else:
        palette.setColor(QPalette.ButtonText, QColor("black"))
        
    # Apply the updated palette to the button
    button.setPalette(palette)
    # Ensure the background auto-fills to show the palette change
    button.setAutoFillBackground(True)

def edit_dialog_layoutlabel (self, loader, filepath):
    """ Add / edit Layout Labels
    """
    # Current object - for easy ref
    label = self.selected_node
    gui_obj = label.parent
    # Load the dialog
    self.edit_gui_dialog = loader.load(filepath, self)
    self.edit_gui_dialog.devNameText.setText (gui_obj.name)
    self.edit_gui_dialog.labelNameText.setText (label.get_long_name())
    # buttonTypeCombo is a combo box
    # Set text to current value will set selection default - use True to capitalize
    self.edit_gui_dialog.clickTypeCombo.setCurrentText(label.get_type_str(True))
    ## Set size
    self.edit_gui_dialog.labelClickValueBox.setValue(label.get_click_value())
    # Set font
    self.edit_gui_dialog.fontCombo.setCurrentText(label.font)
    self.edit_gui_dialog.fontSizeBox.setValue(label.min_font_size)
    # Set color
    color_palette = self.edit_gui_dialog.colorButton.palette()
    color_palette.setColor(QPalette.Button, QColor(label.font_color))
    self.edit_gui_dialog.colorButton.setPalette(color_palette)
    self.edit_gui_dialog.colorButton.setAutoFillBackground(True)

    # Listener for the color picker
    self.edit_gui_dialog.colorButton.clicked.connect(self.color_picker_label)
    
    result = self.edit_gui_dialog.exec()
    
    if result == QDialog.Accepted:
        click_type = self.edit_gui_dialog.clickTypeCombo.currentText()
        # check for each value
        label.set_type_str (click_type)
        
        label.click_value = self.edit_gui_dialog.labelClickValueBox.value()
        
        # If set through here then max is 3 x min_font_size
        # Could set outside of this
        label.min_font_size = self.edit_gui_dialog.fontSizeBox.value()
        label.max_font_size = 3 * label.min_font_size
        
        # Do not use the Qfont object directly, instead get the font family name
        label.font = self.edit_gui_dialog.fontCombo.currentFont().family()
            
        # Get the colour
        # Get the button current palette
        current_palette = self.edit_gui_dialog.colorButton.palette()
        # Get the color for the button role
        button_color = current_palette.color(QPalette.Button)
        # Convert the QColor object to a hex string
        label.font_color = button_color.name()

# Scale the image
# If min_size is specified then that is used instead of the QLabel Size
def scale_image_to_fit(self, min_size=None):
    if self.loco_image == None:
        return

    # Get the current size of the QLabel where the image will be displayed
    image_size = self.ui.locoImage.size()
    
    # compare against min_size and if neccessary replace image_size
    if (min_size != None):
        if (image_size.width() < min_size.width() or
            image_size.height() < min_size.height()):
            image_size = min_size

    # Scale the original pixmap to fit the label's dimensions.
    # Qt.KeepAspectRatio ensures the image ratio isn't distorted.
    # Qt.SmoothTransformation uses a high-quality scaling algorithm.
    scaled_pixmap = self.loco_image.scaled(
        image_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    # Set the newly scaled pixmap to the QLabel
    self.ui.locoImage.setPixmap(scaled_pixmap)


# These are also in mainwindow but included here if required
def color_picker_unknown (self):
    self.color_picker_dialog ("unknown")
    
def color_picker_on (self):
    self.color_picker_dialog ("on")
    
def color_picker_off (self):
    self.color_picker_dialog ("off")