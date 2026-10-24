"""Load synthetic demo complaints through the real API (fictional people and events only).

Usage: python scripts/seed_demo_data.py https://campusresolve-ai-sigma.vercel.app
       python scripts/seed_demo_data.py http://127.0.0.1:5173

Creates ~40 complaints from the seeded demo accounts, with recurring issues (so Common
Issues and the chatbox have something to find), then moves some through the workflow:
in progress, resolved with an outcome note and reporter feedback, or rejected.
It refuses to run twice: if the database already has 20+ complaints it stops.
"""
import sys

import httpx

PASSWORD = 'demo1234'
S = {n: f'student{"" if n == 1 else n}@demo.edu' for n in range(1, 9)}
IT, FAC = 'it.staff@demo.edu', 'facilities.staff@demo.edu'

# (reporter, title, description, location, category, outcome, priority)
# outcome: None (stays Submitted), 'progress', 'resolve', 'reject'
DATA = [
    # Recurring: water leak in Hostel 1
    (S[1], 'Water leak in Hostel 1 washroom', 'Water is leaking from a pipe in the second floor washroom of Hostel 1.', 'Hostel 1', 'Plumbing', 'resolve', None),
    (S[3], 'Water leak near Hostel 1 stairs', 'Constant water leak near the stairs, the floor stays wet and slippery.', 'Hostel 1', 'Plumbing', 'progress', None),
    (S[4], 'Leaking tap in Hostel 1', 'The washroom tap keeps leaking water all night.', 'Hostel 1', 'Plumbing', None, None),
    (S[5], 'Water leak flooding the corridor', 'Water leak has flooded the corridor outside room 204 in Hostel 1.', 'Hostel 1', 'Plumbing', 'progress', 'HIGH'),
    (S[2], 'Water leak again in Hostel 1', 'The water leak in the washroom is back after last week.', 'Hostel 1', 'Plumbing', None, None),
    (S[6], 'Pipe leaking in lab sink', 'Water leak under the sink in Lab 204.', 'Block B / Lab 204', 'Plumbing', 'resolve', None),
    # Recurring: stale food in the cafeteria
    (S[2], 'Stale food at dinner', 'The rice served at dinner was stale food again.', 'Cafeteria', 'Food / Canteen', 'resolve', None),
    (S[3], 'Stale food in canteen', 'Stale food and cold chapati served at lunch.', 'Cafeteria', 'Food / Canteen', 'progress', None),
    (S[7], 'Stale bread at breakfast', 'Breakfast bread was stale food, many students skipped the meal.', 'Cafeteria', 'Food / Canteen', None, None),
    (S[8], 'Canteen snacks overpriced', 'Snacks at the canteen are overpriced compared to the menu board.', 'Cafeteria', 'Food / Canteen', 'reject', None),
    (S[4], 'Stale food served twice this week', 'Stale food was served at lunch on two days this week.', 'Cafeteria', 'Food / Canteen', None, None),
    # Recurring: Wi-Fi drops in the library
    (S[1], 'Wi-Fi keeps dropping in library', 'The wifi connection drops every few minutes in the library reading hall.', 'Library', 'Wi-Fi / Network', 'resolve', None),
    (S[5], 'Library wifi connection drops', 'Wifi connection drops while downloading course material.', 'Library', 'Wi-Fi / Network', 'resolve', None),
    (S[6], 'No internet in library', 'Wifi connection drops and pages do not load in the library.', 'Library', 'Wi-Fi / Network', 'progress', None),
    (S[8], 'Wifi connection drops during exam prep', 'Wifi connection drops near the library windows during exam preparation.', 'Library', 'Wi-Fi / Network', None, 'HIGH'),
    (S[2], 'Lab wifi very slow', 'Internet is very slow in Lab 204 during practicals.', 'Block B / Lab 204', 'Wi-Fi / Network', None, None),
    # Classroom equipment
    (S[3], 'Projector not working in A2', 'Projector in classroom A2 shows no signal.', 'Block A / Classrooms', 'Classroom Equipment', 'resolve', None),
    (S[7], 'Projector flickering', 'The projector in A4 keeps flickering during lectures.', 'Block A / Classrooms', 'Classroom Equipment', 'progress', None),
    (FAC, 'Projector remote missing', 'Projector remote in A1 is missing, staff cannot switch input.', 'Block A / Classrooms', 'Classroom Equipment', None, None),
    # Electrical
    (S[5], 'Sparks from socket in lab', 'Sparks came from a power socket near bench 3 in Lab 204.', 'Block B / Lab 204', 'Electrical', 'resolve', 'HIGH'),
    (S[6], 'Fan not working in hostel room', 'The ceiling fan is not working in room 112.', 'Hostel 1', 'Electrical', None, None),
    # Transport
    (S[4], 'Morning bus late', 'The 8 am bus was 30 minutes late at the main gate.', 'Main Gate / Bus Stop', 'Transport', 'resolve', None),
    (S[7], 'Bus late again', 'Morning bus late for the third day, students miss first class.', 'Main Gate / Bus Stop', 'Transport', 'progress', None),
    (S[8], 'Evening shuttle skipped stop', 'The evening shuttle skipped the main gate stop.', 'Main Gate / Bus Stop', 'Transport', None, None),
    # Cleanliness
    (S[1], 'Overflowing bin near cafeteria', 'Overflowing bin and garbage near the cafeteria entrance.', 'Cafeteria', 'Cleanliness', 'resolve', None),
    (S[3], 'Garbage not collected at hostel', 'Garbage has not been collected outside Hostel 1 for two days.', 'Hostel 1', 'Cleanliness', None, None),
    (S[6], 'Litter near main gate', 'Litter and plastic bottles scattered near the bus stop.', 'Main Gate / Bus Stop', 'Cleanliness', 'resolve', None),
    # Infrastructure
    (S[2], 'Lift not working in admin block', 'The lift in the admin block is not working since morning.', 'Admin Block', 'Infrastructure', 'progress', 'HIGH'),
    (S[5], 'Broken bench in corridor', 'A broken bench in the Block A corridor has a sharp edge.', 'Block A / Classrooms', 'Infrastructure', None, None),
    # Safety / Security
    (S[7], 'Phone stolen in library', 'My phone was stolen from the reading area in the library.', 'Library', 'Safety / Security', 'progress', 'HIGH'),
    (S[8], 'Bag stolen from library desk', 'Bag stolen while I was away from the library desk for five minutes.', 'Library', 'Safety / Security', None, 'HIGH'),
    # Sports
    (S[4], 'Gym treadmill broken', 'The treadmill in the gym is broken and makes a grinding noise.', 'Sports Complex', 'Sports', 'resolve', None),
    (S[6], 'Badminton court net torn', 'The badminton court net is torn in the middle.', 'Sports Complex', 'Sports', None, None),
    # Hostel
    (S[3], 'Room allotment not updated', 'Room allotment list on the hostel board has not been updated.', 'Hostel 1', 'Hostel', 'resolve', None),
    (S[5], 'Warden not responding', 'Warden has not responded to the room allotment request for a week.', 'Hostel 1', 'Hostel', None, None),
    # Housekeeping
    (S[2], 'No toilet paper in washroom', 'No toilet paper or soap in the Block A washroom.', 'Block A / Classrooms', 'Housekeeping', 'resolve', None),
    (S[7], 'Washroom supplies empty', 'Washroom supplies, soap and hand wash are empty in the library.', 'Library', 'Housekeeping', None, None),
    # Academics / Library
    (S[1], 'Timetable clash for 3rd semester', 'Two lectures are scheduled at the same time in the timetable.', 'Admin Block', 'Academics', 'resolve', None),
    (S[8], 'Exam hall seating not posted', 'Exam hall seating list is not posted yet.', 'Admin Block', 'Academics', None, None),
    (S[4], 'Missing library book', 'Library book on data structures is missing from the shelf.', 'Library', 'Library', 'reject', None),
    (IT, 'Staff room wifi down', 'Wifi connection drops in the admin block staff room.', 'Admin Block', 'Wi-Fi / Network', 'resolve', None),
]
NOTES = {'resolve': 'Fixed and checked on site with the reporter (demo data).',
         'reject': 'Not a maintenance issue; forwarded to the right office (demo data).'}


def main(base):
    c = httpx.Client(base_url=base.rstrip('/'), timeout=60)

    def login(email):
        r = c.post('/api/v1/auth/login', json={'email': email, 'password': PASSWORD})
        r.raise_for_status()
        return {'Authorization': 'Bearer ' + r.json()['access_token']}

    admin = login('admin@demo.edu')
    existing = c.get('/api/v1/complaints', headers=admin).json()
    if len(existing) >= 20:
        sys.exit(f'{len(existing)} complaints already exist; not seeding again.')
    cats = {x['name']: x['id'] for x in c.get('/api/v1/categories', headers=admin).json()}
    tokens = {}
    done = {'created': 0, 'resolved': 0, 'in_progress': 0, 'rejected': 0, 'feedback': 0}
    for i, (who, title, desc, loc, cat, outcome, priority) in enumerate(DATA):
        h = tokens.setdefault(who, login(who))
        r = c.post('/api/v1/complaints', headers=h, json={'title': title, 'description': desc, 'location': loc, 'category_id': cats[cat]})
        r.raise_for_status()
        cid = r.json()['id']
        done['created'] += 1
        if priority:
            c.patch(f'/api/v1/complaints/{cid}', headers=admin, json={'priority': priority}).raise_for_status()
        if outcome == 'reject':
            c.patch(f'/api/v1/complaints/{cid}/status', headers=admin, json={'status': 'REJECTED', 'note': NOTES['reject']}).raise_for_status()
            done['rejected'] += 1
        elif outcome in ('progress', 'resolve'):
            c.patch(f'/api/v1/complaints/{cid}/status', headers=admin, json={'status': 'IN_PROGRESS'}).raise_for_status()
            if outcome == 'progress':
                done['in_progress'] += 1
            else:
                c.patch(f'/api/v1/complaints/{cid}/status', headers=admin, json={'status': 'RESOLVED', 'note': NOTES['resolve']}).raise_for_status()
                rating = 3 + i % 3
                c.post(f'/api/v1/complaints/{cid}/feedback', headers=h,
                       json={'rating': rating, 'comment': 'Thanks for the quick fix.' if rating > 3 else 'Fixed, but it took a while.'}).raise_for_status()
                done['resolved'] += 1
                done['feedback'] += 1
    print(done)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5173')
