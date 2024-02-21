from flask import Flask, render_template, request, jsonify
from markupsafe import Markup
import pymongo
import json
import re


app = Flask(__name__)
def get_poems_titles():
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    # client = pymongo.MongoClient('localhost', 27017)
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_titles = []
    all_duplicates = []
    all_non_dup_id_2_next_nondup = {}
    all_non_dup_id_2_previous_nondup = {}
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            titles = [title for title in collection.find({"root": []})]
            all_titles = all_titles + titles
            
            duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
            all_duplicates = all_duplicates + duplicates
            
    titles = sorted(all_titles, key = lambda x: x['meta']['date_written'] if isinstance(x['meta']['date_written'], int) 
       else int(re.findall('\d{4}', str(x['meta']['date_written']))[0]))
            
    non_dup_id_2_next_nondup = {titles[i]['ID']: titles[i + 1]['ID'] for i in range(len(titles) - 1)}
    all_non_dup_id_2_next_nondup.update(non_dup_id_2_next_nondup)

    non_dup_id_2_previous_nondup = {titles[i]['ID']: titles[i - 1]['ID'] for i in range(1, len(titles))}
    all_non_dup_id_2_previous_nondup.update(non_dup_id_2_previous_nondup)
            
    return all_titles, all_duplicates, all_non_dup_id_2_next_nondup, all_non_dup_id_2_previous_nondup


def get_poems_texts(ID):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    # client = pymongo.MongoClient('localhost', 27017)
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_counts = []
    all_poem_texts = []
    all_duplicates = []
    
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            count = collection.count_documents({})
            all_counts.append(count)
            

            poem_texts = [text for text in collection.find({"poem_text": {"$exists": True}, "ID":ID})] 
            all_poem_texts = all_poem_texts + poem_texts
            
            duplicates = [title for title in collection.find({"root": {'$ne':[]}})]
            all_duplicates = all_duplicates + duplicates
            
    return all_poem_texts, all_duplicates, all_counts 


def get_files_by_edition(edition, ID = None):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    # client = pymongo.MongoClient('localhost', 27017)
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_files = []
    all_duplicates = []
    all_non_dup_id_2_next_nondup = {}
    all_non_dup_id_2_previous_nondup = {}
    
    for collection in all_collections:
#         if collection.startswith('Shvarts'):
        collection = db['{}'.format(collection)]
        orig_texts = collection.find({"poem_text": {"$exists": True}}) if ID is None else collection.find({"poem_text": {"$exists": True}, "ID":ID})
        
        
        files = [file for file in orig_texts if edition in file['meta']['edition']] 

        all_files = all_files + files
        duplicates = [file for file in collection.find({"root": {'$ne':[]}})]
        all_duplicates = all_duplicates + duplicates 

    for index, item in enumerate(all_files):
        bibliography = all_files[index]['meta']['edition']
        page = re.findall('[С|с|C|c]..\d+', bibliography)
        if len(page) != 0:
            page = re.findall('\d+', page[0])
            page = int(page[0])
        else:
            page = 0
        item['meta']["page"] = page

    all_files = sorted(all_files, key=lambda k: k['meta']['page'], reverse=False)

    count = len(all_files)
    
    non_dup_id_2_next_nondup = {all_files[i]['ID']: all_files[i + 1]['ID'] for i in range(len(all_files) - 1)}
    all_non_dup_id_2_next_nondup.update(non_dup_id_2_next_nondup)

    non_dup_id_2_previous_nondup = {all_files[i]['ID']: all_files[i - 1]['ID'] for i in range(1, len(all_files))}
    all_non_dup_id_2_previous_nondup.update(non_dup_id_2_previous_nondup)
            
    return all_files, all_duplicates, all_non_dup_id_2_next_nondup, all_non_dup_id_2_previous_nondup, count


def search_result(word):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    # client = pymongo.MongoClient('localhost', 27017)
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_texts = []
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            texts_in_collection = [text for text in collection.find({"$text": {"$search": word}, "root": []}, 
                     projection={'_id':False}).sort('meta.date_written')]
            all_texts = all_texts + texts_in_collection

    poems = []

    for text in all_texts:
        lst = []
        lst.append(text.get('ID'))
        lst.append(text.get('title'))
        lst.append(text.get('meta').get('edition'))
        lst.append(text.get('meta').get('date_written'))
        poems.append(lst)

    return sorted(poems, key=lambda x: x[1])


def show_all_poems():
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    # client = pymongo.MongoClient('localhost', 27017)
    db = client['admin']
    all_collections = db.list_collection_names()
    
    all_texts = []
    
    for collection in all_collections:
        if collection.startswith('Shvarts'):
            collection = db['{}'.format(collection)]
            for text in collection.find({"root": []}).sort('meta.date_written', pymongo.ASCENDING):
                all_texts.append(text)

    poems = []

    for text in all_texts:
        lst = []
        lst.append(text.get('ID'))
        lst.append(text.get('title'))
        lst.append(text.get('meta').get('date_written'))
        poems.append(lst)
        
    poems = sorted(poems, key=lambda x: x[2] if isinstance(x[2], int) else int(re.findall('\d{4}', str(x[2]))[0]))

    return poems


def filter_poems_by_year(name_of_db, start_year, end_year):
    client = pymongo.MongoClient('mongodb://admin:solaerice@142.93.242.162')
    # client = pymongo.MongoClient('localhost', 27017)
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
def get_text_sixties(ID):
    _, _, non_dup_id_2_next_nondup, non_dup_id_2_previous_nondup = get_poems_titles()
    previous_id = non_dup_id_2_previous_nondup[ID] if ID in non_dup_id_2_previous_nondup.keys() else None
    next_id = non_dup_id_2_next_nondup[ID] if ID in non_dup_id_2_next_nondup.keys() else None
    poem_texts, duplicates, _ = get_poems_texts(ID)
    if poem_texts[0]["genre"] == "cycle":
        cycle_text = Markup(poem_texts[0]["poem_text"])
    else:
        cycle_text = None

    return render_template('text.html', page_name='texts', 
							poem_texts=poem_texts, cycle_text=cycle_text, duplicates=duplicates, next_id=next_id, previous_id=previous_id)

@app.route('/show_all_poems')
def all_poems():
    try:
        result = show_all_poems()
        return jsonify(result=result)
    except Exception as e:
        return str(e)


@app.route('/filter_poems_by_period_sixties')
def filter_poems_sixties():
    try:
        result = filter_poems_by_year('Shvarts_60', 1960, 1969)
        return jsonify(result=result)
    except Exception as e:
        return str(e)
    
@app.route('/filter_poems_by_period_seventies')
def filter_poems_seventies():
    try:
        result = filter_poems_by_year('Shvarts_70', 1970, 1979)
        return jsonify(result=result)
    except Exception as e:
        return str(e)


@app.route('/filter_poems_by_period_eighties')
def filter_poems_eighties():
    try:
        result = filter_poems_by_year('Shvarts_80', 1980, 1989)
        return jsonify(result=result)
    except Exception as e:
        return str(e)


@app.route('/filter_poems_by_period_nineties')
def filter_poems_nineties():
    try:
        result = filter_poems_by_year('Shvarts_90', 1990, 1999)
        return jsonify(result=result)
    except Exception as e:
        return str(e)
    
@app.route('/filter_poems_by_period_millenial')
def filter_poems_millenial():
    try:
        result = filter_poems_by_year('Shvarts_20', 2000, 2010)
        return jsonify(result=result)
    except Exception as e:
        return str(e)

#СБОРНИКИ
# Зелёная Тетрадь
@app.route('/zel_tet/') 
def zel_tet_content():
	titles, duplicates, _, _, _, = get_files_by_edition("Стихи из")
	return render_template('zel_tet.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)
@app.route('/zel_tet_text_<int:ID>/') 
def zel_tet_text(ID):
    poem_text, duplicates, _, _, count = get_files_by_edition("Стихи из", ID)
    titles, _, next_ID_dict, prev_ID_dict, _ = get_files_by_edition("Стихи из")

    if poem_text[0]["genre"] == "cycle":
        cycle_text = Markup(poem_text[0]["poem_text"])
    else:
        cycle_text = None

    first_ID = titles[0]["ID"] 
    last_ID = titles[-1]["ID"] 
    if ID in next_ID_dict:
        next_ID = next_ID_dict[ID]
    else:
        next_ID = None
    if ID in prev_ID_dict:
        prev_ID = prev_ID_dict[ID]
    else:
        prev_ID = None
    return render_template('zel_tet_text.html', page_name='texts',  cycle_text= cycle_text,
                           first_ID=first_ID, last_ID=last_ID, next_ID=next_ID, prev_ID=prev_ID,
							poem_text=poem_text, duplicates=duplicates, count=count, titles=titles)

#Танцующий Давид
@app.route('/tanz_david/') 
def tanz_david_content():
	titles, duplicates, _, _, _ = get_files_by_edition("Танцующий")
	return render_template('tanz_david.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)


@app.route('/tanz_david_text_<int:ID>/') 
def tanz_david_text(ID):
    poem_text, duplicates, _, _, count = get_files_by_edition("Давид", ID)
    titles, _, next_ID_dict, prev_ID_dict, _ = get_files_by_edition("Давид")

    if poem_text[0]["genre"] == "cycle":
        cycle_text = Markup(poem_text[0]["poem_text"])
    else:
        cycle_text = None

    first_ID = titles[0]["ID"] 
    last_ID = titles[-1]["ID"]

    if ID in next_ID_dict:
        next_ID = next_ID_dict[ID]
    else:
        next_ID = None
    if ID in prev_ID_dict:
        prev_ID = prev_ID_dict[ID]
    else:
        prev_ID = None
    return render_template('tanz_david_text.html', page_name='texts', cycle_text=cycle_text,
                           first_ID=first_ID, last_ID=last_ID, next_ID=next_ID, prev_ID=prev_ID,
							poem_text=poem_text, duplicates=duplicates, count=count, titles=titles)


# Собрание сочинений, том 1
@app.route('/soch_v_1/') 
def soch_v_1_content():
	titles, duplicates, _, _, _ = get_files_by_edition("том 1")
	return render_template('soch_v_1.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)


@app.route('/soch_v_1_text_<int:ID>/') 
def soch_v_1_text(ID):
    poem_text, duplicates, _, _, count = get_files_by_edition("том 1", ID)
    titles, _, next_ID_dict, prev_ID_dict, _ = get_files_by_edition("том 1")

    if poem_text[0]["genre"] == "cycle":
        cycle_text = Markup(poem_text[0]["poem_text"])
    else:
        cycle_text = None

    first_ID = titles[0]["ID"] 
    last_ID = titles[-1]["ID"]
    if ID in next_ID_dict:
        next_ID = next_ID_dict[ID]
    else:
        next_ID = None
    if ID in prev_ID_dict:
        prev_ID = prev_ID_dict[ID]
    else:
        prev_ID = None


    return render_template('soch_v_1_text.html', page_name='texts', cycle_text=cycle_text,
                           first_ID=first_ID, last_ID=last_ID, next_ID=next_ID, prev_ID=prev_ID,
							poem_text=poem_text, duplicates=duplicates, count=count, titles=titles)

# Собрание сочинений, том 3
@app.route('/soch_v_3/') 
def soch_v_3_content():
	titles, duplicates, _, _, _ = get_files_by_edition("том 3")
	return render_template('soch_v_3.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)


@app.route('/soch_v_3_text_<int:ID>/') 
def soch_v_3_text(ID):
    poem_text, duplicates, _, _, count = get_files_by_edition("том 3", ID)
    titles, _, next_ID_dict, prev_ID_dict, _ = get_files_by_edition("том 3")

    if poem_text[0]["genre"] == "cycle":
        cycle_text = Markup(poem_text[0]["poem_text"])
    else:
        cycle_text = None

    first_ID = titles[0]["ID"] 
    last_ID = titles[-1]["ID"]
    if ID in next_ID_dict:
        next_ID = next_ID_dict[ID]
    else:
        next_ID = None
    if ID in prev_ID_dict:
        prev_ID = prev_ID_dict[ID]
    else:
        prev_ID = None
    return render_template('soch_v_3_text.html', page_name='texts', cycle_text=cycle_text,
                           first_ID=first_ID, last_ID=last_ID, next_ID=next_ID, prev_ID=prev_ID,
							poem_text=poem_text, duplicates=duplicates, count=count, titles=titles)

# Собрание сочинений, том 5
@app.route('/soch_v_5/') 
def soch_v_5_content():
	titles, duplicates, _, _, _ = get_files_by_edition("том 5")
	return render_template('soch_v_5.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)


@app.route('/soch_v_5_text_<int:ID>/') 
def soch_v_5_text(ID):
    poem_text, duplicates, _, _, count = get_files_by_edition("том 5", ID)
    titles, _, next_ID_dict, prev_ID_dict, _ = get_files_by_edition("том 5")

    if poem_text[0]["genre"] == "cycle":
        cycle_text = Markup(poem_text[0]["poem_text"])
    else:
        cycle_text = None

    first_ID = titles[0]["ID"] 
    last_ID = titles[-1]["ID"]
    if ID in next_ID_dict:
        next_ID = next_ID_dict[ID]
    else:
        next_ID = None
    if ID in prev_ID_dict:
        prev_ID = prev_ID_dict[ID]
    else:
        prev_ID = None
    return render_template('soch_v_5_text.html', page_name='texts', cycle_text=cycle_text,
                           first_ID=first_ID, last_ID=last_ID, next_ID=next_ID, prev_ID=prev_ID,
							poem_text=poem_text, duplicates=duplicates, count=count, titles=titles)



# Перелётная птица

@app.route('/perelet_ptitsa/') 
def perelet_ptitsa_content():
	titles, duplicates, _, _, _ = get_files_by_edition("Перелетная птица")
	return render_template('perelet_ptitsa.html', page_name='texts_from_printed_editions', 
							titles=titles, duplicates=duplicates)


@app.route('/perelet_ptitsa_text_<int:ID>/') 
def perelet_ptitsa_text(ID):
    poem_text, duplicates, _, _, count = get_files_by_edition("Перелетная птица", ID)
    titles, _, next_ID_dict, prev_ID_dict, _ = get_files_by_edition("Перелетная птица")

    if poem_text[0]["genre"] == "cycle":
        cycle_text = Markup(poem_text[0]["poem_text"])
    else:
        cycle_text = None

    first_ID = titles[0]["ID"] 
    last_ID = titles[-1]["ID"]
    if ID in next_ID_dict:
        next_ID = next_ID_dict[ID]
    else:
        next_ID = None
    if ID in prev_ID_dict:
        prev_ID = prev_ID_dict[ID]
    else:
        prev_ID = None
    return render_template('perelet_ptitsa_text.html', page_name='texts', cycle_text=cycle_text,
                           first_ID=first_ID, last_ID=last_ID, next_ID=next_ID, prev_ID=prev_ID,
							poem_text=poem_text, duplicates=duplicates, count=count, titles=titles)



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

@app.route('/comparison_<int:ID>/')
def compare_poems(ID):
    poem_texts, duplicates, _ = get_poems_texts(ID)
    return render_template('comparison.html', poem_texts=poem_texts, duplicates=duplicates)


@app.route('/trial/')
def trial():
    return render_template('trial.html', page_name="trial")

if __name__=='__main__':
	app.run(debug=True)