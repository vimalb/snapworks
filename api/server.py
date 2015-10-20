import os
import sys
sys.path.append(os.path.dirname(__file__))

import json
import dateutil.parser
import re
import random
import requests
import pymongo
from time import sleep
from pymongo import MongoClient
from bson.objectid import ObjectId
from urlparse import urlparse
from copy import deepcopy
from datetime import datetime, timedelta
import pytz
import urllib
from geopy.distance import great_circle
from geopy.geocoders import Nominatim

from flask import Flask, request, send_from_directory, safe_join, Response
from flask.ext.cors import CORS
from collections import Counter
app = Flask(__name__)
CORS(app)

MONGO_URL = os.environ['MONGOLAB_URI']
MONGO_CLIENT = MongoClient(MONGO_URL)
MONGO_DB = MONGO_CLIENT[urlparse(MONGO_URL).path[1:]]

GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']

WWW_SERVER_URL = os.environ['WWW_SERVER_URL']

GEOLOCATOR = Nominatim()

def dump(filename, content):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    with open(filename, 'w') as w:
        w.write(content)

def load(filename):
    with open(filename, 'r') as r:
        return r.read()
        
def jdump(jval, filename):
    jdir = os.path.dirname(filename)
    if jdir and not os.path.exists(jdir):
        os.makedirs(jdir)
    with open(filename, 'w') as w:
        json.dump(jval, w, indent=2)

def jload(filename):
    with open(filename, 'r') as r:
        return json.load(r)        

def dist(a,b):
    return great_circle(a,b).meters


@app.route("/api/test")
def sample():
    resp = {"Testing": "Hello world!"}
    return Response(json.dumps(resp), mimetype='application/json')

@app.route("/api/test/echo/<arg>", methods=['GET', 'PUT', 'DELETE', 'POST'])
def sample_echo(arg):
    if request.method in ['POST','PUT']:
        req = json.loads(request.get_data())
    else:
        req = {}
    resp = {"Testing Arg": arg,
            "Testing Method": request.method,
            "Testing Data": req}
    return Response(json.dumps(resp), mimetype='application/json')

def utcnow():
    return datetime.utcnow().replace(tzinfo=pytz.UTC)



@app.route("/api/users/<user_id>", methods=['GET','POST'])
def user_info(user_id):
    user_profile = MONGO_DB.users.find_one({'user_id': user_id}) or {'user_id': user_id,
                     'name': 'Anonymous',
                     'photo_url': WWW_SERVER_URL+'/profiles/anonymous.jpg'
                    }
    
    if '_id' in user_profile:
        del user_profile['_id']
    
    if request.method in ['POST']:
        req = json.loads(request.get_data())
        req['user_id'] = user_id
        for k in user_profile:
            if req.get(k):
                user_profile[k] = req[k]
        MONGO_DB.users.update_one( {'user_id': user_id}, {'$set': user_profile }, upsert=True )

    return Response(json.dumps(user_profile), mimetype='application/json')


def _clean_item(item):
    item_id = str(item['_id'])
    item['item_id'] = item_id
    del item['_id']
    item['map'] = WWW_SERVER_URL+'/api/items/all/'+item_id+'/map'
    return item

@app.route("/api/users/<user_id>/items", methods=['GET','POST'])
def items_info(user_id):
    if request.method in ['GET']:
        items = [_clean_item(item) for item in MONGO_DB.items.find({'user.user_id': user_id})]
        return Response(json.dumps(items), mimetype='application/json')
    elif request.method in ['POST']:
        req = json.loads(request.get_data())
        req['user'] = MONGO_DB.users.find_one({'user_id': user_id})
        del req['user']['_id']

        req['volunteer_timestamp'] = (utcnow() + timedelta(days=random.uniform(5,10))).isoformat()

        try:
            if req.get('location'):
                req['coord'] = [req['location']['longitude'], req['location']['latitude']]
                req['location'].update(GEOLOCATOR.reverse(coord_to_str(req['location'])).raw)
            print req.get('location')
        except:
            pass
        inserted_id = MONGO_DB.items.insert_one(req).inserted_id
        resp = _clean_item(MONGO_DB.items.find_one({'_id': inserted_id}))
        try:
            get_item_map(resp)
        except:
            pass
        return Response(json.dumps(resp), mimetype='application/json')

@app.route("/api/items/all/<item_id>", methods=['GET'])
def items_detail(item_id):
    if request.method in ['GET']:
        resp = _clean_item(MONGO_DB.items.find_one({'_id': ObjectId(item_id)}))
        return Response(json.dumps(resp), mimetype='application/json')


@app.route("/api/items/popular", methods=['GET'])
def items_popular():
    if request.method in ['GET']:
        resp = [_clean_item(item) for item in MONGO_DB.items.find({}).sort("timestamp",pymongo.DESCENDING).limit(10)]
        return Response(json.dumps(resp), mimetype='application/json')

@app.route("/api/items/nearby", methods=['POST'])
def items_nearby():
    if request.method in ['POST']:
        req = json.loads(request.get_data())
        print req
        resp = [_clean_item(item) for item in MONGO_DB.items.find(
            { 'coord': {'$near': { "$geometry": {
                'type': "Point" ,
                'coordinates': [ req['longitude'], req['latitude'] ]
             } } } } ).limit(10)]
        resp.sort(key=lambda x: x['volunteer_timestamp'])
        return Response(json.dumps(resp), mimetype='application/json')


def _clean_message(message):
    message_id = str(message['_id'])
    message['message_id'] = message_id
    del message['_id']
    return message

@app.route("/api/items/all/<item_id>/messages", methods=['GET', 'POST'])
def items_messages(item_id):
    if request.method in ['POST']:
        req = json.loads(request.get_data())
        req['item_id'] = item_id
        item = MONGO_DB.items.find_one({'_id': ObjectId(item_id)})
        req['issue_type'] = item['issue_type']
        inserted_id = MONGO_DB.messages.insert_one(req).inserted_id
    resp = [_clean_message(message) for message in MONGO_DB.messages.find({'item_id': item_id}).sort("timestamp",pymongo.DESCENDING)]
    return Response(json.dumps(resp), mimetype='application/json')

@app.route("/api/users/<user_id>/item_statuses", methods=['POST'])
def items_statuses(user_id):
    if request.method in ['POST']:
        item_ids = json.loads(request.get_data())

        message_counts = {}
        for message_count in MONGO_DB.messages.aggregate([ 
                                                            {"$group" : {'_id':"$item_id",
                                                            'count':{ '$sum':1},
                                                            }} ]):
            message_counts[message_count['_id']] = message_count['count']


        volunteer_counts = {}
        for volunteer_count in MONGO_DB.messages.aggregate([ {"$match": {'volunteer': True} },
                                                            {"$group" : {'_id':"$item_id",
                                                            'count':{ '$sum':1},
                                                            }} ]):
            volunteer_counts[volunteer_count['_id']] = volunteer_count['count']

        like_counts = {}
        for like_count in MONGO_DB.messages.aggregate([ {"$match": {'like': True} },
                                                            {"$group" : {'_id':"$item_id",
                                                            'count':{ '$sum':1},
                                                            }} ]):
            like_counts[like_count['_id']] = like_count['count']


        self_volunteer_counts = {}
        for volunteer_count in MONGO_DB.messages.aggregate([ {"$match": {'volunteer': True, 'user.user_id': user_id} },
                                                            {"$group" : {'_id':"$item_id",
                                                            'count':{ '$sum':1},
                                                            }} ]):
            self_volunteer_counts[volunteer_count['_id']] = volunteer_count['count']

        self_like_counts = {}
        for like_count in MONGO_DB.messages.aggregate([ {"$match": {'like': True, 'user.user_id': user_id} },
                                                            {"$group" : {'_id':"$item_id",
                                                            'count':{ '$sum':1},
                                                            }} ]):
            self_like_counts[like_count['_id']] = like_count['count']

        resp = {'message_counts': {},
                'volunteer_counts': {},
                'like_counts': {},
                'self_volunteer': {},
                'self_like': {},
                }
        for item_id in item_ids:
            resp['message_counts'][item_id] = message_counts.get(item_id, 0)
            resp['volunteer_counts'][item_id] = volunteer_counts.get(item_id, 0)
            resp['like_counts'][item_id] = like_counts.get(item_id, 0)
            resp['self_volunteer'][item_id] = self_volunteer_counts.get(item_id, 0) > 0
            resp['self_like'][item_id] = self_like_counts.get(item_id, 0) > 0

        return Response(json.dumps(resp), mimetype='application/json')



ICON_URLS = {
    'default': 'http://goo.gl/Oev1D6',
    'graffiti': 'http://goo.gl/lncU0b',
    'trash': 'http://goo.gl/J2eZDy',
    'pothole': 'http://goo.gl/2iuuUX',
    'poop': 'http://goo.gl/7RTiRL',
    'other': 'http://goo.gl/YD6n4t',
    }

def coord_to_str(coord):
    if type(coord) == list or type(coord) == tuple:
        return str(coord[0])+','+str(coord[1])
    else:
        return str(coord['latitude'])+','+str(coord['longitude'])

def get_item_map(item):
    map_filename = os.path.join(os.path.dirname(__file__), 'map_cache/item_'+item['item_id']+'.png')
    if not os.path.exists(map_filename):
        icon_url = ICON_URLS.get(item['issue_type'],ICON_URLS['default']);            
        map_url = 'https://maps.googleapis.com/maps/api/staticmap'
        map_params = {'size': '330x350',
                      'markers': [ 'icon:'+icon_url+'|'+coord_to_str(item['location']) ],
                      'key': GOOGLE_API_KEY,
                      }
        resp = requests.get(map_url, map_params)
        if resp.status_code == 200:
            with open(map_filename, 'wb') as w:
                w.write(resp.content)
        print resp.status_code, resp.url
        sleep(1)        
    with open(map_filename) as r:
        return r.read()

@app.route("/api/items/all/<item_id>/map", methods=['GET'])
def item_map(item_id):
    item = _clean_item(MONGO_DB.items.find_one({'_id': ObjectId(item_id)}))
    return Response(get_item_map(item), mimetype='image/png')

@app.route("/api/dashboard/categories", methods=['GET'])
def dashboard_categories():
    item_counts = {}
    for item_count in MONGO_DB.items.aggregate([ {"$group" : {'_id':"$issue_type",
                                                        'count':{ '$sum':1},
                                                       }} ]):
        item_counts[item_count['_id']] = item_count['count']

    volunteer_counts = {}
    for volunteer_count in MONGO_DB.messages.aggregate([ {"$match": {'volunteer': True} },
                                                    {"$group" : {'_id':"$issue_type",
                                                        'count':{ '$sum':1},
                                                       }} ]):
        volunteer_counts[volunteer_count['_id']] = volunteer_count['count']


    resp = [ {  'name': issue_type,
                'item_count': item_counts.get(issue_type, 0),
                'volunteer_count': volunteer_counts.get(issue_type, 0),
                }
            for issue_type in ['graffiti', 'trash', 'pothole', 'poop', 'other']]
    return Response(json.dumps(resp), mimetype='application/json')


def get_items_map(items):
    map_url = 'https://maps.googleapis.com/maps/api/staticmap'
    map_params = {'size': '330x350',
                  'markers': [ 'icon:'+ICON_URLS.get(item['issue_type'],ICON_URLS['default'])+'|'+coord_to_str(item['location']) for item in items],
                  'key': GOOGLE_API_KEY,
                  }
    resp = requests.get(map_url, map_params)
    return resp.content


@app.route("/api/dashboard/categories/<category>/map", methods=['GET'])
def dashboard_category_map(category):
    items = list(MONGO_DB.items.find({'issue_type': category}))

    return Response(get_items_map(items), mimetype='image/png')



def get_issue_chart(category=None):
    today = utcnow().date()
    issue_chart = { 'series': ['item_count'],
                   'labels': [],
                   'data': [[]],
                   }

    issue_date_counts = Counter([ item['timestamp'][:10] for item in MONGO_DB.items.find({'issue_type': category} if category is not None else {}, {'timestamp': 1}) ])
    for day_offset in range(-28,1,1):
        ref_day = today + timedelta(days=day_offset)
        ref_day_str = ref_day.isoformat()[:10]
        if ref_day_str in issue_date_counts:
            issue_chart['data'][0].append(issue_date_counts[ref_day_str])
            del issue_date_counts[ref_day_str]
        else:
            issue_chart['data'][0].append(0)
        issue_chart['labels'].append(ref_day.strftime('%b %d'))

    pledge_total = sum(issue_date_counts.values())
    for i in range(len(issue_chart['data'][0])):
        issue_chart['data'][0][i] = issue_chart['data'][0][i] + pledge_total
        pledge_total = issue_chart['data'][0][i]
    
    for i in range(len(issue_chart['labels'])):
        if i%4 != 0:
            issue_chart['labels'][i] = ""

    return issue_chart


def get_volunteer_chart(category=None):
    today = utcnow().date()
    issue_chart = { 'series': ['item_count'],
                   'labels': [],
                   'data': [[]],
                   }

    issue_date_counts = Counter([ item['timestamp'][:10] for item in MONGO_DB.messages.find({'issue_type': category, 'volunteer': True} if category is not None else {'volunteer': True}, {'timestamp': 1}) ])
    for day_offset in range(-28,1,1):
        ref_day = today + timedelta(days=day_offset)
        ref_day_str = ref_day.isoformat()[:10]
        if ref_day_str in issue_date_counts:
            issue_chart['data'][0].append(issue_date_counts[ref_day_str])
            del issue_date_counts[ref_day_str]
        else:
            issue_chart['data'][0].append(0)
        issue_chart['labels'].append(ref_day.strftime('%b %d'))

    #pledge_total = sum(issue_date_counts.values())
    #for i in range(len(issue_chart['data'][0])):
    #    issue_chart['data'][0][i] = issue_chart['data'][0][i] + pledge_total
    #    pledge_total = issue_chart['data'][0][i]
    
    for i in range(len(issue_chart['labels'])):
        if i%4 != 0:
            issue_chart['labels'][i] = ""

    return issue_chart


@app.route("/api/dashboard/summary", methods=['GET'])
def dashboard_summary():
    resp = {'item_count': MONGO_DB.items.find({}).count(),
            'volunteer_count': MONGO_DB.messages.find({'volunteer': True}).count(),
            'user_count':  MONGO_DB.users.find({}).count(),
            }
    return Response(json.dumps(resp), mimetype='application/json')


@app.route("/api/dashboard/issue_chart", methods=['GET'])
def dashboard_issue_chart():
    return Response(json.dumps(get_issue_chart()), mimetype='application/json')

@app.route("/api/dashboard/categories/<category>/issue_chart", methods=['GET'])
def dashboard_category_issue_chart(category):
    return Response(json.dumps(get_issue_chart(category)), mimetype='application/json')

@app.route("/api/dashboard/volunteer_chart", methods=['GET'])
def dashboard_volunteer_chart():
    return Response(json.dumps(get_volunteer_chart()), mimetype='application/json')

@app.route("/api/dashboard/categories/<category>/volunteer_chart", methods=['GET'])
def dashboard_category_volunteer_chart(category):
    return Response(json.dumps(get_volunteer_chart(category)), mimetype='application/json')


@app.route("/api/reset", methods=['GET'])
def reset():
    if request.args.get('key') != 'kwyjibo':
        return Response(json.dumps({'status': 'reset ignored'}), mimetype='application/json')

    MONGO_DB.users.drop()
    MONGO_DB.users.create_index('user.user_id')

    MONGO_DB.messages.drop()
    MONGO_DB.messages.create_index('user.user_id')
    MONGO_DB.messages.create_index('item_id')
    MONGO_DB.messages.create_index('issue_type')


    MONGO_DB.items.drop()
    MONGO_DB.items.create_index('user.user_id')
    MONGO_DB.items.create_index([('coord', pymongo.GEOSPHERE)])

    men_names = [   'Michael',
                    'Christopher',
                    'Jason',
                    'David',
                    'James',
                    'Matthew',
                    'Joshua',
                    'John',
                    'Robert',
                    'Joseph',
                    'Daniel',
                    'Brian',
                    'Justin',
                    'William',
                    'Ryan',
                    'Eric',
                    'Nicholas',
                    'Jeremy',
                    'Andrew',
                    'Timothy',
                    ]
    women_names = [ 'Jennifer',
                    'Amanda',
                    'Jessica',
                    'Melissa',
                    'Sarah',
                    'Heather',
                    'Nicole',
                    'Amy',
                    'Elizabeth',
                    'Michelle',
                    'Kimberly',
                    'Angela',
                    'Stephanie',
                    'Tiffany',
                    'Christina',
                    'Lisa',
                    'Rebecca',
                    'Crystal',
                    'Kelly',
                    'Erin',
                    ]

    locations = [{"display_name": "Hall of Justice, 850, Bryant Street, West SoMa, SF, California, 94103, United States of America", "place_id": "77716342", "lon": "-122.404276851235", "longitude": -122.40409969279773, "lat": "37.77513815", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "103383865", "latitude": 37.775497202938986, "address": {"city": "SF", "public_building": "Hall of Justice", "house_number": "850", "country": "United States of America", "county": "SF", "state": "California", "road": "Bryant Street", "country_code": "us", "neighbourhood": "West SoMa", "postcode": "94103"}}, {"display_name": "Masonic Memorial Temple, California Street, Nob Hill, SF, California, 94121, United States of America", "place_id": "62955667", "lon": "-122.412989954684", "longitude": -122.41259212318445, "lat": "37.7911743", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "32947040", "latitude": 37.79172622091882, "address": {"building": "Masonic Memorial Temple", "city": "SF", "country": "United States of America", "county": "SF", "state": "California", "road": "California Street", "country_code": "us", "neighbourhood": "Nob Hill", "postcode": "94121"}}, {"display_name": "Pacific Heights School, Jackson Street, Pacific Heights, SF, California, 94118, United States of America", "place_id": "128111463", "lon": "-122.433660719451", "longitude": -122.43378544030038, "lat": "37.7928746", "osm_type": "relation", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "3528184", "latitude": 37.792588153804935, "address": {"city": "SF", "school": "Pacific Heights School", "country": "United States of America", "county": "SF", "state": "California", "road": "Jackson Street", "country_code": "us", "neighbourhood": "Pacific Heights", "postcode": "94118"}}, {"display_name": "W San Francisco, 181, 3rd Street, South of Market, SF, California, 94124, United States of America", "place_id": "2581161488", "lon": "-122.4004934", "longitude": -122.40027762562546, "lat": "37.7852231", "osm_type": "node", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "3455075365", "latitude": 37.785324799375196, "address": {"city": "SF", "house_number": "181", "country": "United States of America", "hotel": "W San Francisco", "county": "SF", "state": "California", "road": "3rd Street", "country_code": "us", "neighbourhood": "South of Market", "postcode": "94124"}}, {"display_name": "Bessie Carmichael Elementary School, Sherman Street, West SoMa, SF, California, 94103, United States of America", "place_id": "2589946130", "lon": "-122.406346944111", "longitude": -122.40644042819879, "lat": "37.776381", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "353732824", "latitude": 37.776301321982054, "address": {"city": "SF", "school": "Bessie Carmichael Elementary School", "country": "United States of America", "county": "SF", "state": "California", "road": "Sherman Street", "country_code": "us", "neighbourhood": "West SoMa", "postcode": "94103"}}, {"display_name": "1819, O'Farrell Street, Japantown, SF, California, 94115, United States of America", "place_id": "454013727", "lon": "-122.433989032258", "longitude": -122.43397206536636, "lat": "37.783045516129", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "address": {"city": "SF", "house_number": "1819", "country": "United States of America", "county": "SF", "state": "California", "road": "O'Farrell Street", "country_code": "us", "neighbourhood": "Japantown", "postcode": "94115"}, "latitude": 37.782920025333375}, {"display_name": "Larkin Corner Market, 1496, Larkin Street, Nob Hill, SF, California, 94109, United States of America", "place_id": "45935682", "lon": "-122.4190711", "longitude": -122.4188555356079, "lat": "37.7916503", "osm_type": "node", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "3238659965", "latitude": 37.79197007570003, "address": {"city": "SF", "house_number": "1496", "country": "United States of America", "state": "California", "county": "SF", "convenience": "Larkin Corner Market", "road": "Larkin Street", "country_code": "us", "neighbourhood": "Nob Hill", "postcode": "94109"}}, {"display_name": "425-427, Fell Street, Western Addition, SF, California, 94102, United States of America", "place_id": "111832092", "lon": "-122.424853348218", "longitude": -122.42512028571167, "lat": "37.77548805", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "239620171", "latitude": 37.775993017283575, "address": {"city": "SF", "house_number": "425-427", "country": "United States of America", "county": "SF", "state": "California", "road": "Fell Street", "country_code": "us", "neighbourhood": "Western Addition", "postcode": "94102"}}, {"display_name": "1337, Mission Street, West SoMa, SF, California, 94103, United States of America", "place_id": "114760930", "lon": "-122.41501277183", "longitude": -122.41481222411124, "lat": "37.77567495", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "252570873", "latitude": 37.775406914373534, "address": {"city": "SF", "house_number": "1337", "country": "United States of America", "county": "SF", "state": "California", "road": "Mission Street", "country_code": "us", "neighbourhood": "West SoMa", "postcode": "94103"}}, {"display_name": "Academy of Art University, Natoma Street, South of Market, SF, California, 94105, United States of America", "place_id": "71853085", "lon": "-122.399521326362", "longitude": -122.39925333128576, "lat": "37.78625445", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "80296763", "latitude": 37.78597752550215, "address": {"city": "SF", "school": "Academy of Art University", "country": "United States of America", "county": "SF", "state": "California", "road": "Natoma Street", "country_code": "us", "neighbourhood": "South of Market", "postcode": "94105"}}, {"display_name": "Turk Boulevard, Western Addition, SF, California, 94115, United States of America", "place_id": "49760363", "lon": "-122.4304968", "longitude": -122.42675538815486, "lat": "37.7807035", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "8921634", "latitude": 37.781367626790264, "address": {"city": "SF", "country": "United States of America", "county": "SF", "state": "California", "road": "Turk Boulevard", "country_code": "us", "neighbourhood": "Western Addition", "postcode": "94115"}}, {"display_name": "USPS, Laguna Street, Pacific Heights, SF, California, 94123, United States of America", "place_id": "3849062", "lon": "-122.4284335", "longitude": -122.42825093783739, "lat": "37.7868203", "osm_type": "node", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "429641444", "latitude": 37.786721189542774, "address": {"city": "SF", "post_box": "USPS", "country": "United States of America", "county": "SF", "state": "California", "road": "Laguna Street", "country_code": "us", "neighbourhood": "Pacific Heights", "postcode": "94123"}}, {"display_name": "Jones & Sacramento, Jones Street, Nob Hill, SF, California, 94109, United States of America", "place_id": "15142508", "lon": "-122.414324", "longitude": -122.41468160820365, "lat": "37.792595", "osm_type": "node", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "1409407330", "latitude": 37.79268406978303, "address": {"city": "SF", "country_code": "us", "country": "United States of America", "county": "SF", "state": "California", "road": "Jones Street", "address29": "Jones & Sacramento", "neighbourhood": "Nob Hill", "postcode": "94109"}}, {"display_name": "643, Bryant Street, South of Market, SF, California, 94107, United States of America", "place_id": "453788606", "lon": "-122.398961428571", "longitude": -122.39886019649397, "lat": "37.7787388571429", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "address": {"city": "SF", "house_number": "643", "country": "United States of America", "county": "SF", "state": "California", "road": "Bryant Street", "country_code": "us", "neighbourhood": "South of Market", "postcode": "94107"}, "latitude": 37.778627293310755}, {"display_name": "SFJAZZ Center, 201, Franklin Street, Western Addition, SF, California, 94102, United States of America", "place_id": "2573769209", "lon": "-122.4215394", "longitude": -122.42109248391021, "lat": "37.77636975", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "256720482", "latitude": 37.7760117286426, "address": {"city": "SF", "theatre": "SFJAZZ Center", "house_number": "201", "country": "United States of America", "county": "SF", "state": "California", "road": "Franklin Street", "country_code": "us", "neighbourhood": "Western Addition", "postcode": "94102"}}, {"display_name": "Temple Sherith Israel, 2266, California Street, Pacific Heights, SF, California, 94121, United States of America", "place_id": "62823669", "lon": "-122.43197845", "longitude": -122.43259645988049, "lat": "37.7894431", "osm_type": "way", "licence": "Data \u00a9 OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright", "osm_id": "32965008", "latitude": 37.789455754244926, "address": {"place_of_worship": "Temple Sherith Israel", "city": "SF", "house_number": "2266", "country": "United States of America", "county": "SF", "state": "California", "road": "California Street", "country_code": "us", "neighbourhood": "Pacific Heights", "postcode": "94121"}}]

    user_profiles = []
    for i in range(53):
        user_profiles.append({'user_id': 'demo'+str(len(user_profiles) + 1),
                              'username': random.choice(men_names),
                              'photo_url': WWW_SERVER_URL+'/profiles/man'+str(i%50)+'.jpg'
                              })
    for i in range(54):
        user_profiles.append({'user_id': 'demo'+str(len(user_profiles) + 1),
                              'username': random.choice(women_names),
                              'photo_url': WWW_SERVER_URL+'/profiles/woman'+str(i%50)+'.jpg'
                              })

    MONGO_DB.users.insert_many(user_profiles)
    for user in user_profiles:
        del user['_id']

    random.shuffle(user_profiles)

    items = []
    for i in range(16):
        if i < 5:
            issue_type = 'graffiti'
        elif i < 10:
            issue_type = 'trash'
        elif i < 15:
            issue_type = 'pothole'
        elif i < 16:
            issue_type = 'poop'

        req = {'user': user_profiles[i],
                'photo': WWW_SERVER_URL+'/assets/images/'+issue_type+'_'+str((i%5)+1)+'.jpg',
                'issue_type': issue_type,
                'location': locations[i],
                'timestamp': (utcnow() - timedelta(days=random.uniform(1,15))).isoformat(),
                'volunteer_timestamp': (utcnow() + timedelta(days=random.uniform(10,15))).isoformat(),
                'coord': [locations[i]['longitude'], locations[i]['latitude']],
                }
        items.append(req)

    MONGO_DB.items.insert_many(items)

    messages = []
    for item in items:
        creation_date = dateutil.parser.parse(item['timestamp'])
        future_span = int((utcnow() - creation_date).total_seconds()-100)

        likers = random.sample(user_profiles, random.randint(1, 20))
        volunteers = random.sample(user_profiles, random.randint(0, 5))

        item_id = str(item['_id'])

        for user in likers:
            message = {'user': user,
                       'item_id': item_id,
                       'issue_type': item['issue_type'],
                       'like': True,
                       'timestamp': (creation_date + timedelta(seconds=random.randint(10,future_span))).isoformat(),
                       'text': "Liked this"}
            messages.append(message)

        for user in volunteers:
            message = {'user': user,
                       'item_id': item_id,
                       'issue_type': item['issue_type'],
                       'volunteer': True,
                       'timestamp': (creation_date + timedelta(seconds=random.randint(10,future_span))).isoformat(),
                       'text': "Volunteered to help fix this!"}
            messages.append(message)

    MONGO_DB.messages.insert_many(messages)

    
    return Response(json.dumps({'status': 'reset_complete',
                                'timestamp': utcnow().isoformat(),
                                }), mimetype='application/json')
    
    




    
if __name__ == "__main__":
    app.run('0.0.0.0', 3000, debug=True)
