# Pi SignalBox 
VLCB / CBUS implementation in Python

This is currently in development. The class and method names and arguments are all subject to change.

The application is client server based using a Python GUI code / VLCB library.

This will provide a way to send messages to / from VLCB / CBUS using a CANUSB4.

For more details about VLCB / CBUS see: [PenguinTutor MERG page](https://www.penguintutor.com/projects/merg) 

## Install

The GUI requires PySide6.

To install on Raspberry Pi OS Trixie (or later)

Install PySide6 using:

    sudo apt update
    sudo apt install python3-pyside6.qtgui python3-pyside6.qtwidgets python3-pyside6.qtuitools  


Additional libraries are required to install using virtual environment (recommended):

    mkdir -p ~/venv
    python3 -m venv ~/venv/pisignalbox --system-site-packages
    source ~/venv/pisignalbox/bin/activate
    pip install pyvlcb
    pip install strip_tags
    pip install flask
    pip install flask_login
    pip install flask.wtf
    pip install json5
    pip install pyserial

Note if you would like to use a different virtual environment directory then you may need to create your own startup scripts replacing pisignalbox.sh and/or start_server.sh with your virtual environment. This is not required if using the ~/venv/pisignalbox directory. 

Then clone this repository onto your computer. You can use the GitHub download or to be able to get the latest update then use:

    git clone https://github.com/penguintutor/pisignalbox.git ~/pisignalbox

### Adding API-Key

For security reasons you must add a secure API key to both the
server and client. This needs to be identical.

For the client add it to guiclient/data/settings.json
If the file doesn't exist already the file should have:

```json
{
	"server": {
		"api_key": "INSERT LONG API KEY HERE - random string"
	}
}
```

For the server it should be stored in vlcbserver/server.json

```json
{
    // Set the API key
    "api_key": "INSERT LONG API KEY HERE - random string"
}
```

Note the server includes comments, but they are not allowed in the guiclient file. Also note the lack of "server" top level in the 
server.json file. 


# Upgrade September 2026

Another major refactoring has moved the file structure. If you
are upgrading from an older version move the files in your data folder to guiclient/data/

For security reasons the server now needs an api_key which must 
match the client. At the moment this must be manually edited, but
in future this will be added to the GUI config.


# Upgrade July 2026

Due to a major refactoring and node name change any layout files before July 2026 will need to be updated. To update, first checkout one of the refactor git commits (eg. main 7420e97). Then run the application choose Tools -> Layout Edit, and then click on the cross to close out of Layout Edit mode. You can then move to a a newer version.

This will be deprecated in future. 

Note: There may be other data upgrades needed in future whilst the code is still under development. 


# Development

If you would like to be involved in the development then you will likely want to download the submodule when cloning the repository. Use:

    git clone --recurse-submodules git@github.com:penguintutor/pisignalbox.git

Then activate the venv before running the following from the pisignalbox directory

    pip install -e lib/pyvlcb

If you would like to update the pyvlcb library then change to that directory 

    cd lib/pyvlcb

and then checkout the main branch

    git checkout main

# Running

Start the application using

    ./pisignalbox.sh

This will start the server (if local and not already running) and the GUI application.

To start just the server use

    ./start_server.sh

# Running Automatically

To run the program automatically run the script

    setup/install_services.sh
    sudo systemctl enable pisignalbox.service

### Disabling autostart

To disable the GUI application from starting automatically 

    rm ~/.config/autostart/pisignalbox-gui.desktop

To disable the server from starting automatically

    sudo systemctl stop pisignalbox.service
    sudo systemctl disable pisignalbox.service
    sudo rm /etc/systemd/system/pisignalbox.service
    sudo systemctl daemon-reload



# Tests

Unittest is used to provide testing of some of the backend classes. This is not exhaustive.
There is no testing of the GUI components beyond testing of the use of Signals and Slots.

To run the tests change to the tests directory and run 

    python3 run_tests.py


# Features / limitations

All requests are sent to a message queue, so there may be a short delay in them being actioned. This should not be noticeable
unless there are a lot of updates in progress.

For loco control the dial shows the desired speed, the LCD display shows the value provided in the last update
