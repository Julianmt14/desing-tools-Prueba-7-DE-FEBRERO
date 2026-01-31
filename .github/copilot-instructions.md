# Copilot Instructions

## Architecture & Data Flow
- Monorepo with `frontend/` (React 18 + Vite) and `backend/` (FastAPI) described in README/ INSTALL.
- `frontend/src/App.jsx` wires routing + theme; auth is simulated by storing a token string in `localStorage`, so any page that requires auth should read/update that key.
- `backend/main.py` exposes placeholder CRUD/auth endpoints with in-memory responses; schema classes (`User`, `Design`) define the contract the UI mocks today.
- Data currently flows via hardcoded arrays (e.g., dashboards, forms) until real API wiring replaces the placeholders.

## Frontend Conventions
- Material UI drives layout and theming; gradients + rounded corners are defined through the `ThemeProvider` in `App.jsx` and per-component `sx` props.
- Navigation lives inside `components/Layout.js`; menu entries are arrays of `{text, icon, path}` and render as `<Button href>` rather than `Link`, so SPA navigation currently reloads—stay consistent unless you refactor both Layout and Router simultaneously.
- Dashboard (`pages/Dashboard.js`) mixes Tailwind-like utility classes, Material Symbols, and inline `<style jsx>` blocks; reuse the same imports/embeds whenever you add icons or custom utilities.
- Forms (`pages/Login.js`, `pages/Register.js`) standardize on `react-hook-form` + `zod` + `@hookform/resolvers`, adorn each `TextField` with MUI icons, and surface feedback via `react-hot-toast`; copy that pattern for any new auth/profile screens.
- Route-level pages should be declared in `src/pages/`, imported into `App.jsx`, and linked through `Layout` if they need presence in the main menu.

## Backend Conventions
- FastAPI app is bootstrapped directly in `backend/main.py`; `OAuth2PasswordBearer` uses `/token`, but the handler returns a simulated token string—wire real JWT issuance before trusting it.
- Models share naming with frontend fields (`username`, `design_type`, `settings` dict), so update both sides together to avoid drift.
- CORS is hardcoded to `http://localhost:3000`; adjust `allow_origins` plus `.env` when changing Vite ports or deploying.
- Run locally via `python main.py` (uvicorn reload enabled); dependencies are pinned in `backend/requirements.txt`.

## Developer Workflows
- Backend: `cd backend && python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt && python main.py` per README/INSTALL.
- Frontend: `cd frontend && npm install && npm run dev`; Vite is configured in `vite.config.js` to serve on port `3001` and proxy `/api` calls to `http://localhost:8001` (update README or the proxy before exposing new endpoints).
- Build artifacts emit to `frontend/build` via `npm run build`; lint via `npm run lint` (ESLint with CRA presets).
- Windows users can launch both tiers with the optional `run.bat` described in INSTALL.

## Integration Notes
- When wiring Axios, prefer `/api/...` paths to reuse the Vite proxy; direct `http://localhost` URLs will bypass that configuration and may reintroduce CORS issues.
- Persisted auth hinges on the `access_token` key; `Layout` receives `onLogout` to clear it, so any new logout flows should delegate to that handler.
- UI copy is fully localized in Spanish—maintain tone/wording when adding components.
- Dashboard imagery comes from external Google-hosted URLs; replace with local assets if offline resilience matters.
