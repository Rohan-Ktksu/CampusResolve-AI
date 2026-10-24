# CampusResolve AI — Frontend (`feature/frontend`)

Owner: Sonia (`@sonia449-prog`)  
Stack: React 18 + Plain JavaScript (`.jsx`) + Plain CSS (`.css`), Vite build & dev proxy to `/api/v1`.

## Local Setup & Commands (Windows PowerShell)

```powershell
cd frontend
npm install
npm run build
npm run dev
```

- Development server runs at `http://127.0.0.1:5173` and proxies `/api` to `BACKEND_URL` (default `http://127.0.0.1:8000`).
- Standalone application: `http://127.0.0.1:5173/app` (or `/`)
- Embedded portal view: `http://127.0.0.1:5173/app?embed=1`
- Fictional college portal demo wrapper: `http://127.0.0.1:5173/demo-portal`
- Figma wireframe specification: `frontend/FIGMA_WIREFRAME.md` and `/wireframe.svg`
