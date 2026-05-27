# ADR 0001: Read-Only Edge Client for Vehicle and Tag Management

## Status
Approved

## Context
The gate automation system runs on edge hardware (such as a Raspberry Pi) and is designed to operate "offline-first". It validates RFID tags against a local SQLite database that is synchronized periodically with a central cloud API.
To prevent offline-online write conflicts and maintain a single source of truth:
* All resource registration (vehicles, tags, drivers) and relationships (associating a tag with a vehicle) must be performed centrally on the cloud platform.
* The edge client must periodically pull these changes down to the local SQLite database.

## Decision
We will not build any creation, editing, or association capability for vehicles and tags in the local Tkinter GUI. The GUI will only contain read-only listing screens (tabs) to view current local state (e.g. which vehicles and tags are currently cached locally and their status). 

## Consequences
* **Simplification**: The local GUI logic remains simple, robust, and lightweight.
* **Consistency**: No conflicts occur when the edge device is offline and attempts to edit/link tags, as there is no local mutation interface.
* **Security**: Changes to gate permissions (approving/disapproving tags) must go through the centralized server API, preventing unauthorized local override on the edge device GUI.
