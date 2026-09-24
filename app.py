from flask import Flask, render_template, request
from modules import db
import psycopg

port = 8000

app = Flask(__name__)

@app.route('/')
def home():
	return render_template('player_entry.html')

@app.route('/game')
def game():
	return render_template('game.html')

@app.route('/getPlayer')
def get_player():
	try:
		playerID = int(request.args.get('playerID'))
	except (ValueError, TypeError):
		return {'success': False, 'error': 'Invalid playerID'}

	try:
		player = db.PlayerDatabase().getById(playerID)

		return {'success': True, 'data': {
			'playerID': playerID,
			'codename': player.codename
		}} # Player codename found
	except AttributeError:
		return {'success': False, 'error': {
			'playerID': playerID
		}} # Player codename not found
	except Exception as e:
		return {'success': False, 'error': str(e)} # Something went wrong

@app.route('/getAllPlayers')
def get_all_players():
	try:
		players = db.PlayerDatabase().getAll()
		player_list = [{'id': player.id, 'codename': player.codename} for player in players]

		return {'success': True, 'data': player_list}  # All players retrieved
	except Exception as e:
		return {'success': False, 'error': str(e)}  # Something went wrong

@app.route('/setPlayer', methods=['POST'])
def set_player():
	try:
		playerID = int(request.form.get('playerID')) # -1 by default
	except (ValueError, TypeError):
		return {'success': False, 'error': 'Invalid playerID'}

	codename = request.form.get('codename')

	try:
		player = db.Player(playerID, codename)
		players = db.PlayerDatabase().getAll()

		if any(p.id == playerID for p in players): # Player with ID exists, update codename
			db.PlayerDatabase().update(player)
		else: # Player with ID does not exist, insert new player
			player.id = max([p.id for p in players]) + 1
			db.PlayerDatabase().insert(player)

		return {'success': True, 'data': {
			'playerID': player.id,
			'codename': player.codename
		}} # Player codename set successfully

	except Exception as e:
		return {'success': False, 'error': str(e)}

@app.route('/deletePlayer', methods=['POST'])
def delete_player():
	try:
		playerID = int(request.form.get('playerID'))
	except (ValueError, TypeError):
		return {'success': False, 'error': 'Invalid playerID'}

	try:
		deleted_count = db.PlayerDatabase().delete(playerID)

		if deleted_count > 0:
			return {'success': True, 'message': f'Player with ID {playerID} deleted.'}
		else:
			return {'success': False, 'error': f'Player with ID {playerID} not found.'}

	except Exception as e:
		return {'success': False, 'error': str(e)}  # Something went wrong

if __name__ == '__main__':
	app.run(debug=True, port=port)
