from flask import Flask, render_template, request
from modules import db, udp
import ipaddress
import time

port = 8000
DEFAULT_DEST_ADDR = '127.0.0.1'

app = Flask(__name__)
transmitter = udp.Transmitter(DEFAULT_DEST_ADDR)
receiver = udp.Receiver()
playerDB = db.PlayerDatabase()

scores = {}
gamePlayers = {} # Player ID: current-game data
playerEquipment = {} # Equipment ID: Player ID
VALID_TEAMS = {'red', 'green'}
MAX_PLAYERS_PER_TEAM = 15

@app.route('/')
def home():
	return render_template('player_entry.html')

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

	codename = data.get('codename')
	if not isinstance(codename, str) or not codename.strip():
		return {'success': False, 'error': 'Codename is required'}
	codename = codename.strip()

	try:
		players = playerDB.getAll()
		player_id = max((player.id for player in players), default=0) + 1
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

	try:
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
		deleted_count = playerDB.delete(player_id)
		if deleted_count == 0:
			return {'success': False, 'error': f'Player with ID {player_id} not found.'}

		game_player = gamePlayers.pop(player_id, None)
		if game_player is not None:
			playerEquipment.pop(game_player['equipmentID'], None)
		scores.pop(player_id, None)
		return {'success': True, 'message': f'Player with ID {player_id} deleted.'}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/game/players', methods=['GET'])
def get_game_players():
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

	try:
		player_id = int(data.get('playerID'))
	except (ValueError, TypeError):
		return {'success': False, 'error': 'Invalid playerID'}

	try:
		equipment_id = int(data.get('equipmentID'))
	except (ValueError, TypeError):
		return {'success': False, 'error': 'Invalid equipmentID'}

	team = data.get('team')
	if not isinstance(team, str) or team.lower() not in VALID_TEAMS:
		return {'success': False, 'error': 'Team must be red or green'}
	team = team.lower()

	try:
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

		transmitter.send(equipment_id)
		gamePlayers[player_id] = {
			'playerID': player_id,
			'codename': player.codename,
			'equipmentID': equipment_id,
			'team': team
		}
		playerEquipment[equipment_id] = player_id
		scores[player_id] = 0

		return {'success': True, 'data': {
			**gamePlayers[player_id],
			'score': scores[player_id]
		}}
	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/api/game/players/<int:player_id>/remove', methods=['POST'])
def remove_game_player(player_id):
	game_player = gamePlayers.pop(player_id, None)
	if game_player is None:
		return {'success': False, 'error': f'Player with ID {player_id} is not in the game.'}

	playerEquipment.pop(game_player['equipmentID'], None)
	scores.pop(player_id, None)
	return {'success': True, 'message': f'Player with ID {player_id} removed from the game.'}

@app.route('/api/game/players/clear', methods=['POST'])
def clear_game_players():
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
	newIP = data.get('ip')

	if not isinstance(newIP, str) or not newIP.strip():
		return {'success': False, 'error': 'IP address is required'}

	newIP = newIP.strip()

	try:
		transmitter.send(f'-999:{ipaddress.IPv4Address(newIP)}')
		# Each set of equipment must respond with 'ACK:<equipmentID>


		transmitter.ip = newIP

		return {'success': True, 'message': f'Network changed to {newIP}.'}
	except Exception as e:
		return {'success': False, 'error': str(e)}  # Something went wrong

if __name__ == '__main__':
	app.run(debug=True, port=port)
