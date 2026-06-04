from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from markupsafe import Markup
import os
import pymongo
import re


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


def search_result(word):
    all_texts = []

    for name in shvarts_collections():
        collection = db[name]
        all_texts += list(collection.find(
            {"$text": {"$search": word}, "root": []},
            projection={'_id': False}).sort('meta.date_written'))

    poems = [[text.get('ID'), text.get('title'),
              text.get('meta').get('edition'), text.get('meta').get('date_written')]
             for text in all_texts]

    return sorted(poems, key=lambda x: x[1])


def show_all_poems():
    all_texts = []

    for name in shvarts_collections():
        collection = db[name]
        all_texts += list(collection.find({"root": []}).sort('meta.date_written', pymongo.ASCENDING))

    poems = [[text.get('ID'), text.get('title'), text.get('meta').get('date_written')]
             for text in all_texts]

    return sorted(poems, key=lambda x: written_year(x[2]))


def filter_poems_by_year(name_of_db, start_year, end_year):
    collection = db[name_of_db]
    texts = collection.find(
        {'meta.date_written': {'$gte': start_year, '$lte': end_year}, "root": []}
    ).sort('meta.date_written', pymongo.ASCENDING)

    return [[text.get('ID'), text.get('title'), text.get('meta').get('date_written')]
            for text in texts]


@app.route('/')
def base():
    return render_template('index.html', page_name="shvarts")


@app.route('/about/')
def index():
    return render_template('index.html', page_name='project')


@app.route('/list_of_texts/')
def get_list_of_texts():
    titles, duplicates, _, _ = get_poems_titles()
    return render_template('titles.html', page_name='list_of_texts',
                           titles=titles, duplicates=duplicates)


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


@app.route('/show_all_poems')
def all_poems():
    return jsonify(result=show_all_poems())


@app.route('/filter_poems_by_period_sixties')
def filter_poems_sixties():
    return jsonify(result=filter_poems_by_year('Shvarts_60', 1960, 1969))


@app.route('/filter_poems_by_period_seventies')
def filter_poems_seventies():
    return jsonify(result=filter_poems_by_year('Shvarts_70', 1970, 1979))


@app.route('/filter_poems_by_period_eighties')
def filter_poems_eighties():
    return jsonify(result=filter_poems_by_year('Shvarts_80', 1980, 1989))


@app.route('/filter_poems_by_period_nineties')
def filter_poems_nineties():
    return jsonify(result=filter_poems_by_year('Shvarts_90', 1990, 1999))


@app.route('/filter_poems_by_period_millenial')
def filter_poems_millenial():
    return jsonify(result=filter_poems_by_year('Shvarts_20', 2000, 2010))


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


@app.route('/background_process')
def background_process():
    word = request.args.get('search', '', type=str)
    if not word.strip():
        return jsonify(result=[])
    return jsonify(result=search_result(word))


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
