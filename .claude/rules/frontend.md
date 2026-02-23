---
paths:
  - "frontend/**/*"
---

# Frontend Conventions

## Stack

Plain HTML + vanilla JS. No build step, no framework, no bundler. Files are served directly by FastAPI via `StaticFiles`.

## Structure

- `frontend/index.html` — single page, two-column layout (chat + trace panel)
- `frontend/app.js` — all JS logic, no modules (loaded via `<script src="/app.js">`)
- `frontend/style.css` — all styles, CSS custom properties for theming

## Key JS patterns

- **Session ID**: generated with `crypto.randomUUID()` on page load; sent with every `/api/chat` request
- **Config display**: `GET /api/config` is fetched on startup to populate the header status line
- **Chat flow**: `POST /api/chat` → render `data.answer` as agent message → call `renderTrace(data)` with the full response
- **Trace panel**: `data.spans` array rendered as collapsible `span-card` elements; `data.token_usage` shown in the footer strip

## Adding UI features

Keep it simple — add to the existing single-file structure. If a new API endpoint returns data that should be visible to users, add rendering in `app.js` and style in `style.css`. Do not introduce a JS framework or build tooling.
