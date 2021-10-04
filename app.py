from flask import Flask, render_template, request, jsonify
import pymongo
import json

from urllib.parse import quote_plus
user = 'admin'
password = 'solaerice'
host='142.93.242.162'
uri = "mongodb://%s:%s@%s" % (
    quote_plus(user), quote_plus(password), host)

app = Flask(__name__)
def get_poems_titles(name_of_db):
    client = pymongo.MongoClient(uri)
    db = client['admin']
    collection= db[name_of_db]
    titles = [title for title in collection.find({"root": []})]
    duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
    non_dup_id_2_next_nondup = {titles[i]['ID']: titles[i + 1]['ID'] for i in range(len(titles) - 1)}
    non_dup_id_2_previous_nondup = {titles[i]['ID']: titles[i - 1]['ID'] for i in range(1, len(titles))}
    return titles, duplicates, non_dup_id_2_next_nondup, non_dup_id_2_previous_nondup


def get_poems_texts(ID, name_of_db):
    client = pymongo.MongoClient(uri)
    db = client['admin']
    collection = db[name_of_db]
    count = collection.count_documents({})
    poem_texts = [text for text in collection.find({"poem_text": {"$exists": True}, "ID":ID})] #вот тут словарь в списке
    duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
    return poem_texts, duplicates, count 

def search_result(word):
    client = pymongo.MongoClient(uri)
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_texts = []
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            texts_in_collection = [text for text in collection.find({"$text": {"$search": word}}, 
                     projection={'_id':False}).sort('meta.date_written')]
            all_texts = all_texts + texts_in_collection

    poems = []

    for text in all_texts:
        lst = []
        lst.append(text.get('ID'))
        lst.append(text.get('title'))
        lst.append(text.get('meta').get('edition'))
        lst.append(text.get('meta').get('date_written'))
        lst.append(text.get('path'))
        poems.append(lst)

    return sorted(poems, key=lambda x: x[1])

def filter_poems_by_year(name_of_db, start_year, end_year):
    client = pymongo.MongoClient(uri)
    db = client['admin']
    collection = db[name_of_db]
    texts_of_exact_period = []
    for text in collection.find({'meta.date_written':{'$gte':start_year, '$lte':end_year}, "root": []}).sort('meta.date_written', pymongo.ASCENDING):
        texts_of_exact_period.append(text)

    poems = []

    for text in texts_of_exact_period:
        lst = []
        lst.append(text.get('ID'))
        lst.append(text.get('title'))
        lst.append(text.get('meta').get('date_written'))
        poems.append(lst)

    return poems

# app.jinja_env.filters['poems_of_period'] = filter_poems_by_year

@app.route('/')
def base():
    return render_template('index.html', page_name="shvarts")

@app.route('/about/')
def index():
    return render_template('index.html', page_name='project')

@app.route('/list_of_texts/')
def get_list_of_texts():
	titles, duplicates, _, _ = get_poems_titles('Shvarts_60')
	return render_template('titles.html', page_name='list_of_texts', 
							titles=titles, duplicates=duplicates)

@app.route('/filter_poems_by_period')
def filter_poems():
    try:
        result = filter_poems_by_year('Shvarts_60', 1960, 1969)
        return jsonify(result=result)
    except Exception as e:
        return str(e)

@app.route('/texts_60_<int:ID>/')
def get_text(ID):
    _, _, non_dup_id_2_next_nondup, non_dup_id_2_previous_nondup = get_poems_titles('Shvarts_60')
    previous_id = non_dup_id_2_previous_nondup[ID] if ID in non_dup_id_2_previous_nondup.keys() else None
    next_id = non_dup_id_2_next_nondup[ID] if ID in non_dup_id_2_next_nondup.keys() else None
    poem_texts, duplicates, _ = get_poems_texts(ID, 'Shvarts_60')
    return render_template('text.html', page_name='texts', 
							poem_texts=poem_texts, duplicates=duplicates, next_id=next_id, previous_id=previous_id)

@app.route('/printed_edition/')
def get_list_of_texts_from_printed_editions():
	titles, duplicates, _, _ = get_poems_titles('Shvarts_ZT')
	return render_template('printed_edition.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)

@app.route('/texts_ZT_<int:ID>/')
def get_ZT_text(ID):
    poem_texts, duplicates, count = get_poems_texts(ID, 'Shvarts_ZT')
    titles, _, _, _ = get_poems_titles('Shvarts_ZT')
    return render_template('text_from_printed_edition.html', page_name='texts', 
							poem_texts=poem_texts, duplicates=duplicates, count=count, titles=titles)

@app.route('/background_process', methods=['GET', 'POST', 'DELETE', 'PATCH'])
def background_process():
    try:
        word = request.args.get('search', 'text', type=str)
        result = search_result(word)
        print(result)
        return jsonify(result=result)
    except Exception as e:
        return str(e)

@app.route('/contrib/')
def photos():
    return render_template('contrib.html', page_name='photos')

@app.route('/other/')
def other():
    return render_template('other.html', page_name='other')

@app.route('/bibl/')
def bibl():
    return render_template('bibl.html', page_name="bibl")

@app.route('/trial/')
def trial():
    return render_template('trial.html', page_name="trial")

@app.route('/comparison_60_<int:ID>/')
def compare_poems(ID):
    poem_texts, duplicates, _ = get_poems_texts(ID, 'Shvarts_60')
    return render_template('comparison.html', poem_texts=poem_texts, duplicates=duplicates)


if __name__=='__main__':
	app.run(host='0.0.0.0', debug=True)