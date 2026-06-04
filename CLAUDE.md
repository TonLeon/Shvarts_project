# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A digital scholarly archive of Elena Shvarts's poetry (Елена Шварц, 1948–2010): a Flask + MongoDB web app for browsing ~1,285 poems chronologically or by published collection, comparing textual variants of the same poem, and full-text search. UI text is Russian. Production lives at https://eshvarts.com/ (DigitalOcean droplet 142.93.242.162, nginx + uWSGI).

## Running locally

The database is a local Docker container that must be started first:

```bash
docker start mongodb          # mongo:4.0.4, port 27017, no auth
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
FLASK_APP=app .venv/bin/flask run
```

Connection is configured by env vars `MONGO_URI` (default `mongodb://localhost:27017`) and `MONGO_DB` (default `admin` — yes, the data really lives in the `admin` database).

There is no test suite or linter yet. Quick smoke test: `curl localhost:5000/list_of_texts/` (DB-backed) and `curl localhost:5000/texts_21/` (single poem).

Backup/restore: `docker exec mongodb mongodump --db admin --archive > backup.archive`. A verified backup from 2026-06-04 exists at `~/Documents/Shvarts_backups/`.

## Architecture

**Data pipeline (one-way):** TEI XML files in `static/data/` (one per poem, with `teiHeader` bibliography metadata) → parsed by `Shvarts_MongoDB_main.ipynb` → MongoDB collections. The XML files are the source of truth for corpus changes; the app only reads Mongo.

**MongoDB layout:** poems are split by decade of writing into collections `Shvarts_60`, `Shvarts_70`, `Shvarts_80`, `Shvarts_90`, `Shvarts_20` (=2000s). Nearly every query in `app.py` iterates all `Shvarts*` collections and merges results in Python. Document fields that matter:
- `ID` (int) — app-level key used in all URLs; unique across collections
- `poem_text` — HTML, rendered with `Markup()` (trusted content)
- `genre` — `"cycle"` gets special rendering (whole cycle text on one page)
- `meta.date_written` — int year or a string containing a 4-digit year (parsed by regex)
- `meta.edition` — free-text bibliography string; edition pages match it by **substring** (e.g. `"том 1"`, `"Стихи из"`)
- `root` — variant linkage: `root: []` means canonical text; non-empty `root` marks a duplicate/variant of another poem (the "duplicates" passed to templates power the comparison feature at `/comparison_<ID>/`)

**Routes in `app.py`** come in three groups:
1. Chronological browsing: `/list_of_texts/`, `/texts_<ID>/`, plus JSON endpoints (`/show_all_poems`, `/filter_poems_by_period_*`, `/background_process?search=` for Mongo `$text` search) consumed by jQuery in `static/js/main.js`
2. Edition browsing: six structurally identical route pairs (`/zel_tet/` + `/zel_tet_text_<ID>/`, same for `tanz_david`, `soch_v_1`, `soch_v_3`, `soch_v_5`, `perelet_ptitsa`), each with its own near-duplicate template pair — a change to one usually needs to be applied to all six
3. Static pages: about, bibliography, contributors

**Templates:** `base.html` is the shared shell; `comparison.html` + the diff highlighter in `main.js` implement side-by-side variant comparison. Frontend stack is Bootstrap 4 + jQuery (vendored via npm into `node_modules`, untracked).

## Current modernization effort (2026)

The project is being updated in phases; Phases 0–1 are done (slim requirements, env-var DB config, single shared Mongo client, no `debug=True`/error-leaking handlers). Pending:
- **Phase 2:** consolidate the six edition route/template pairs into one parameterized pair; `abort(404)` on unknown IDs (currently `IndexError` → 500); restore the commented-out `Shvarts` prefix filter in `get_files_by_edition` (a stray `Club 21` collection currently gets scanned); harden `date_written` parsing; normalize mixed tabs/spaces in `app.py`; add route tests; fix base.html correctness bugs (no viewport meta → broken on mobile; `lang="en"` on a Russian site; duplicate `class` attributes so nav styling never applies; bootstrap JS loaded once as a dead `<link>` and once as a script)
- **Phase 3:** UI redesign with accessibility (consolidate first so visual decisions are made once); merge the three overlapping stylesheets (`style.css`, `main.css`, `style-sasha.css`, ~1,900 lines with 27+ `!important`); dedupe `main.js` (the same decade-render function is pasted five times); add aria/alt throughout
- **Phase 4:** deploy — blocked on recovering SSH/console access to the droplet, whose mongod is down (production DB pages currently 500)

## Gotchas

- Old MongoDB credentials are burned into git history; rotate before ever re-exposing Mongo publicly.
- `app.py` mixes tabs and spaces between functions — match the indentation of the function you're editing until Phase 2 normalizes it.
- Poem text rendering relies on `<pre>`/preserved whitespace; line breaks are semantically significant (it's poetry).
