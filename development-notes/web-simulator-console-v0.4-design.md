# Web Simulator Console v0.4 Design

## Layout

The console uses a local robotics lab layout: sticky header, then a responsive dashboard. Desktop uses three columns: AI Chat, Robot Overview, and Simulator Controls plus Timeline. Tablet collapses to two columns. Mobile order is Header, API Status, Robot Overview, Chat, Confirmation, Simulator Controls, Timeline.

## Color Tokens

- Background: `#0d1114`
- Surface: `#151a1f`
- Raised surface: `#1b2229`
- Border: `#2d3741`
- Text: `#e6edf2`
- Muted text: `#8f9ba7`
- Simulator accent: `#41a7ff`
- Normal: `#46d56b`
- Warning/confirmation: `#f0c84b`
- Fault/danger/emergency: `#ff5a4f`

## Typography

System sans-serif for interface text. Monospace is reserved for runtime values, timestamps, event fields, and status identifiers. Letter spacing remains `0`.

## Spacing And Panels

Panels use 8px radius, restrained borders, and compact 12px internal padding. The UI avoids nested cards; repeated messages and timeline rows are list items.

## Status Semantics

Green means normal, yellow means warning or confirmation, red means emergency/fault/blocked. Color is paired with text labels and icons.

## Interaction States

Offline and blocked health disable Chat, fault injection, and reset controls. Confirmation is a modal dialog with focus trap, Escape cancel, no autofocus on confirm, and no visible confirmation ID.

## Responsive Rules

No horizontal scrolling is allowed. Buttons wrap into columns on mobile. Timeline reason/result text wraps inside event rows.
