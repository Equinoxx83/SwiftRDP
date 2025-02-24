<div style="display: flex; justify-content: space-between;">
  <img src="src/presentation1.png" alt="Texte alternatif" width="45%" height="45%">
  <img src="src/Presentation2.png" alt="Texte alternatif" width="45%" height="45%">
  </div>

# FastRDP – User Manual

FastRDP is a Remote Desktop (RDP) connection manager developed in Python with a Tkinter graphical interface. It allows you to manage your RDP connections (add, modify, delete, etc.) via a user-friendly interface, save or import/export your configurations, and even automatically check for updates from a Git repository.

## Prerequisites

The FastRDP installation script automatically checks for and installs the required dependencies via **apt**.

## Installation

### Installing via the .deb Package

FastRDP is distributed as a **.deb** package. To install FastRDP and automatically resolve dependencies, run:

```bash
sudo apt install ./fastrdp.deb
```

Once installed, FastRDP resides in the /opt/FastRDP directory, and a shortcut is created in the application menu.

Usage
Launching FastRDP
FastRDP is accessible from the application menu. Simply launch the FastRDP application from your desktop environment.

Main Interface
The main interface of FastRDP includes:

Search Field
Filter connections by any field (Name, IP, Login, Group, etc.).

Connections Table
Displays a list of saved connections with the following columns:

Name
IP
Login
Last Connection
Note
Group
Command Buttons

Connect: Initiates an RDP connection to the selected entry (after entering your password).
Add: Opens a window to add a new connection. You can also input a note using the integrated button.
Edit: Allows you to modify the details of the selected connection.
Delete: Removes the selected connection (after confirmation).
Manage Groups: Enables you to add or delete groups. Deleting a group clears the group field for all connections that use it.
Options: Provides access to configuration functions (backup, export, import, delete configuration, update FastRDP, and support).
Establishing an RDP Connection
Select a connection from the table (use the search field if necessary).
Click on Connect or double-click the row (outside the Note column) to start the connection.
Enter your password in the prompted window.
A progress window will appear while the connection is being established.
If the connection is successful, the "Last Connection" date in the table will be updated.
If the connection fails, an error message will be displayed.
Viewing Full Notes
Notes in the table are truncated to maintain a clean layout. To view the complete note:

Double-click the cell in the Note column of the desired connection.
A new window will open displaying the full content of the note.
Configuration Options
Within the Options menu, you can access the following features:

Backup Configuration
Choose a destination folder. FastRDP will create a ZIP archive containing all configuration files.

Export Configuration
Creates a ZIP archive in a folder of your choice.

Import Configuration
Select a ZIP archive to import a previously saved configuration.

Delete Configuration
Removes all connections and/or groups (after confirmation).

Update FastRDP
Checks for a new version. If an update is available, FastRDP will download it and automatically restart. During startup, this check is performed in the background without a popup if no update is found.

Support
Opens the issue tracking page on GitLab.

Automatic Updates
At startup, FastRDP silently checks in the background for a new version:

If an update is detected and you confirm it through the Options menu, the application will update and restart automatically.
If no update is available at startup, no popup is displayed.
