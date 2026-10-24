import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const apiSource = fs.readFileSync(path.join(__dirname, 'src', 'api.js'), 'utf8');
const appSource = fs.readFileSync(path.join(__dirname, 'src', 'App.jsx'), 'utf8');
const workspaceSource = fs.readFileSync(
  path.join(__dirname, 'src', 'components', 'TicketWorkspace.jsx'),
  'utf8'
);
const adminSource = fs.readFileSync(
  path.join(__dirname, 'src', 'components', 'AdminDashboard.jsx'),
  'utf8'
);

// 1. Verify single API base and sessionStorage usage
assert(apiSource.includes("const API_BASE = '/api/v1'"), 'Must use /api/v1 base');
assert(apiSource.includes('sessionStorage.getItem'), 'Must read token from sessionStorage');
assert(apiSource.includes('URL.createObjectURL(blob)'), 'Must create blob URL for authorized images');

// 2. Verify all required API client endpoints exist in src/api.js
const requiredEndpoints = [
  '/auth/login',
  '/auth/me',
  '/institutions/current',
  '/locations',
  '/categories',
  '/departments',
  '/staff?department_id=',
  '/complaints',
  '/image',
  '/assign',
  '/status',
  '/history',
  '/feedback',
  '/dashboard/stats',
  '/analyze',
  '/dashboard/insights',
  '/dashboard/insights/report'
];

for (const ep of requiredEndpoints) {
  assert(apiSource.includes(ep), `Missing endpoint ${ep} in src/api.js`);
}

// 3. Verify Atif v0.2 contract alignment in UI components
assert(
  workspaceSource.includes('key={`${h.kind}-${h.id}`}'),
  'History timeline must use kind + id composite React key'
);
assert(
  appSource.includes('student@demo.edu') && appSource.includes('it.staff@demo.edu'),
  'Login must include seeded demo account helpers'
);
assert(
  appSource.includes('/demo-portal') && appSource.includes('/app?embed=1'),
  'App must support /demo-portal and /app?embed=1'
);
assert(
  workspaceSource.includes('source: {aiResult.source}') &&
    adminSource.includes('source: {report.source}'),
  'AI panels must explicitly display source label (rules / local_model)'
);

// 4. Verify production build output in dist/
const distIndex = path.join(__dirname, 'dist', 'index.html');
const distWireframe = path.join(__dirname, 'dist', 'wireframe.svg');
assert(fs.existsSync(distIndex), 'dist/index.html must exist after npm run build');
assert(fs.existsSync(distWireframe), 'dist/wireframe.svg must exist after npm run build');

console.log(
  'Frontend verification passed: 17 endpoint groups, v0.2 contract alignment, and production dist/ bundle verified.'
);
