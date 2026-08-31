# UI Layout Package - as UILayoutMixin
# Included into MainWindow

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
import logging
from pathlib import Path 
from core import event_bus
from common.imageexistdialog import ImageExistDialog
from layout.layoutdialog import LayoutDialog

# As this is a Mixin it will report as this file rather than the file it's imported into
logger = logging.getLogger(__name__)

class UITrackViewMixin:

    def change_layout_dialog (self):
        layout_dialog = LayoutDialog(self, self.data_dir, self.dirs['layouts'], self.files['layouts'], self.settings)
        result = layout_dialog.exec()
        # If not changed then ignore
        if result != 1:
            return    
            
        # Get the new Layout filename
        new_filename = layout_dialog.selected_layout
        self.layout.load_file(new_filename)
        
        self.ui.layoutDisplayLabel.set_layout(self, self.layout)
        # Update the layout display
        # Includes load layout background image
        # and UI objects
        self.ui.layoutDisplayLabel.update()

    def change_layout_image_dialog(self):
        file_dialog = QFileDialog(self,
                        caption="Select Background Image",
                        directory=self.dirs['layouts'],
                        filter="Images (*.png *.jpg *.jpeg *.bmp)",
                        fileMode=QFileDialog.FileMode.ExistingFile
                        )

        # Guard clause: Return immediately if the user cancels
        if not file_dialog.exec():
            return

        selected_file = file_dialog.selectedFiles()[0]
        
        # Delegate the complex file resolution to a helper method
        final_filename = self._resolve_layout_image(selected_file)
        
        # If the helper returns a valid filename, update the railway layout
        if final_filename:
            self.layout.set_layout_image(final_filename)
            self.ui.layoutDisplayLabel.load_image()


    def _resolve_layout_image(self, selected_file: str) -> str | None:
        """
        Handles copying the selected layout image if necessary and resolving conflicts.
        Returns the final filename to be used, or None if the operation was cancelled.
        """
        filename = os.path.basename(selected_file)

        # File is already in the layouts directory
        if self.is_datadir(selected_file, 'layouts'):
            return filename

        new_path = os.path.join(self.dirs['layouts'], filename)

        # File is not in layouts, and no naming conflict exists
        if not os.path.exists(new_path):
            shutil.copyfile(selected_file, new_path)
            return filename

        # Conflict exists: File is not in layouts, but the filename already exists there
        exist_dialog = ImageExistDialog(self, self.dirs['layouts'])
        
        # Guard clause: Return if the user cancels the conflict resolution dialog
        if exist_dialog.exec() != QDialog.Accepted:
            return None

        # Process the specific action chosen in the dialog
        if exist_dialog.action == "overwrite":
            shutil.copyfile(selected_file, new_path)
            return filename
            
        elif exist_dialog.action == "existing":
            return filename
            
        elif exist_dialog.action == "save":
            new_filename = exist_dialog.ui.filenameEdit.text()
            new_path = os.path.join(self.dirs['layouts'], new_filename)
            shutil.copyfile(selected_file, new_path)
            return new_filename

        # Unknown state fallback
        return None


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
            self.layout.save_file()

    def edit_dialog_layoutbutton (self, selected_node):
        """ Dialog for creating and editing Layout Buttons
        """
        # Current object - for easy ref
        button = selected_node
        gui_obj = button.parent
        # Load the dialog
        loader = QUiLoader()
        filepath = Path(__file__).parent /  "editgbuttondialog.ui"
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
    def edit_dialog_trackviewnode (self, selected_node):
        """ Setup dialog for add / edit GUI object  (device)
        """
        # Current object - for easy ref
        gui_obj = selected_node
        # Load the dialog
        loader = QUiLoader()
        filepath = Path(__file__).parent / "editguidialog.ui"
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
        # Previously tried simplified QColorDialog.getColor = possible bug so used enhanced colour picker
        # Still possible bug in hsv val setting - so set manually to 255 (1)
        # dont know why bug here but not in the other color pickers
        hue, sat, val, alpha = current_color.getHsvF()
        logger.debug (f"Colour value HsvF is {hue}, {sat}, {val}, {alpha}")
        current_color.setHsvF(hue, sat, 1, alpha)
        color_dialog = QColorDialog(current_color, self.edit_gui_dialog)
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

    def edit_dialog_layoutlabel (self, selected_node):
        """ Add / edit Layout Labels
        """
        # Current object - for easy ref
        label = selected_node
        gui_obj = label.parent
        # Load the dialog
        loader = QUiLoader()
        filepath = Path(__file__).parent / "editglabeldialog.ui"
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
    # This scales the loco image for display in the MainWindow
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

    # Helper functions, allowing simple filename call which
    # sends appropriate argument to method
    def color_picker_unknown (self):
        self.color_picker_dialog ("unknown")
        
    def color_picker_on (self):
        self.color_picker_dialog ("on")
        
    def color_picker_off (self):
        self.color_picker_dialog ("off")