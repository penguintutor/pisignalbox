# Data Files for Pi Signal Box

## Default locations
By default all files are relative to the data directory
This is normally basedir/data/

It can be overwritten using command line argument -d or --datadir.

## Data directory structure
These are relative to the data directory (eg. basedir/data/)
- locos (loco files and images)
- layouts (layout files and images)
- rules (rules for handling events)
- automation (automation instructions)


## Settings (settings.json)
Provides settings, including loading the current layout and details from previous run
This is stored in the data directory named settings.json

It is loaded from the MainWindows - using the class Settings
If it doesn't exist then default values are used instead. A warning is issued to the command line (not in the GUI).

### Setting entries
enabledlocos = list of loco filenames (stored in locos directory)
layoutfile = filename of the layout file


## Layouts (layouts.json)
The Layouts file stores all the Layouts that are available. It is not required to run as without it then the layout from the settings will be used. It is required for selecting an appropriate layout.

This is loaded using Layouts class

This is stored in the data directory named layouts.json
If it doesn't exist then an empty file is created when the class is run.

### Layouts entries
These are stored as a dict:
- filename : Layout Name

### Creates Layout file
When a new layout is created, as well as updating the Layouts file, a new file is created in the layouts directory matching the filename. This is based on the layout name but made filename friendly (lowercase and replace space for _ etc.) 


## Layout (defined in settings.json / layouts.json)
The Layout file is named based on the layout (filename friendly filename). Image files needed for the layout are also stored in the same directory
The file is stored in the data/layouts directory.
The current layout is defined in settings and loaded from MainWindow based on the settings.


### Layout file details

- title
- guiobjects (eg. points / labels)
- layoutimage (image file stored in the layouts directory)


## Locos directory
The Locos consist of a .json file based on loco_id, class_id and name or classification
The name is generated from within LocoWindow (# Create a filename loco_id)
Any images are also stored in that directory.

Contains various information about the loco


