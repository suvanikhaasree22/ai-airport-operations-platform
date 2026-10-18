# AI Airport Operations Platform

A modular frontend project for the Airport Operations Coordination Engine.

## Current module

**Gates, Staff & Resource Management** — owned by Suvanikhaa Sree.

Implemented in plain HTML, CSS and JavaScript under `frontend/resource-management/`.

### Features
- Navy-blue aviation operations interface with aircraft/terminal imagery.
- Gate cards with status, terminal, flight/route and schedule details.
- Gate status filters and search.
- Staff availability and allocation table with search and status filter.
- Demo actions to update a gate, add staff and edit/assign staff.
- Staff shift overview and CSV export.
- Responsive sidebar and layouts for desktop, tablet and mobile.
- Clearly labelled illustrative demo data.

## Run locally
1. Clone the repository or download the project files.
2. Open `frontend/resource-management/index.html` in a browser, or open the repository in VS Code and use the Live Server extension.
3. No build step or package installation is required.

## Important data note
This is a **frontend demo**. The current gate and staff records are fictional sample data stored in `app.js`. Form changes stay in the current page session and are not persisted to a database. The project is not connected to live airport systems, backend REST APIs, or real flight operations.

## Team integration
Keep this module in its own folder while the remaining frontend modules are developed. When the common dashboard architecture and backend API contract are agreed, connect these views to the team's shared navigation and REST endpoints. Coordinate changes through Git branches or pull requests once other team members join.

## Ownership
Frontend module: Gates, Staff & Resource Management  
Team member: Suvanikhaa Sree  
Project: Airport Operations Coordination Engine
