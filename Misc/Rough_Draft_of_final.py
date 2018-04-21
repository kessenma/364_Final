import os
import json
import datetime

from flask import Flask, url_for, redirect, render_template, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField, SubmitField, TextAreaField, IntegerField
from wtforms.validators import Required
from flask_login import LoginManager, login_required, login_user, logout_user, current_user, UserMixin
from requests_oauthlib import OAuth2Session
from requests.exceptions import HTTPError
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from flask_wtf import FlaskForm

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True

# All app.config values
app.config['SECRET_KEY'] = 'hard to guess string'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/kessen364final"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Other setup
manager = Manager(app) # In order to use manager
db = SQLAlchemy(app) # For database use

#################################
##### ASSOCIATION TABLE  ########
#################################

gifs_n_songs = db.Table('gifs_n_songs',db.Column('gif_id',db.Integer, db.ForeignKey('gif.id')),db.Column('song_id',db.Integer, db.ForeignKey('songs.id')))

user_collection = db.Table('user_collection',db.Column('gif_id',db.Integer, db.ForeignKey('gif.id')),db.Column('user_id',db.Integer, db.ForeignKey('uses.id')))


#Setup association tables between songs and gif & on the next line users and songs. 

#Should end up with 6 points in the database

#################################
############## MODELS ###########
#################################

#Need to make a User Model.db 
#Need to make a gif Model.db

class Gif(db.Model):
    __tablename__ = "gif"
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(128))
    embedURL = db.Column(db.String(256))
    def __repr__(self):
        return "(title: {}) (URL: {})".format(self.title, self.embedURL)

class SearchTerm(db.Model):
    __tablename__ = "searchterm"
    id = db.Column(db.Integer,primary_key=True)
    term = db.Column(db.String(32),unique=True)
    gifs = db.relationship('Gif',secondary=gifs_n_songs,backref=db.backref('gifs',lazy='dynamic'),lazy='dynamic')
    def __repr__(self):
        return "(term: {})".format(self.term)

class Artist(db.Model):
    __tablename__ = "artists"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    songs = db.relationship('Song',backref='Artist')

class Song(db.Model):
    __tablename__ = "songs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64),unique=True) 
    artist_id = db.Column(db.Integer, db.ForeignKey("artists.id"))

class User(db.Model, UserMixin):
    __tablename__ = "users" # This was built to go with Google specific auth
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    avatar = db.Column(db.String(200))
    tokens = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow())
    songs = db.relationship('Song',secondary=gifs_n_songs,backref=db.backref('songs',lazy='dynamic'),lazy='dynamic')



#################################
######### FORM CLASSES ##########
#################################

class SongForm(FlaskForm):
    name = StringField("What is your name?", validators=[Required()]) #Is this name or username?
    song = StringField("Name a song", validators=[Required()])
    artist = StringField("Who performs it?",validators=[Required()])
    gif = StringField("How does it make you feel?",)  #Not sure if I have to create a new form for gifs?
    submit = SubmitField('Submit')

#################################
####### HELPER FUNCTIONS ########
#################################

def get_or_create_artist(db_session,artist_name):
    artist = db_session.query(Artist).filter_by(name=artist_name).first()
    if artist:
        return artist
    else:
        artist = Artist(name=artist_name)
        db_session.add(artist)
        db_session.commit()
        return artist

def get_or_create_song(db_session, song_title, song_artist):
    song = db_session.query(Song).filter_by(title=song_title).first()
    if song:
        return song
    else:
        artist = get_or_create_artist(db_session, song_artist)
        song = Song(title=song_title,artist_id=artist.id)
        db_session.add(song)
        db_session.commit()
        return song

#may need to make a get or create function for gifs 
#Still need to add in a helper function for the base_url + parameters. 

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

@app.route('/', methods=['GET', 'POST'])
#@app.login_required
def index():
    songs = Song.query.all()
    num_songs = len(songs)
    form = SongForm()
    if form.validate_on_submit():
        if db.session.query(Song).filter_by(title=form.song.data).first():
            flash("You've already saved a song with that title!")
        else:
            get_or_create_song(db.session,form.song.data, form.artist.data)
        return redirect(url_for('see_all'))
    return render_template('index.html', form=form,num_songs=num_songs)

@app.route('/music_form', methods=['GET', 'POST'])
def music_form():
    form = MusicForm()
    return render_template('music_form.html', form=form)


@app.route('/all_songs')
def see_all():
    all_songs = []
    songs = Song.query.all()
    for s in songs:
        artist = Artist.query.filter_by(id=s.artist_id).first()
        all_songs.append((s.title,artist.name, s.genre))
    return render_template('all_songs.html',all_songs=all_songs)

@app.route('/all_artists')
def see_all_artists():
    artists = Artist.query.all()
    names = [(a.name, len(Song.query.filter_by(artist_id=a.id).all())) for a in artists]
    return render_template('all_artists.html',artist_names=names)

@app.route('/login')
def login():
	pass
#Go back to Sample-Login-OAuth-Example-master file to complete the login +logout areas

@app.route('/logout')
def logout():
	pass


#################################
######### App Setup  ############
#################################

if __name__ == "__main__":
    db.create_all()
    #app.run(host='0.0.0.0', port=5001, debug=True) 
    manager.run()
