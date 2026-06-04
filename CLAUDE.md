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

Tests (require the Docker DB to be up): `pip install -r requirements-dev.txt && python -m pytest tests/`. The suite smoke-tests every route type, the legacy-URL redirects, and 404 behavior.

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
2. Edition browsing: `/edition/<slug>/` + `/edition/<slug>/text_<ID>/`, driven by the `EDITIONS` dict in `app.py` (slug → `meta.edition` match substring + page labels) and rendered by `edition.html` / `edition_text.html`. The pre-2026 per-edition URLs (`/zel_tet/`, `/zel_tet_text_<ID>/`, etc.) 301-redirect to the new scheme — keep those redirects, the old URLs are indexed and cited
3. Static pages: about, bibliography, contributors

**Templates:** `base.html` is the shared shell; `comparison.html` + the diff highlighter in `main.js` implement side-by-side variant comparison. Frontend stack is Bootstrap 4 + jQuery (vendored via npm into `node_modules`, untracked).

## Current modernization effort (2026)

The project is being updated in phases; Phases 0–2 are done:
- **Phase 0–1:** slim requirements, env-var DB config, single shared Mongo client, no `debug=True`/error-leaking handlers
- **Phase 2:** edition routes/templates consolidated (see above); `abort(404)` on unknown IDs; `Shvarts` collection-prefix filter enforced everywhere; tolerant `date_written` parsing (`written_year()`); `app.py` normalized to 4-space indents; pytest route suite; base.html fixed (viewport meta, `lang="ru"`, merged duplicate `class` attributes, removed dead bootstrap `<link>`)

Pending:
- **Phase 3:** UI redesign with accessibility; merge the three overlapping stylesheets (`style.css`, `main.css`, `style-sasha.css`, ~1,900 lines with 27+ `!important`); dedupe `main.js` (the same decade-render function is pasted five times); add aria/alt throughout
- **Phase 4:** deploy — blocked on recovering SSH/console access to the droplet, whose mongod is down (production DB pages currently 500)

## Gotchas

- Old MongoDB credentials are burned into git history; rotate before ever re-exposing Mongo publicly.
- Poem text rendering relies on `<pre>`/preserved whitespace; line breaks are semantically significant (it's poetry).
