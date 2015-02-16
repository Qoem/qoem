import sniffer
import engine
import re

from engine import MeasurementEngine
from mpd_parser import Parser
from request import Get
from session import Session
from api import api
from time import sleep
from pymongo import Connection

connection = Connection('localhost', 27017)
db = connection['qoems']

sessions = {}

def new_client(local_mpd, request):
	parser = Parser(local_mpd)
	mpd = parser.mpd
	session = Session(mpd, request.timestamp)
	global sessions
	session_identifier = str(request.src_ip) + '-' + str(request.host)
	sessions[session_identifier] = session

def get_playback_bitrate(url):
	"""Parse the URL to unreliably(!) determine the playback bitrate."""
	pattern = re.compile(ur'.*\_(.*kbit).*')
	match = re.match(pattern, url)
	bitrate = int(match.group(1).replace('kbit', ''))
	return bitrate

def handle_m4s_request(request):
	session_identifier = str(request.src_ip) + '-' + str(request.host)
	session = sessions[session_identifier]

	key = request.path
	key = key.split('/')[-2] + '/' + key.split('/')[-1]

	entry = dict(request.__dict__.items() + session.mpd[key].items())
	bitrate = get_playback_bitrate(entry['path'])
	entry['bitrate'] = bitrate 

	client = db[session_identifier]
	client.insert(entry)

def get_active_sessions():
	connection = Connection('localhost', 27017)
	db = connection['qoems']

	collections = db.collection_names(include_system_collections=False)

	connection.close()
	return collections

def get_session_information():
	connection = Connection('localhost', 27017)
	db = connection['qoems']
	sessions = get_active_sessions()

	for session in sessions:
		client = db[session]
		cursor = client.find()
		print '*'*80
		print session
		print '*'*80
		max = 0
		min = 0
		for document in cursor:
			if document['bitrate'] > max:
				max = document['bitrate']
			if document['bitrate'] < min:
				min = document['bitrate']
		print ('max: ' + str(max) + ' min:' + str(min))

if __name__ == '__main__':
	sniff = sniffer.sniffing_thread()
	sniff.start()
	while(True):
		get_session_information()
		sleep(1)