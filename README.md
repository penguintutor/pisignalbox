# Pi SignalBox 
VLCB / CBUS implementation in Python

This is currently in development. The class and method names and arguments are all subject to change.

The application is client server based using a Python GUI code / VLCB library.

This will provide a way to send messages to / from VLCB / CBUS using a CANUSB4.

For more details about VLCB / CBUS see: [PenguinTutor MERG page](https://www.penguintutor.com/projects/merg) 

## Install

The GUI requires PySide6.

To install on Raspberry Pi OS Trixie (or later)
sudo apt install python3-pyside6.qtgui python3-pyside6.qtwidgets python3-pyside6.qtuitools  

First update the Raspberry Pi using:

    sudo apt update
    sudo apt install python3-venv python3-pip


To setup using virtual environment:

    mkdir ~/venv
    python3 -m venv ~/venv/pyvlcb --system-site-packages
    source ~/venv/pyvlcb/bin/activate
    pip install strip_tags
    pip install flask
    pip install flask.wtf
    pip install pyserial


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

Start the server using

    source ~/.venv/pyvlcb/bin/activate
    python3 vlcbserver.py


After starting the server then from another terminal session run 

    python3 app.py 


# Tests

Unittest is used to provide testing of some of the backend classes. This is not exhaustive.
There is no testing of the GUI components beyond testing of the use of Signals and Slots.

To run the tests change to the tests directory and run 

    python3 run_tests.py


# Features / limitations

All requests are sent to a message queue, so there may be a short delay in them being actioned. This should not be noticeable
unless there are a lot of updates in progress.

For loco control the dial shows the desired speed, the LCD display shows the value provided in the last update
