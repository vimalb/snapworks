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
        items = [_clean_item(item) for item in MONGO_DB.items.find({'user_id': user_id})]
        return Response(json.dumps(items), mimetype='application/json')
    elif request.method in ['POST']:
        req = json.loads(request.get_data())
        req['user_id'] = user_id

        try:
            if req.get('location'):
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
        resp = [_clean_item(item) for item in MONGO_DB.items.find({}).sort("timestamp",pymongo.DESCENDING)][:10]
        return Response(json.dumps(resp), mimetype='application/json')

@app.route("/api/items/nearby", methods=['POST'])
def items_nearby():
    if request.method in ['POST']:
        req = json.loads(request.get_data())
        print req
        resp = [_clean_item(item) for item in MONGO_DB.items.find({})][:10]
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
        inserted_id = MONGO_DB.messages.insert_one(req).inserted_id
    resp = [_clean_message(message) for message in MONGO_DB.messages.find({'item_id': item_id}).sort("timestamp",pymongo.DESCENDING)]
    return Response(json.dumps(resp), mimetype='application/json')


ICON_URLS = {
    'default': 'http://goo.gl/sWSDFa',
    'graffiti': 'http://goo.gl/RG2kNl',
    'trash': 'http://goo.gl/PS4Dor',
    'other': 'http://goo.gl/8uGb5R',
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


@app.route("/api/reset", methods=['GET'])
def reset():
    if request.args.get('key') != 'kwyjibo':
        return Response(json.dumps({'status': 'reset ignored'}), mimetype='application/json')

    MONGO_DB.users.drop()
    MONGO_DB.users.create_index('user_id')

    MONGO_DB.messages.drop()
    MONGO_DB.messages.create_index('user_id')
    MONGO_DB.messages.create_index('item_id')


    MONGO_DB.items.drop()
    MONGO_DB.items.create_index('user.user_id')

    
    return Response(json.dumps({'status': 'reset_complete',
                                'timestamp': utcnow().isoformat(),
                                }), mimetype='application/json')
    
    




    
if __name__ == "__main__":
    app.run('0.0.0.0', 3000, debug=True)
