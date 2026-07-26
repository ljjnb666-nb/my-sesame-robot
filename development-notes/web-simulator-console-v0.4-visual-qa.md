# Web Simulator Console v0.4 Visual QA

## Completed Checks

- 1440x900 desktop dashboard
- 1280x800 laptop dashboard
- 1024x768 tablet dashboard
- 390x844 mobile layout
- Confirmation dialog state
- Confirmation submitting state
- Offline API state
- Blocked non-simulator backend state
- Fault state

## Acceptance Notes

- Layout follows the dark local robotics lab design.
- Typography uses system sans-serif plus monospace values.
- Controls avoid browser default styling.
- Confirmation dialog uses warning color and stays visually distinct from reset confirmation.
- Timeline text wraps inside event rows.
- Mobile order is Header, Robot Overview, Chat, Simulator Controls, Timeline.
- No horizontal overflow was detected by Playwright at 390px.
- No horizontal overflow was detected by Playwright at 1024px or 1280px.
- Submitting confirmation state disables Cancel, Confirm, Enter, and Escape and shows the Runtime wait message.
- Offline and blocked states visibly disable command controls and show reconnect affordance.

## Screenshots

- `web-console/frontend/test-results/desktop-dashboard.png`
- `web-console/frontend/test-results/confirmation-dialog.png`
- `web-console/frontend/test-results/confirmation-submitting.png`
- `web-console/frontend/test-results/fault-state.png`
- `web-console/frontend/test-results/mobile-dashboard.png`
- `web-console/frontend/test-results/laptop-1280-dashboard.png`
- `web-console/frontend/test-results/tablet-1024-dashboard.png`
- `web-console/frontend/test-results/offline-state.png`
- `web-console/frontend/test-results/blocked-state.png`

## Remaining Deviation

The generated concept used a more detailed blueprint robot drawing. The implementation intentionally uses a simpler code-native SVG schematic so the app remains lightweight and does not ship a static screenshot as UI.
