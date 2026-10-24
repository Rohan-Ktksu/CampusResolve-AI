-- Idempotent schema; applied on startup. shortcut: no migrations tool, add Alembic once the schema must evolve with real data.
CREATE TABLE IF NOT EXISTS institutions (
  id serial PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
  id serial PRIMARY KEY,
  institution_id int NOT NULL REFERENCES institutions(id),
  name text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  UNIQUE (institution_id, name)
);

CREATE TABLE IF NOT EXISTS categories (
  id serial PRIMARY KEY,
  institution_id int NOT NULL REFERENCES institutions(id),
  name text NOT NULL,
  default_department_id int REFERENCES departments(id),
  is_active boolean NOT NULL DEFAULT true,
  UNIQUE (institution_id, name)
);

CREATE TABLE IF NOT EXISTS locations (
  id serial PRIMARY KEY,
  institution_id int NOT NULL REFERENCES institutions(id),
  name text NOT NULL,
  UNIQUE (institution_id, name)
);

CREATE TABLE IF NOT EXISTS users (
  id serial PRIMARY KEY,
  email text NOT NULL UNIQUE,
  name text NOT NULL,
  password_hash text NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
  id serial PRIMARY KEY,
  user_id int NOT NULL REFERENCES users(id),
  institution_id int NOT NULL REFERENCES institutions(id),
  role text NOT NULL CHECK (role IN ('STUDENT', 'STAFF', 'COORDINATOR', 'ADMIN')),
  department_id int REFERENCES departments(id),
  is_active boolean NOT NULL DEFAULT true,
  UNIQUE (user_id, institution_id)
);

CREATE TABLE IF NOT EXISTS complaints (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ticket_number text GENERATED ALWAYS AS ('CMP-' || lpad(id::text, 6, '0')) STORED UNIQUE,
  institution_id int NOT NULL REFERENCES institutions(id),
  reporter_user_id int NOT NULL REFERENCES users(id),
  title text NOT NULL,
  description text NOT NULL,
  location text NOT NULL,
  category_id int REFERENCES categories(id),
  status text NOT NULL DEFAULT 'SUBMITTED' CHECK (status IN ('SUBMITTED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED')),
  priority text NOT NULL DEFAULT 'NORMAL' CHECK (priority IN ('LOW', 'NORMAL', 'HIGH')),
  assigned_department_id int REFERENCES departments(id),
  assigned_user_id int REFERENCES users(id),
  image_path text,
  image_type text,
  archived boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz
);

CREATE TABLE IF NOT EXISTS complaint_status_history (
  id serial PRIMARY KEY,
  complaint_id bigint NOT NULL REFERENCES complaints(id),
  actor_user_id int NOT NULL REFERENCES users(id),
  old_status text,
  new_status text NOT NULL,
  note text,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS assignments (
  id serial PRIMARY KEY,
  complaint_id bigint NOT NULL REFERENCES complaints(id),
  actor_user_id int NOT NULL REFERENCES users(id),
  department_id int REFERENCES departments(id),
  assigned_user_id int REFERENCES users(id),
  note text,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS feedback (
  id serial PRIMARY KEY,
  complaint_id bigint NOT NULL UNIQUE REFERENCES complaints(id),
  author_user_id int NOT NULL REFERENCES users(id),
  rating int NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment text,
  created_at timestamptz NOT NULL DEFAULT now()
);
