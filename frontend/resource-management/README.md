# Gates, Staff & Resource Management

Owner: Suvanikhaa Sree  
Project: Airport Operations Coordination Engine  
Stack: HTML + CSS + JavaScript

## Run
Open `index.html` in a browser, or run it via VS Code Live Server. No npm install or build step is needed.

## Files
- `index.html` — dashboard structure and accessible controls.
- `styles.css` — responsive dark navy aviation theme.
- `app.js` — illustrative gate/staff records, filters, demo edit/assignment dialogs, shift view and CSV export.

## Demo behaviour
Gate status changes, staff edits and new staff records update the in-memory sample data in the current browser session. Refreshing the page resets demo changes. CSV export downloads the sample records. This module is not connected to a backend and must not be treated as a live airport operating tool.

## Integration notes
Keep API access out of this UI until the backend endpoint shapes, authentication, loading states and error behaviour are agreed with the project team. Replace the sample records in `app.js` with the approved API data layer at integration time.
