from flask import Flask
from modules.deezer_client import SpotifyClient

app = Flask(__name__)
app.config.from_object('config')

spotify_client = SpotifyClient()

@app.route('/')
def index():
    return render_template('index.html')
