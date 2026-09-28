from flask import Flask, render_template, request
from modules import db, udp
import ipaddress
import threading
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

port = 8000
DEFAULT_DEST_ADDR = '127.0.0.1'

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
transmitter = udp.Transmitter(DEFAULT_DEST_ADDR)
receiver = udp.Receiver()
playerDB = db.PlayerDatabase()

scores = {}
gamePlayers = {} # Player ID: current-game data
playerEquipment = {} # Equipment ID: Player ID
VALID_TEAMS = {'red', 'green'}
MAX_PLAYERS_PER_TEAM = 15
MAX_INTEGER_ID = 2_147_483_647
MAX_CODENAME_LENGTH = 255
stateLock = threading.RLock()
transmitterLock = threading.Lock()

def parse_positive_integer(data, field_name):
	value = data.get(field_name)
	if isinstance(value, bool):
		return None

	if isinstance(value, int):
		parsed_value = value
	elif isinstance(value, str):
		try:
			parsed_value = int(value)
		except (ValueError, TypeError, OverflowError):
			return None
	else:
		return None

	if parsed_value < 1 or parsed_value > MAX_INTEGER_ID:
		return None
	return parsed_value

@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(error):
	return {'success': False, 'error': 'Request body is too large'}, 413

@app.errorhandler(Exception)
def handle_unexpected_error(error):
	if isinstance(error, HTTPException):
		return error
	app.logger.exception('Unhandled server error')
	return {'success': False, 'error': 'Internal server error'}, 500

def receive_messages():
	while True:
		try:
			message = receiver.recv()
			# TODO: Process the received message.
		except ValueError as error:
			app.logger.warning('Ignored invalid UDP message: %s', error)
		except OSError as error:
			app.logger.error('UDP receiver stopped: %s', error)
			break
		except Exception:
			app.logger.exception('Unexpected UDP receiver error')

@app.route('/')
def home():
	return render_template('player_entry.html', destination=transmitter.ip)

@app.route('/game')
def game():
	return render_template('game.html')

@app.route('/api/database/players', methods=['GET'])
def get_database_players():
	try:
		players = playerDB.getAll()
		player_list = [{'playerID': player.id, 'codename': player.codename} for player in players]
		return {'success': True, 'data': player_list}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/database/players/<int:player_id>', methods=['GET'])
def get_database_player(player_id):
	try:
		player = playerDB.getById(player_id)
		if player is None:
			return {'success': False, 'error': f'Player with ID {player_id} not found.'}

		return {'success': True, 'data': {
			'playerID': player.id,
			'codename': player.codename
		}}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/database/players/create', methods=['POST'])
def create_database_player():
	data = request.get_json(silent=True)
	if not isinstance(data, dict):
		return {'success': False, 'error': 'JSON body is required'}

	player_id = parse_positive_integer(data, 'playerID')
	if player_id is None:
		return {'success': False, 'error': 'Invalid playerID'}

	codename = data.get('codename')
	if not isinstance(codename, str) or not codename.strip():
		return {'success': False, 'error': 'Codename is required'}
	codename = codename.strip()
	if len(codename) > MAX_CODENAME_LENGTH:
		return {'success': False, 'error': 'Codename must be 255 characters or fewer'}

	try:
		with stateLock:
			if playerDB.getById(player_id) is not None:
				return {'success': False, 'error': f'Player with ID {player_id} already exists.'}

			player = db.Player(player_id, codename)
			playerDB.insert(player)

		return {'success': True, 'data': {
			'playerID': player.id,
			'codename': player.codename
		}}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/database/players/<int:player_id>/update', methods=['POST'])
def update_database_player(player_id):
	data = request.get_json(silent=True)
	if not isinstance(data, dict):
		return {'success': False, 'error': 'JSON body is required'}

	codename = data.get('codename')
	if not isinstance(codename, str) or not codename.strip():
		return {'success': False, 'error': 'Codename is required'}
	codename = codename.strip()
	if len(codename) > MAX_CODENAME_LENGTH:
		return {'success': False, 'error': 'Codename must be 255 characters or fewer'}

	try:
		with stateLock:
			if playerDB.getById(player_id) is None:
				return {'success': False, 'error': f'Player with ID {player_id} not found.'}

			player = db.Player(player_id, codename)
			playerDB.update(player)
			if player_id in gamePlayers:
				gamePlayers[player_id]['codename'] = codename

		return {'success': True, 'data': {
			'playerID': player.id,
			'codename': player.codename
		}}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/database/players/<int:player_id>/delete', methods=['POST'])
def delete_database_player(player_id):
	try:
		with stateLock:
			deleted_count = playerDB.delete(player_id)
			if deleted_count == 0:
				return {'success': False, 'error': f'Player with ID {player_id} not found.'}

			game_player = gamePlayers.pop(player_id, None)
			if game_player is not None:
				playerEquipment.pop(game_player.get('equipmentID'), None)
			scores.pop(player_id, None)
		return {'success': True, 'message': f'Player with ID {player_id} deleted.'}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/game/players', methods=['GET'])
def get_game_players():
	with stateLock:
		game_player_list = [
			{**game_player, 'score': scores.get(player_id, 0)}
			for player_id, game_player in gamePlayers.items()
		]
	return {'success': True, 'data': game_player_list}

@app.route('/api/game/players/add', methods=['POST'])
def add_game_player():
	data = request.get_json(silent=True)
	if not isinstance(data, dict):
		return {'success': False, 'error': 'JSON body is required'}

	player_id = parse_positive_integer(data, 'playerID')
	if player_id is None:
		return {'success': False, 'error': 'Invalid playerID'}

	equipment_id = parse_positive_integer(data, 'equipmentID')
	if equipment_id is None:
		return {'success': False, 'error': 'Invalid equipmentID'}

	team = data.get('team')
	if not isinstance(team, str) or team.lower() not in VALID_TEAMS:
		return {'success': False, 'error': 'Team must be red or green'}
	team = team.lower()

	try:
		with stateLock:
			player = playerDB.getById(player_id)
			if player is None:
				return {'success': False, 'error': f'Player with ID {player_id} not found.'}
			if player_id in gamePlayers:
				return {'success': False, 'error': f'Player with ID {player_id} is already in the game.'}
			if equipment_id in playerEquipment:
				return {'success': False, 'error': f'Equipment ID {equipment_id} is already assigned.'}

			team_count = sum(1 for game_player in gamePlayers.values() if game_player['team'] == team)
			if team_count >= MAX_PLAYERS_PER_TEAM:
				return {'success': False, 'error': f'Team {team} already has 15 players.'}

			with transmitterLock:
				transmitter.send(equipment_id)
			gamePlayers[player_id] = {
				'playerID': player_id,
				'codename': player.codename,
				'equipmentID': equipment_id,
				'team': team
			}
			playerEquipment[equipment_id] = player_id
			scores[player_id] = 0
			game_player_data = {
				**gamePlayers[player_id],
				'score': scores[player_id]
			}

		return {'success': True, 'data': game_player_data}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/game/players/<int:player_id>/remove', methods=['POST'])
def remove_game_player(player_id):
	with stateLock:
		game_player = gamePlayers.pop(player_id, None)
		if game_player is None:
			return {'success': False, 'error': f'Player with ID {player_id} is not in the game.'}

		playerEquipment.pop(game_player.get('equipmentID'), None)
		scores.pop(player_id, None)
	return {'success': True, 'message': f'Player with ID {player_id} removed from the game.'}

@app.route('/api/game/players/clear', methods=['POST'])
def clear_game_players():
	with stateLock:
		cleared_count = len(gamePlayers)
		gamePlayers.clear()
		playerEquipment.clear()
		scores.clear()
	return {'success': True, 'message': f'Cleared {cleared_count} players from the game.'}

@app.route('/api/network/destination/change', methods=['POST'])
def change_network_destination():
	data = request.get_json(silent=True)
	if not isinstance(data, dict):
		return {'success': False, 'error': 'JSON body is required'}
	new_ip = data.get('ip')

	if not isinstance(new_ip, str) or not new_ip.strip():
		return {'success': False, 'error': 'IP address is required'}

	try:
		new_ip = str(ipaddress.IPv4Address(new_ip.strip()))
	except ipaddress.AddressValueError:
		return {'success': False, 'error': 'Invalid IPv4 address'}

	with transmitterLock:
		transmitter.ip = new_ip
	print(f"Destination changed to {new_ip}")
	return {'success': True, 'message': f'Network destination changed to {new_ip}.'}

if __name__ == '__main__':
	receiver_thread = threading.Thread(
		target=receive_messages,
		name='udp-receiver',
		daemon=True
	)
	receiver_thread.start()
	app.run(debug=True, port=port, use_reloader=False)
