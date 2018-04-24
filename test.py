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


api_key ='M3zQdXIg3aqRvSaj7Tj3UGosPEltn0QV'


def get_gifs_from_giphy(search):
    url = "https://api.giphy.com/v1/gifs/search"
    params = {'api_key': api_key, 'q': search, 'limit': None}
    search_results = json.loads(requests.get(url=url, params=params).text)
    return search_results['data']

print(get_gifs_from_giphy("joy"))
print((type(get_gifs_from_giphy("joy"))))

