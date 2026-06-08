# ScoutKE

ScoutKE is a Kenyan football community scouting network. Fans, players, scouts, and clubs can share football content, submit structured talent spots, verify prospects, write scout reports, and move promising leads into club shortlists.

## Core Flows

- Football Feed: public football-only social feed.
- Talent Spots: structured community sightings of promising players.
- Player Claims: players can claim spots and scouts/admins can link them to profiles.
- Scout Reports: scouts rate and recommend prospects.
- Club Shortlist: clubs track prospects through watching, contacted, trial, signed, or rejected.
- Notifications: users receive updates on confirmations, reports, claims, and shortlist activity.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`.
