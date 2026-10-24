# CampusResolve AI — Figma Wireframe & UI Specification

Owner: Sonia (`@sonia449-prog`)  
Branch: `feature/frontend`  
Stack: React + Plain JavaScript (`.jsx`) + Plain CSS (`.css`), Vite dev proxy to `/api/v1`

---

## 1. Visual Architecture & Layout Modes

- **Standard App (`/app` or `/`)**: Full header with Institution badge, active user role/department pill, role-aware navigation tabs, and logout button.
- **Embedded Mode (`/app?embed=1`)**: Compact header for iframe embedding inside `/demo-portal`; identical API authentication, permissions, and database state.
- **Fictional College Portal (`/demo-portal`)**: Clearly labeled prototype host page embedding `/app?embed=1` in a same-origin `<iframe>`.

```
+-----------------------------------------------------------------------------------+
| CampusResolve AI | [Institution Badge]       [Role: STUDENT/STAFF/COORDINATOR/ADMIN] |
|-----------------------------------------------------------------------------------|
| Navigation Tabs:                                                                  |
|  - Report Issue (STUDENT, STAFF)                                                  |
|  - My Complaints (STUDENT, STAFF)                                                 |
|  - Department Queue (STAFF)                                                       |
|  - Admin Dashboard: [Inbox & Triage] [Analytics] [AI Insights] [Config (ADMIN)]   |
+-----------------------------------------------------------------------------------+
| Main Workspace                                                                    |
| +-----------------------------------+ +-----------------------------------------+ |
| | Left / Primary Column             | | Right / Detail & Triage Drawer          | |
| | - Filters (Status, Category)      | | - Ticket Header (CMP-000042, Priority)  | |
| | - Ticket Cards / Issue Form       | | - Description, Location, Auth Image     | |
| | - Status & Priority Pills         | | - Reporter Edit (while SUBMITTED)       | |
| | - Empty / Loading / Error Banner  | | - Image Upload & Retry (<= 5 MiB)       | |
| |                                   | | - AI Triage Panel (ADMIN/COORDINATOR)   | |
| |                                   | |   [source: rules | needs_review]        | |
| |                                   | | - Department & Staff Assignment         | |
| |                                   | | - Status Transition + Outcome Note      | |
| |                                   | | - Chronological Audit History Timeline  | |
| |                                   | | - Reporter Feedback (1-5 Stars, CRUD)   | |
| +-----------------------------------+ +-----------------------------------------+ |
+-----------------------------------------------------------------------------------+
```

---

## 2. Screen-by-Screen Wireframe Notes

### A. Login Screen
- Email + Password form (`POST /api/v1/auth/login`).
- Stores `access_token` and verified `user` in `sessionStorage` (prototype same-origin token storage).
- Quick-fill helper buttons for local demo accounts (Student, Staff, Coordinator, Admin) that populate email/password fields for fast live demonstration while still authenticating against the real FastAPI + PostgreSQL backend.

### B. Report Issue & Image Attachment (`STUDENT`, `STAFF`)
- Fields: `title` (1–160 chars), `category_id` (optional; nullable routes to admin review), `location` (selectable from `GET /api/v1/locations` canonical campus locations or custom input), `description` (1–5000 chars), optional JPEG/PNG image (`<= 5 MiB`).
- Two-step submission per contract:
  1. `POST /api/v1/complaints` creates the persisted PostgreSQL ticket and returns `ticket_number`.
  2. If an image is selected, `POST /api/v1/complaints/{id}/image` uploads multipart field `file`.
  3. If image upload fails, the created ticket remains saved and opens with an explicit **Retry Image Upload** banner.

### C. My Complaints & Ticket Detail Timeline (`STUDENT`, `STAFF`)
- Lists reporter's own tickets (`GET /api/v1/complaints?mine=true`).
- Detail view loads `GET /api/v1/complaints/{id}`, `GET /api/v1/complaints/{id}/history`, authenticated `GET /api/v1/complaints/{id}/image` (rendered via `URL.createObjectURL`), and `GET /api/v1/complaints/{id}/feedback` when `RESOLVED`.
- While `SUBMITTED`, reporter can edit `title`, `description`, `location`, `category_id` (`PATCH /api/v1/complaints/{id}`) and upload/replace image.
- Once `RESOLVED`, original reporter can create (`POST`), update (`PATCH`), or delete (`DELETE`) their 1–5 star rating and comment.

### D. Staff Department Queue (`STAFF`)
- Separate tab from staff's own personal reports (`GET /api/v1/complaints` filtered to departmental visibility).
- Shows tickets assigned to the staff member's department (`assigned_department_id === user.department_id`) where `assigned_user_id` is `null` or `user.id`.
- Allows status transitions (`SUBMITTED -> IN_PROGRESS | REJECTED`, `IN_PROGRESS -> RESOLVED | REJECTED`) with required verification and outcome note.

### E. Single Admin Dashboard (`ADMIN`, `COORDINATOR`)
1. **Operational Inbox & Per-Ticket AI Assistance**:
   - Institution-wide complaint list with `status` and `category_id` filters.
   - Per-ticket **AI Triage Assistance** (`POST /api/v1/complaints/{id}/analyze`): shows `source` (`rules` or `local_model`), `needs_review`, `summary`, `reason`, suggested `category_id`, `suggested_department_id`, `priority`, and `suggested_actions`. Never mutates ticket state automatically; provides human-confirmed action buttons to apply category/priority or pre-fill assignment.
   - Assignment panel (`PATCH /api/v1/complaints/{id}/assign`): selects active department and loads active departmental staff from `GET /api/v1/staff?department_id=...`.
   - Admin soft archive (`DELETE /api/v1/complaints/{id}`, `ADMIN` only).
2. **Resolution Analytics (`GET /api/v1/dashboard/stats`)**:
   - Cards for `total`, `submitted`, `in_progress`, `resolved`, `rejected`, `resolved_count`, and `avg_resolution_hours` (`null` rendered honestly as `"N/A (0 resolved)"`).
   - Category distribution chart (`by_category`).
3. **AI Insights (Optional Tab)**:
   - UTC `from` and `to` date controls (`GET /api/v1/dashboard/insights?from=...&to=...`).
   - Separate panels for **Frequent Categories**, **Location Hotspots**, and **Urgent / Oldest Unresolved Backlog**.
   - On-demand **Generate Recommendations Report** (`POST /api/v1/dashboard/insights/report` with `{ from, to }`), displaying `source` (`rules`/`local_model`), `sample_size`, `generated_at`, `summary`, and `recommendations` with `IMMEDIATE` / `ASSESSMENT` horizons.
4. **Configuration (`ADMIN` only)**:
   - Manage Categories (`GET/POST/PATCH/DELETE /api/v1/categories`) and Departments (`GET/POST/PATCH/DELETE /api/v1/departments`).
