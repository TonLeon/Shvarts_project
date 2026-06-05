from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from markupsafe import Markup, escape
from urllib.parse import urlencode
import os
import pymongo
import re
import snowballstemmer


app = Flask(__name__)

# Single shared client: MongoClient is thread-safe and pools connections.
# Configure via env vars; defaults match the local Docker setup.
client = pymongo.MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017'))
db = client[os.environ.get('MONGO_DB', 'admin')]


# Printed editions: slug -> substring that identifies the edition in
# meta.edition, plus the labels used on the index and text pages.
EDITIONS = {
    'zel_tet': {
        'match': 'Стихи из',
        'title': 'Стихи из «Зелёной Тетради»',
        'text_title': 'Стихи из «Зелёной тетради»',
        'intro': True,
    },
    'tanz_david': {
        'match': 'Танцующий',
        'title': 'Танцующий Давид',
        'text_title': 'Стихи из сборника «Танцующий Давид»',
    },
    'soch_v_1': {
        'match': 'том 1',
        'title': 'Собрание сочинений, том I',
        'text_title': 'Стихи из I тома Собрания сочинений',
    },
    'soch_v_3': {
        'match': 'том 3',
        'title': 'Собрание сочинений, том III',
        'text_title': 'Стихи из III тома Собрания сочинений',
    },
    'soch_v_5': {
        'match': 'том 5',
        'title': 'Собрание сочинений, том V',
        'text_title': 'Стихи из V тома Собрания сочинений',
    },
    'perelet_ptitsa': {
        'match': 'Перелетная птица',
        'title': 'Перелётная птица',
        'text_title': 'Стихи из сборника «Перелётная птица»',
    },
}


def written_year(date_written):
    """meta.date_written is either an int year or free text containing one;
    extract a sortable year, falling back to 0 for undatable texts."""
    if isinstance(date_written, int):
        return date_written
    match = re.search(r'\d{4}', str(date_written))
    return int(match.group()) if match else 0


def shvarts_collections():
    return [name for name in db.list_collection_names() if name.startswith('Shvarts')]


def get_poems_titles():
    all_titles = []
    all_duplicates = []

    for name in shvarts_collections():
        collection = db[name]
        all_titles += list(collection.find({"root": []}))
        all_duplicates += list(collection.find({"root": {'$ne': []}}))

    # Chronological order drives only the prev/next navigation;
    # the returned title list keeps collection order (as it always has).
    titles = sorted(all_titles, key=lambda x: written_year(x['meta']['date_written']))

    next_nondup = {titles[i]['ID']: titles[i + 1]['ID'] for i in range(len(titles) - 1)}
    previous_nondup = {titles[i]['ID']: titles[i - 1]['ID'] for i in range(1, len(titles))}

    return all_titles, all_duplicates, next_nondup, previous_nondup


def get_poems_texts(ID):
    all_poem_texts = []
    all_duplicates = []

    for name in shvarts_collections():
        collection = db[name]
        all_poem_texts += list(collection.find({"poem_text": {"$exists": True}, "ID": ID}))
        all_duplicates += list(collection.find({"root": {'$ne': []}}))

    return all_poem_texts, all_duplicates


def get_files_by_edition(edition, ID=None):
    all_files = []
    all_duplicates = []

    for name in shvarts_collections():
        collection = db[name]
        query = {"poem_text": {"$exists": True}}
        if ID is not None:
            query["ID"] = ID
        orig_texts = collection.find(query)

        all_files += [file for file in orig_texts if edition in file['meta']['edition']]
        all_duplicates += list(collection.find({"root": {'$ne': []}}))

    # Sort by the page number embedded in the bibliography string ("С. 47").
    for item in all_files:
        page = re.findall(r'[С|с|C|c]..\d+', item['meta']['edition'])
        item['meta']['page'] = int(re.findall(r'\d+', page[0])[0]) if page else 0

    all_files = sorted(all_files, key=lambda k: k['meta']['page'])

    count = len(all_files)
    next_id = {all_files[i]['ID']: all_files[i + 1]['ID'] for i in range(len(all_files) - 1)}
    previous_id = {all_files[i]['ID']: all_files[i - 1]['ID'] for i in range(1, len(all_files))}

    return all_files, all_duplicates, next_id, previous_id, count


def normalize_query(q):
    """The search_text field is ё→е normalized (see scripts/
    build_search_index.py); queries must be normalized the same way."""
    return q.replace('ё', 'е').replace('Ё', 'Е')


# Same Snowball algorithm Mongo's $text uses for default_language: russian,
# so the snippet finder agrees with the index about what "matched".
_stemmer = snowballstemmer.stemmer('russian')

_WORD = re.compile(r'[А-Яа-яЁёA-Za-z-]+')


def _stem(word):
    return _stemmer.stemWord(normalize_query(word).lower())


def find_snippet(doc, query_stems):
    """First line of the poem (or epigraph/dedication) containing a word
    that stems to one of the query's stems, with the hits marked up —
    the KWIC line shown under a search result."""
    for source in (doc.get('poem_text'), doc.get('epigraph'), doc.get('dedication')):
        if not source:
            continue
        for line in source.split('\n'):
            hits = {w for w in _WORD.findall(line) if _stem(w) in query_stems}
            if hits:
                pattern = re.compile('|'.join(
                    re.escape(w) for w in sorted(hits, key=len, reverse=True)))
                parts, last = [], 0
                line = line.strip()
                for m in pattern.finditer(line):
                    parts.append(escape(line[last:m.start()]))
                    parts.append(Markup('<mark>{}</mark>').format(m.group()))
                    last = m.end()
                parts.append(escape(line[last:]))
                return Markup('').join(parts)
    return None


def search_poems(q=None, year_from=None, year_to=None, edition_slug=None):
    """Canonical poems filtered by full-text query (titles + texts, Russian
    stemming, ё/е-insensitive), year-written range, and edition (matching
    the poem's own source or any of its variants). The corpus is small
    (~430 canonical texts), so year/edition filtering happens in Python
    where written_year() can handle string dates."""
    docs = []
    dup_editions = {}

    for name in shvarts_collections():
        collection = db[name]
        query = {"root": []}
        if q:
            query["$text"] = {"$search": normalize_query(q)}
        docs += list(collection.find(query))
        for dup in collection.find({"root": {'$ne': []}}, {"meta.edition": 1}):
            dup_editions[dup['_id']] = dup['meta']['edition']

    match = EDITIONS[edition_slug]['match'] if edition_slug else None
    poems = []
    for doc in docs:
        year = written_year(doc['meta']['date_written'])
        if year_from is not None and (year == 0 or year < year_from):
            continue
        if year_to is not None and (year == 0 or year > year_to):
            continue
        if match is not None:
            editions = [doc['meta']['edition']]
            editions += [dup_editions.get(child, '') for child in doc.get('children', [])]
            if not any(match in e for e in editions):
                continue
        poem = {'ID': doc['ID'], 'title': doc['title'], 'year': year}
        if q:
            poem['snippet'] = find_snippet(doc, {_stem(w) for w in _WORD.findall(q)})
        poems.append(poem)

    # chronological; undatable texts go last
    poems.sort(key=lambda p: (p['year'] == 0, p['year'], p['ID']))
    return poems


@app.route('/')
def base():
    return render_template('index.html', page_name="shvarts")


@app.route('/about/')
def index():
    return render_template('index.html', page_name='project')


@app.route('/list_of_texts/')
def get_list_of_texts():
    q = request.args.get('q', '').strip()

    def int_arg(name):
        value = request.args.get(name, '').strip()
        return int(value) if value.isdigit() else None

    year_from = int_arg('year_from')
    year_to = int_arg('year_to')
    edition = request.args.get('edition', '').strip()
    if edition not in EDITIONS:
        edition = ''

    poems = search_poems(q or None, year_from, year_to, edition or None)
    count = len(poems)

    # pagination (50 per page), preserving the active filters in links
    per_page = 50
    pages = max(1, -(-count // per_page))
    page = min(max(int_arg('page') or 1, 1), pages)
    poems = poems[(page - 1) * per_page: page * per_page]

    params = {'q': q, 'year_from': year_from, 'year_to': year_to, 'edition': edition}
    qs = urlencode({k: v for k, v in params.items() if v})
    qs = qs + '&' if qs else ''

    # group consecutive poems by year for the timeline
    groups = []
    for poem in poems:
        if groups and groups[-1][0] == poem['year']:
            groups[-1][1].append(poem)
        else:
            groups.append((poem['year'], [poem]))

    return render_template('titles.html', page_name='list_of_texts',
                           groups=groups, count=count,
                           page=page, pages=pages, qs=qs,
                           q=q, year_from=year_from, year_to=year_to,
                           edition=edition, editions=EDITIONS,
                           filtered=bool(q or year_from or year_to or edition))


@app.route('/texts_<int:ID>/')
def get_text(ID):
    poem_texts, duplicates = get_poems_texts(ID)
    if not poem_texts:
        abort(404)
    _, _, next_nondup, previous_nondup = get_poems_titles()
    cycle_text = Markup(poem_texts[0]["poem_text"]) if poem_texts[0]["genre"] == "cycle" else None

    return render_template('text.html', page_name='texts',
                           poem_texts=poem_texts, cycle_text=cycle_text, duplicates=duplicates,
                           next_id=next_nondup.get(ID), previous_id=previous_nondup.get(ID))


# The decade-filter and search JSON endpoints (/show_all_poems,
# /filter_poems_by_period_*, /background_process) were jQuery-only
# internals of the old titles page; /list_of_texts/ now serves
# filtered, server-rendered, citable URLs instead.


@app.route('/edition/<slug>/')
def edition_content(slug):
    edition = EDITIONS.get(slug)
    if edition is None:
        abort(404)
    titles, duplicates, _, _, _ = get_files_by_edition(edition['match'])
    return render_template('edition.html', page_name='texts_from_printed_editions',
                           edition=edition, slug=slug, titles=titles, duplicates=duplicates)


@app.route('/edition/<slug>/text_<int:ID>/')
def edition_text(slug, ID):
    edition = EDITIONS.get(slug)
    if edition is None:
        abort(404)
    poem_text, duplicates, _, _, count = get_files_by_edition(edition['match'], ID)
    if not poem_text:
        abort(404)
    titles, _, next_id, previous_id, _ = get_files_by_edition(edition['match'])
    cycle_text = Markup(poem_text[0]["poem_text"]) if poem_text[0]["genre"] == "cycle" else None

    return render_template('edition_text.html', page_name='texts',
                           edition=edition, slug=slug, cycle_text=cycle_text,
                           first_ID=titles[0]["ID"], last_ID=titles[-1]["ID"],
                           next_ID=next_id.get(ID), prev_ID=previous_id.get(ID),
                           poem_text=poem_text, duplicates=duplicates, count=count, titles=titles)


# The six editions used to live at /<slug>/ and /<slug>_text_<ID>/; those URLs
# are indexed and bookmarked, so redirect them permanently to the new scheme.
def _register_legacy_redirects():
    for slug in EDITIONS:
        app.add_url_rule(
            '/{}/'.format(slug), 'legacy_{}'.format(slug),
            lambda slug=slug: redirect(url_for('edition_content', slug=slug), 301))
        app.add_url_rule(
            '/{}_text_<int:ID>/'.format(slug), 'legacy_{}_text'.format(slug),
            lambda ID, slug=slug: redirect(url_for('edition_text', slug=slug, ID=ID), 301))


_register_legacy_redirects()


@app.route('/contrib/')
def photos():
    return render_template('contrib.html', page_name='photos')


@app.route('/other/')
def other():
    return render_template('other.html', page_name='other')


@app.route('/bibl/')
def bibl():
    return render_template('bibl.html', page_name="bibl")


@app.route('/comparison_<int:ID>/')
def compare_poems(ID):
    poem_texts, duplicates = get_poems_texts(ID)
    if not poem_texts:
        abort(404)
    return render_template('comparison.html', poem_texts=poem_texts, duplicates=duplicates)


@app.route('/trial/')
def trial():
    return render_template('trial.html', page_name="trial")


if __name__ == '__main__':
    app.run()
