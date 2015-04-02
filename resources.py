import json

from flask import Flask, request, Response, g, jsonify
from flask.ext.restful import Resource, Api, abort
from werkzeug.exceptions import NotFound,  UnsupportedMediaType
import database

DEFAULT_DB_PATH = 'db/musicdb.db'

#Constants for hypermedia formats and profiles
COLLECTIONJSON = "application/vnd.collection+json"
HAL = "application/hal+json"

FORUM_USER_PROFILE = "http://atlassian.virtues.fi:8090/display/PWP/Exercise+3#Exercise3-Forum_User"
FORUM_MESSAGE_PROFILE = "http://atlassian.virtues.fi:8090/display/PWP/Exercise+3#Exercise3-Forum_Message"
ATOM_THREAD_PROFILE = "https://tools.ietf.org/html/rfc4685"


#Define the application and the api
app = Flask(__name__)
app.debug = True
#Set the database API. Change the DATABASE value from app.config to modify the
#database to be used (for instance for testing)
app.config.update({'DATABASE':database.MusicDatabase(DEFAULT_DB_PATH)})
#Start the RESTful API.
api = Api(app)



def create_error_response(status_code, title, message, resource_type=None):
    response = jsonify(title=title, message=message, resource_type=resource_type)
    response.status_code = status_code
    return response

@app.errorhandler(404)
def resource_not_found(error):
    return create_error_response(404, "Resource not found", "This resource url does not exit")

@app.errorhandler(500)
def unknown_error(error):
    return create_error_response(500, "Error", "The system has failed. Please, contact the administrator")

@app.before_request
def set_database():
    '''Stores an instance of the database API before each request in the flas.g
    variable accessible only from the application context'''
    g.db = app.config['DATABASE']
	
class Artists(Resource):
	
	def get(self):
	
		artist_db = g.db.get_artists()

		envelope = {}
		collection = {}
		envelope["collection"] = collection
		collection['version'] = "1.0"
		collection['href'] = api.url_for(Artists)
		collection['template'] = {
		  "data" : [
			{"prompt" : "", "name" : "name", "value" : "", "required":True},
			{"prompt" : "", "name" : "country", "value" : "", "required":False},
			{"prompt" : "", "name" : "genre", "value" : "", "required":False},
			{"prompt" : "", "name" : "language", "value" : "", "required":False},
			{"prompt" : "", "name" : "formed_in", "value" : "", "required":False}
			
		  ]
		}
		#Create the items
		items = []
		for a in artist_db: 
			_name = a['name']
			_country = a['country']
			_genre = a['genre']
			_language = a['language']
			_formed_in = a['formed_in']
			_url = api.url_for(Artist, artist=_name)
			artist = {}
			artist['href'] = _url
			artist['data'] = []
			value = {'name':'name', 'value':_name}
			artist['data'].append(value)
			value = {'name':'genre', 'value':_genre}
			artist['data'].append(value)
			
			artist['links'] = []
			items.append(artist)
		collection['items'] = items
		return envelope
	
	def post(self):		        
		input = request.get_json(force=True)
		if not input:
			abort(415)

		#It throws a BadRequest exception, and hence a 400 code if the JSON is 
		#not wellformed
		try: 
			data = input['template']['data']
			ipaddress = request.remote_addr

			for d in data: 
				#This code has a bad performance. We write it like this for
				#simplicity. Another alternative should be used instead.
				if d['name'] == 'name':
					name = d['value']
				elif d['name'] == 'genre':
					genre = d['value']
					
				elif d['name'] == 'country':
					country = d['country']
					
				elif d['name'] == 'language':
					language = d['value']
					
				elif d['name'] == 'formed_in':
					formed_in = d['value']
					

			#CHECK THAT DATA RECEIVED IS CORRECT
			if not name or not genre:
				return create_error_response(400, "Wrong request format",
											 "Be sure you include message title and body",
											 "Artists")
		except: 
			#This is launched if either title or body does not exist or if 
			# the template.data array does not exist.
			return create_error_response(400, "Wrong request format",
											 "Be sure you include message title and body",
											 "Artists")
		
		#Create the new message and build the response code'
		aid = g.db.create_artist(name, genre, country=None, language=None, formed_in=None)
		if not aid:
			abort(500)
			   
		#Create the Location header with the id of the message created
		url = api.url_for(Artist, name=name)

		#RENDER
		#Return the response
		return Response(status=201, headers={'Location':url})

class Artist(Resource):

	def get(self, artist):
		artist_db = g.db.get_artist(artist)
		if not artist_db:
			return create_error_response(404, "Unknown message",
										 "There is no artist named %s" % artist,
										 "Artist")
		#FILTER AND GENERATE RESPONSE
		#Create the envelope:
		envelope = {}
		#Now create the links
		links = {}
		envelope["_links"] = links

		#Fill the links
		_curies = [
			{
				"name": "artist",
				"href": FORUM_MESSAGE_PROFILE,
			},
			{
				"name": "atom-thread",
				"href": ATOM_THREAD_PROFILE
			}
		]
		links['curies'] = _curies
		links['self'] = {'href':api.url_for(Artist, artist=artist),
						 'profile': FORUM_MESSAGE_PROFILE}
		links['collection'] = {'href':api.url_for(Artists),
							   'profile': FORUM_MESSAGE_PROFILE,
							   'type':COLLECTIONJSON}
		#Extract the author and add the link
		#If sender is not Anonymous extract the nickname from message_db. The link
		# exist but its href points to None.
		#Extract the parent and add the corresponding link
		
		#Fill the template
		envelope['template'] = {
		  "data" : [
			{"prompt" : "", "name" : "name", "value" : "", "required":True},
			{"prompt" : "", "name" : "genre", "value" : "", "required":False},
			{"prompt" : "", "name" : "country", "value" : "", "required":False},
			{"prompt" : "", "name" : "language", "value" : "", "required":False},
			{"prompt" : "", "name" : "formed_in", "value" : "", "required":False},

			]
		}

		#Fill the rest of properties
		envelope['name'] = artist_db['name']
		envelope['genre'] = artist_db['genre']
		envelope['country'] = artist_db['country']
		envelope['language'] = artist_db['language']
		envelope['formed_in'] = artist_db['formed_in']
		
		#RENDER
		return Response (json.dumps(envelope), 200, mimetype=HAL+";"+FORUM_MESSAGE_PROFILE)
			
	def post(self):
		return
	
class Songs(Resource):

	def get(self, artist):
		songs_db = g.db.get_songs(artist)

		envelope = {}
		collection = {}
		envelope["collection"] = collection
		collection['version'] = "1.0"
		collection['href'] = api.url_for(Songs, artist=artist)
		collection['template'] = {
		  "data" : [
			{"prompt" : "", "name" : "title", "value" : "", "required":True},
			{"prompt" : "", "name" : "artist", "value" : "", "required":True},
			{"prompt" : "", "name" : "length", "value" : "", "required":False},
			{"prompt" : "", "name" : "year", "value" : "", "required":False},
			
		  ]
		}
		#Create the items
		items = []
		for a in songs_db: 
			_title = a['title']
			_length = a['length']
			_year = a['year']
			_url = api.url_for(Song, artist=artist, title=_title)
			song = {}
			song['href'] = _url
			song['data'] = []
			value = {'name':'title', 'value':_title}
			song['data'].append(value)
			value = {'name':'artist', 'value':artist}
			song['data'].append(value)
			value = {'name':'length', 'value':_length}
			song['data'].append(value)
			value = {'name':'year', 'value':_year}
			song['data'].append(value)
			
			song['links'] = []
			items.append(song)
		collection['items'] = items
		return envelope

	def post(self):
		return
		
class Song(Resource):

	def get(self, artist, title):
		song_db = g.db.get_song(artist, title)
		if not song_db:
			return create_error_response(404, "Unknown song",
										 "There is no song named %s of the artist %s" % (title,artist),
										 "Song")
		#FILTER AND GENERATE RESPONSE
		#Create the envelope:
		envelope = {}
		#Now create the links
		links = {}
		envelope["_links"] = links

		#Fill the links
		_curies = [
			{
				"name": "song",
				"href": FORUM_MESSAGE_PROFILE,
			},
			{
				"name": "atom-thread",
				"href": ATOM_THREAD_PROFILE
			}
		]
		links['curies'] = _curies
		links['self'] = {'href':api.url_for(Song, title=title, artist=artist),
						 'profile': FORUM_MESSAGE_PROFILE}
		links['collection'] = {'href':api.url_for(Songs, artist=artist),
							   'profile': FORUM_MESSAGE_PROFILE,
							   'type':COLLECTIONJSON}


		#Extract the author and add the link
		#If sender is not Anonymous extract the nickname from message_db. The link
		# exist but its href points to None.
		#Extract the parent and add the corresponding link
		
		#Fill the template
		envelope['template'] = {
		  "data" : [
			{"prompt" : "", "name" : "title", "value" : "", "required":True},
			{"prompt" : "", "name" : "artist", "value" : "", "required":False},
			{"prompt" : "", "name" : "year", "value" : "", "required":False},
			{"prompt" : "", "name" : "length", "value" : "", "required":False},
			{"prompt" : "", "name" : "sid", "value" : "", "required":False},

			]
		}

		#Fill the rest of properties
		envelope['title'] = song_db['title']
		envelope['artist'] = song_db['artist']
		envelope['year'] = song_db['year']
		envelope['length'] = song_db['length']
		envelope['sid'] = song_db['songid']

		
		#RENDER
		return Response (json.dumps(envelope), 200, mimetype=HAL+";"+FORUM_MESSAGE_PROFILE)
	
	def post(self):
		return

	def delete(self, artist, title):

		if g.db.delete_song(artist, title):
			return '', 204
		else:

			return create_error_response(404, "Unknown message",
										 "There is no a message with id %s" % messageid,
										 "Message")


class Playlist(Resource):

	def get(self, nickname, title):
		pl_db = g.db.get_playlist(title, nickname)
		if not pl_db:
			return create_error_response(404, "Unknown playlist",
										 "There is no playlist called %s" % title,
										 "Playlist")
		#FILTER AND GENERATE RESPONSE
		#Create the envelope:
		envelope = {}
		#Now create the links
		links = {}
		envelope["_links"] = links

		#Fill the links
		_curies = [
			{
				"name": "playlist",
				"href": FORUM_MESSAGE_PROFILE,
			},
			{
				"name": "atom-thread",
				"href": ATOM_THREAD_PROFILE
			}
		]
		links['curies'] = _curies
		links['self'] = {'href':api.url_for(Playlist, nickname=nickname, title=title),
						 'profile': FORUM_MESSAGE_PROFILE}
		links['collection'] = {'href':api.url_for(User_playlists, nickname=nickname),
							   'profile': FORUM_MESSAGE_PROFILE,
							   'type':COLLECTIONJSON}
		#Extract the author and add the link
		#If sender is not Anonymous extract the nickname from message_db. The link
		# exist but its href points to None.
		#Extract the parent and add the corresponding link
		
		#Fill the template
		envelope['template'] = {
		  "data" : [
			{"prompt" : "", "name" : "name", "value" : "", "required":True},
			{"prompt" : "", "name" : "user", "value" : "", "required":True},
			{"prompt" : "", "name" : "created_on", "value" : "", "required":False}
			]
		}

		#Fill the rest of properties
		envelope['name'] = pl_db['name']
		envelope['user'] = pl_db['user']
		envelope['created_on'] = pl_db['created_on']
		
		#RENDER
		return Response (json.dumps(envelope), 200, mimetype=HAL+";"+FORUM_MESSAGE_PROFILE)
	
	def post(self):
		return
	
	def delete(self, nickname, title):
        
		#PERFORM DELETE OPERATIONS
		if g.db.delete_playlist(nickname, title):
			return '', 204
		else:
			#Send error message
			return create_error_response(404, "Unknown playlist",
										 "There is no playlist titled %s" % title,
										 "Playlist")
    
	def put(self, nickname, title):
		'''
		Modifies the title, body and editor properties of this message.

		ENTITY BODY INPUT FORMAT:
		* Media type: Collection+JSON: 
			 http://amundsen.com/media-types/collection/
		   - Extensions: template validation and value-types
			 https://github.com/collection-json/extensions
		 * Profile: Forum_Message
		   http://atlassian.virtues.fi:8090/display/PWP
		   /Exercise+3#Exercise3-Forum_Message

		The body should be a Collection+JSON template.         
		Semantic descriptors used in template: headline, articleBody and editor. 
		If author is not there consider it  "Anonymous". 
	   
		OUTPUT:
		Returns 204 if the message is modified correctly
		Returns 400 if the body of the request is not well formed or it is
		empty.
		Returns 404 if there is no message with messageid
		Returns 415 if the input is not JSON.

		NOTE: 
		Now articleBody links to the column body in the database
		Now headline links to the column title in the database
		Now author links to the column sender in the database.

		'''

		#CHECK THAT MESSAGE EXISTS
		if not g.db.contains_playlist(nickname, title):
			raise NotFound()

		#PARSE THE REQUEST
		#Extract the request body. In general would be request.data
		#Since the request is JSON I use request.get_json
		#get_json returns a python dictionary after serializing the request body
		#get_json returns None if the body of the request is not formatted
		input = request.get_json(force=True)
		# using JSON
		if not input:
			return create_error_response(415, "Unsupported Media Type",
									 "Use a JSON compatible format",
									 "Playlist")


		#It throws a BadRequest exception, and hence a 400 code if the JSON is 
		#not wellformed
		try: 
			data = input['template']['data']
			new_title = None
			new_user = None
			created_on = None
			for d in data: 
				#This code has a bad performance. We write it like this for
				#simplicity. Another alternative should be used instead.
				if d['name'] == 'name':
					new_title = d['value']
				elif d['name'] == 'user':
					new_user = d['value']
				elif d['name'] == 'created_on':
					created_on = d['value']
			#CHECK THAT DATA RECEIVED IS CORRECT
			if not new_title or not new_user:
				abort(400)
		except: 
			#This is launched if either title or body does not exist or the 
			#template.data is not there. 
			abort(400)
		else:
			#Modify the message in the database
			if not g.db.modify_playlist(nickname, title, new_user, new_title, created_on):
				return NotFound()
			return '', 204

class Playlist_songs(Resource):

	def get(self):
		return
	
	def post(self):
		return
class Users(Resource):

	def get(self):
				#PERFORM OPERATIONS
			#Create the messages list
			users_db = g.db.get_users()

		   #FILTER AND GENERATE THE RESPONSE
		   #Create the envelope
			envelope = {}
			collection = {}
			envelope["collection"] = collection
			collection['version'] = "1.0"
			collection['href'] = api.url_for(Users)
			collection['links'] = [{'prompt':'List of all artists in the Finder', 
								  'rel':'artists-all',
								  'href': api.url_for(Artists)}
								]
			collection['template'] = {
			  "data" : [
				{"prompt" : "Insert nickname", "name" : "nickname",
				 "value" : "", "required":True},
				{"prompt" : "Insert password", "name" : "password",
				 "object" : {}, "required":False},
				{"prompt" : "Insert user gender", "name" : "gender",
				 "value" : "", "required":False},
				{"prompt" : "Insert user country", "name" : "country",
				 "value" : "", "required":False},
				{"prompt" : "Insert user age", "name" : "age",
				 "value" : "", "required":False}

			  ]
			}
			#Create the items
			items = []
			for user in users_db: 
				print user
				_nickname = user['nickname']
				_gender = user['gender']
				_country = user['country']
				_age = user['age']
				
				_url = api.url_for(User, nickname=_nickname)
				_playlist_url = api.url_for(User_playlists, nickname=_nickname)
				user = {}
				user['href'] = _url
				user['read-only'] = True
				user['data'] = []
				value = {'name':'nickname', 'value':_nickname}
				user['data'].append(value)
				value = {'name':'gender', 'value':_gender}
				user['data'].append(value)
				value = {'name':'country', 'value':_country}
				user['data'].append(value)
				value = {'name':'age', 'value':_age}
				user['data'].append(value)

				user['links'] = [{
									 'href':_playlist_url,
									 'rel':"playlists",
									 'name':"playlists",
									 'prompt':"Playlists of user"
									}]
				items.append(user)
			collection['items'] = items
			#RENDER
			return envelope

	
	def post(self):
		return
		
class User(Resource):

	def get(self, nickname):
		user_db = g.db.get_user(nickname)
		if not user_db:
			return create_error_response(404, "Unknown message",
										 "There is no user named %s" % nickname,
										 "User")
		#FILTER AND GENERATE RESPONSE
		#Create the envelope:
		envelope = {}
		#Now create the links
		links = {}
		envelope["_links"] = links

		#Fill the links
		_curies = [
			{
				"name": "user",
				"href": FORUM_MESSAGE_PROFILE,
			},
			{
				"name": "atom-thread",
				"href": ATOM_THREAD_PROFILE
			}
		]
		links['curies'] = _curies
		links['self'] = {'href':api.url_for(User, nickname=nickname),
						 'profile': FORUM_MESSAGE_PROFILE}
		links['collection'] = {'href':api.url_for(Users),
							   'profile': FORUM_MESSAGE_PROFILE,
							   'type':COLLECTIONJSON}
		#Extract the author and add the link
		#If sender is not Anonymous extract the nickname from message_db. The link
		# exist but its href points to None.
		#Extract the parent and add the corresponding link
		
		#Fill the template
		envelope['template'] = {
		  "data" : [
			{"prompt" : "", "name" : "nickname", "value" : "", "required":True},
			{"prompt" : "", "name" : "gender", "value" : "", "required":False},
			{"prompt" : "", "name" : "country", "value" : "", "required":False},
			{"prompt" : "", "name" : "age", "value" : "", "required":False}
			]
		}

		#Fill the rest of properties
		envelope['nickname'] = user_db['nickname']
		envelope['gender'] = user_db['gender']
		envelope['country'] = user_db['country']
		envelope['age'] = user_db['age']
		
		#RENDER
		return Response (json.dumps(envelope), 200, mimetype=HAL+";"+FORUM_MESSAGE_PROFILE)

	def post(self, nickname):

			
		#CHECK THAT MESSAGE EXISTS
        #If the message with messageid does not exist return status code 404

        #Extract the request body. In general would be request.data
        #Since the request is JSON I use request.get_json
        #get_json returns a python dictionary after serializing the request body
        #get_json returns None if the body of the request is not formatted
        # using JSON
		input = request.get_json(force=True)
		if not input:
			return create_error_response(415, "Unsupported Media Type",
										 "Use a JSON compatible format",
										 "User")
	
		
		try: 
			data = input['template']['data']
			name = None
			for d in data: 
				#This code has a bad performance. We write it like this for
				#simplicity. Another alternative should be used instead.
				if d['name'] == 'name':
					name = d['value']
			#CHECK THAT DATA RECEIVED IS CORRECT
				if not name or not nickname:
					return create_error_response(400, "Wrong request format",
											 "Be sure you include playlist's title and owner",
											 "User")
		except: 
			#This is launched if either title or body does not exist or if 
			# the template.data array does not exist.
				return create_error_response(400, "Wrong request format",
											 "Be sure you include playlist's title and owner",
											 "User")
		
		#Create the new message and build the response code'
		plid = g.db.create_playlist(name, nickname)
		if not plid:
			abort(500)
			   
		#Create the Location header with the id of the message created
		url = api.url_for(Playlist, nickname=nickname, title=name)

		#RENDER
		#Return the response
		return Response(status=201, headers={'Location':url})
	
	def delete(self, nickname):
		if g.db.delete_user(nickname):
			return '', 204
		else:
			#Send error message
			return create_error_response(404, "Unknown user",
										 "There is no user with nickname %s" % nickname,
										 "User")
										 
	def put(self, nickname):
		'''
		Modifies the title, body and editor properties of this message.

		ENTITY BODY INPUT FORMAT:
		* Media type: Collection+JSON: 
			 http://amundsen.com/media-types/collection/
		   - Extensions: template validation and value-types
			 https://github.com/collection-json/extensions
		 * Profile: Forum_Message
		   http://atlassian.virtues.fi:8090/display/PWP
		   /Exercise+3#Exercise3-Forum_Message

		The body should be a Collection+JSON template.         
		Semantic descriptors used in template: headline, articleBody and editor. 
		If author is not there consider it  "Anonymous". 
	   
		OUTPUT:
		Returns 204 if the message is modified correctly
		Returns 400 if the body of the request is not well formed or it is
		empty.
		Returns 404 if there is no message with messageid
		Returns 415 if the input is not JSON.

		NOTE: 
		Now articleBody links to the column body in the database
		Now headline links to the column title in the database
		Now author links to the column sender in the database.

		'''

		#CHECK THAT MESSAGE EXISTS

		#PARSE THE REQUEST
		#Extract the request body. In general would be request.data
		#Since the request is JSON I use request.get_json
		#get_json returns a python dictionary after serializing the request body
		#get_json returns None if the body of the request is not formatted
		# using JSON
		input = request.get_json(force=True)
		if not input:
			return create_error_response(415, "Unsupported Media Type",
									 "Use a JSON compatible format",
									 "User")


		#It throws a BadRequest exception, and hence a 400 code if the JSON is 
		#not wellformed
		try: 
			data = input['template']['data']
			age = None
			country = None
			gender = None
			for d in data: 
				#This code has a bad performance. We write it like this for
				#simplicity. Another alternative should be used instead.
				if d['name'] == 'age':
					age = d['value']
				elif d['name'] == 'country':
					country = d['value']
				elif d['name'] == 'gender':
					gender = d['value']

		except: 
			#This is launched if either title or body does not exist or the 
			#template.data is not there. 
			abort(400)
		else:
			#Modify the message in the database
			if not g.db.modify_user(nickname, age, country, gender):
				return NotFound()
			return '', 204

class User_playlists(Resource):

	def get(self, nickname):
		pl_db = g.db.get_playlists(nickname)

		envelope = {}
		collection = {}
		envelope["collection"] = collection
		collection['version'] = "1.0"
		collection['href'] = api.url_for(User_playlists, nickname=nickname)
		collection['template'] = {
		  "data" : [
			{"prompt" : "", "name" : "name", "value" : "", "required":True},
			{"prompt" : "", "name" : "user", "value" : "", "required":True},
			{"prompt" : "", "name" : "created_on", "value" : "", "required":False}			
		  ]
		}
		#Create the items
		items = []
		for a in pl_db: 
			_title = a['name']
			_user = a['user']
			_created_on = a['created_on']
			_url = api.url_for(Playlist, nickname=_user, title=_title)
			pl = {}
			pl['href'] = _url
			pl['data'] = []
			value = {'name':'name', 'value':_title}
			pl['data'].append(value)
			value = {'name':'user', 'value':_user}
			pl['data'].append(value)
			value = {'name':'created_on', 'value':_created_on}
			pl['data'].append(value)
			
			pl['links'] = []
			items.append(pl)
			
		collection['items'] = items
		return envelope

	def post(self):
		return
		




api.add_resource(Artists, '/musicfinder/api/artists/',
                 endpoint='artists')
api.add_resource(Artist, '/musicfinder/api/artists/<artist>/',
                 endpoint='artist')
api.add_resource(Songs, '/musicfinder/api/artists/<artist>/songs/',
                 endpoint='songs')
api.add_resource(Song, '/musicfinder/api/artists/<artist>/songs/<title>',
                 endpoint='song')
api.add_resource(Users, '/musicfinder/api/users/',
                 endpoint='users')
api.add_resource(User, '/musicfinder/api/users/<nickname>/',
                 endpoint='user')
api.add_resource(User_playlists, '/musicfinder/api/users/<nickname>/playlists/',
                 endpoint='playlists')
api.add_resource(Playlist, '/musicfinder/api/users/<nickname>/playlists/<title>/',
                 endpoint='playlist')
api.add_resource(Playlist_songs, '/musicfinder/api/users/<nickname>/playlists/<title>/songs/',
                 endpoint='playlist_songs')

				 #Start the application
#DATABASE SHOULD HAVE BEEN POPULATED PREVIOUSLY
if __name__ == '__main__':
    #Debug True activates automatic code reloading and improved error messages
    app.run(debug=True)
				 
