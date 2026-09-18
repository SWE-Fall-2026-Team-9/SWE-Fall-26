from flask import Flask, render_template, request
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
	playerID = request.args.get('playerID')
	codename = ''

    # PostgreSQL Logic to retrieve player data based on playerID would go here

	return {'success': True, 'data': {
		'playerID': playerID,
		'codename': codename
    }} # Player codename found
    # return {'success': False, 'error': {
	# 	'playerID': playerID
    # }} # Player codename not found

@app.route('/setPlayer', methods=['POST'])
def set_player():
	playerID = request.args.get('playerID')
	codename = request.args.get('codename')

    # PostgreSQL Logic to update player data based on playerID would go here

	return {'success': True, 'data': {
		'playerID': playerID,
		'codename': codename
    }} # Player codename updated
    # return {'success': False, 'error': {
	# 	'playerID': playerID
    # }} # Something went wrong

if __name__ == '__main__':
	app.run(debug=True, port=port)
