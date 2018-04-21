import os
import json
import datetime
import requests

from flask import Flask, url_for, redirect, render_template, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from giphy_api_key import api_key
from wtforms import StringField, SubmitField, TextAreaField, IntegerField, FloatField
from wtforms.validators import Required
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
from requests_oauthlib import OAuth2Session 
from requests.exceptions import HTTPError
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from flask_wtf import FlaskForm

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # So you can use http, not just https
basedir = os.path.abspath(os.path.dirname(__file__))

"""App Configuration"""
## http://bitwiser.in/2015/09/09/add-google-login-in-flask.html
class Auth:
    """Google Project Credentials"""
    CLIENT_ID = ('478445007860-hlagnabr2l4jlff0tldsel23btiv9cf8.apps.googleusercontent.com') 
    CLIENT_SECRET = 'Mty34unn7stuPQi_167kyfmA'
    REDIRECT_URI = 'http://localhost:5000/gCallback' 
    AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    USER_INFO = 'https://www.googleapis.com/userinfo/v2/me'
    SCOPE = ['profile', 'email'] 

class Config:
    """Base config"""
    APP_NAME = "Test Google Login"
    SECRET_KEY = os.environ.get("SECRET_KEY") or "something secret"


class DevConfig(Config):
    """Dev config"""
    DEBUG = True
    USE_RELOADER = True
    SQLALCHEMY_DATABASE_URI = "postgresql://localhost/kesssen364final" 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True


class ProdConfig(Config):
    """Production config"""
    DEBUG = False
    USE_RELOADER = True
    SQLALCHEMY_DATABASE_URI = "postgresql://localhost/kesssen364final" #Not sure why there are two databases
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

config = {
    "dev": DevConfig,
    "prod": ProdConfig,
    "default": DevConfig
}

"""APP creation and configuration"""
app = Flask(__name__)
app.config.from_object(config['dev']) 
db = SQLAlchemy(app)
manager = Manager(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong" 


#################################
##### ASSOCIATION TABLE  ########
#################################

#Song_Gif = db.Table('Song_Gif', db.Column('gif_id', db.Integer, db.ForeignKey('gifs.id')), db.Column('song_id', db.Integer, db.ForeignKey('songs.id')))
#User_SearchTerms = db.Table('User_Song', db.Column('gif_id', db.Integer, db.ForeignKey('gifs.id')), db.Column('', db.Integer, db.ForeignKey('gifs.id')))
Song_Gif = db.Table('Song_Gif', db.Column('searchterm_id', db.Integer, db.ForeignKey('searchterms.id')), db.Column('gif_id', db.Integer, db.ForeignKey('gifs.id')))

#################################
############## MODELS ###########
#################################

class User(db.Model, UserMixin):
    __tablename__ = "users" # This was built to go with Google specific auth
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200))
    tokens = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow())

class Gif(db.Model):
    __tablename__ = "gifs"
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(128))
    embedURL = db.Column(db.String(256))

class Artist(db.Model):
    __tablename__ = "artists"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(225))
    songs = db.relationship('Song',backref='Artist')

class Song(db.Model):
    __tablename__ = "songs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64),unique=True) 
    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id"))
    search = db.Column(db.String(64))
    rating = db.Column(db.Float) 
    #gifs = db.relationship('Gif', secondary=Song_Gif, backref=db.backref('songs', lazy='dynamic'), lazy='dynamic') 
    #Gif relationship many-to-many setup

#Model replicated from https://github.com/kessenma/HW4 
## __author__ = "Jackie Cohen (jczetta)"
class SearchTerm(db.Model):
    __tablename__ = 'searchterms'
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(32), unique=True)
    gifs = db.relationship('Gif', secondary=Song_Gif, backref=db.backref('SearchTerm',lazy='dynamic'),lazy='dynamic')




#################################
########## Google Stuff #########
#################################

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


""" OAuth Session creation """
def get_google_auth(state=None, token=None):
    if token:
        return OAuth2Session(Auth.CLIENT_ID, token=token)
    if state:
        return OAuth2Session(
            Auth.CLIENT_ID,
            state=state,
            redirect_uri=Auth.REDIRECT_URI)
    oauth = OAuth2Session(
        Auth.CLIENT_ID,
        redirect_uri=Auth.REDIRECT_URI,
        scope=Auth.SCOPE)
    return oauth

#################################
######### FORM CLASSES ##########
#################################

class SongForm(FlaskForm):
    song = StringField("Name a song", validators=[Required()])
    artist = StringField("Who performs it?",validators=[Required()])
    search = StringField("How does it make you feel?",validators=[Required()]) 
    rating = FloatField("What is your rating of this song?", validators = [Required()])
    submit = SubmitField('Submit')

class UpdateButtonForm(FlaskForm):
    submit = SubmitField('Update')

class UpdateInfoForm(FlaskForm):
    newRating = StringField("What is the new rating of the song?", validators=[Required()])
    submit = SubmitField('Update')

class DeleteButtonForm(FlaskForm):
    submit = SubmitField("Delete")

#################################
####### HELPER FUNCTIONS ########
#################################


##Get or create functions repurposed from https://github.com/alonmelon25/HW4_364 
## __author__ = "Aaron Cheng (alonmelon25)"

def get_gifs_from_giphy(search_string):
    url = "https://api.giphy.com/v1/gifs/search"
    params = {'api_key': api_key, 'q': search_string, 'limit': None}
    search_results = json.loads(requests.get(url=url, params=params).text)
    return search_results['data']

def get_gif_by_id(id):
    """Should return gif object or None"""
    g = Gif.query.filter_by(id=id).first()
    return g

def get_or_create_gif(title, url):
    gif = Gif.query.filter_by(title=title).first()
    if gif:
        return gif
    else:
        gif = Gif(title=title,embedURL = url)
        db.session.add(gif)
        db.session.commit()
        return gif

def get_or_create_search_term(term):
    search_term = SearchTerm.query.filter_by(term=term).first()

    if search_term:
        print("Term exists!")
        return search_term
    else:
        print("Term added!")
        search_term = SearchTerm(term=term)
        gif_list = get_gifs_from_giphy(search_term)
        for g in gif_list:
            g = get_or_create_gif(g['title'], g['embed_url'])
            search_term.gifs.append(g)
        db.session.add(search_term)
        db.session.commit()
        return search_term

def get_or_create_artist(db_session, artist_name):
    artist = db.session.query(Artist).filter_by(name=artist_name).first()
    if artist:
        return artist
    else:
        artist = Artist(name=artist_name)
        db.session.add(artist)
        db.session.commit()
        return artist

def get_or_create_song(db_session, song_title, song_artist, gif_search, song_rating):
    song = db_session.query(Song).filter_by(title=song_title).first()
    if song: 
        print('Found song')
        return song
    else:
        artist = get_or_create_artist(db_session, song_artist)
        song = Song(title=song_title, search=gif_search, artist_id=artist.id, rating = song_rating)
        db.session.add(song)
        #urrent_user.songs.append(song)
        db.session.commit()
        return song

#################################
######## ERROR HANDLING #########
#################################

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


#################################
#### ROUTES & VIEW FUNCTIONS ####
#################################

@app.route('/',methods=["GET","POST"])
@login_required
def index():
    form = SongForm()
    num_songs = Song.query.all()
    if form.validate_on_submit():
        search = form.search.data
        results = get_or_create_search_term(search)
        if db.session.query(Song).filter_by(title=form.song.data, ).first():
            flash("You've already saved a song with that title!") 
        get_or_create_song(db.session, form.song.data, form.artist.data, form.search.data, form.rating.data)
        flash("Successfully saved song!")
        return redirect(url_for('all_songs'))
    return render_template('index.html',form=form, num_songs=num_songs)


## Below routes and their respective html templates are replicated from this repo: https://github.com/SI364-Winter2018/Discussion-Playlists_GetOrCreate 
## __author__ = "Jackie Cohen (jczetta)"
@app.route('/all_songs', methods=["GET", "POST"])
def all_songs():
    all_songs = [] # To be tuple list of title, searchs
    form = DeleteButtonForm()
    songs = Song.query.all()
    for s in songs:
        artist = Artist.query.filter_by(id=s.artist_id).first()
        all_songs.append((s.title,artist.name, s.search))
    return render_template('all_songs.html',all_songs=all_songs)

@app.route('/all_feels', methods=["GET", "POST"])
def all_feels():
    gifs = Gif.query.all()
    return render_template('all_feels.html', all_feels=gifs)

@app.route('/delete/<song>',methods=["GET","POST"])
def delete(song):
    d = TodoList.query.filter_by(id=song).first()
    db.session.delete(d)
    db.session.commit()
    return redirect(url_for('see_all'))


@app.route('/update/<song>', methods = ['GET','POST'])
def updateSong(song):
    print(song)
    form = UpdateInfoForm()
    if form.validate_on_submit():
        new_rating = form.newRating.data
        s = Song.query.filter_by(title = song).first()
        s.rating = new_rating
        db.session.commit()
        flash("Updated rating of " + song)
        return redirect(url_for('index'))
    return render_template('update_info.html',song_name = song, form = form)
    



    # all_feels = [] # To be tuple list of title, searchs
    # feels = Gif.query.all()
    # for f in feels:
    #     #song = Song.query.filter_by(id=f.song_id).first()
    #     all_feels.append((f.title, f.embedURL))
    # return render_template('all_feels.html',all_feels=all_feels)



#################################
##### Authorization Routes ######
#################################

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    google = get_google_auth()
    auth_url, state = google.authorization_url(
        Auth.AUTH_URI, access_type='offline')
    session['oauth_state'] = state
    return render_template('login.html', auth_url=auth_url)

@app.route('/gCallback')
def callback():
    if current_user is not None and current_user.is_authenticated:
        return redirect(url_for('index'))
    if 'error' in request.args:
        if request.args.get('error') == 'access_denied':
            return 'You denied access.'
        return 'Error encountered.'
    # print(request.args, "ARGS")
    if 'code' not in request.args and 'state' not in request.args:
        return redirect(url_for('login'))
    else:
        google = get_google_auth(state=session['oauth_state'])
        try:
            token = google.fetch_token(
                Auth.TOKEN_URI,
                client_secret=Auth.CLIENT_SECRET,
                authorization_response=request.url)
        except HTTPError:
            return 'HTTPError occurred.'
        google = get_google_auth(token=token)
        resp = google.get(Auth.USER_INFO)
        if resp.status_code == 200:
            # print("SUCCESS 200") # For debugging/understanding
            user_data = resp.json()
            email = user_data['email']
            user = User.query.filter_by(email=email).first()
            if user is None:
                # print("No user...")
                user = User()
                user.email = email
            user.name = user_data['name']
            # print(token)
            user.tokens = json.dumps(token)
            user.avatar = user_data['picture']
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        return 'Could not fetch your information.'

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

#################################
######### App Setup  ############
#################################

if __name__ == "__main__":
    db.create_all()
    #app.run(host='0.0.0.0', port=5001, debug=True) 
    manager.run()


migrate = Migrate(app, db) # For database use/updating
manager.add_command('db', MigrateCommand) # Add migrate command to manager
