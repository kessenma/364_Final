#used this tutorial series to get this to run https://www.youtube.com/watch?v=Tc5xnI6c8b0
#Spotify's API is confusing and I am going to need help with translating this code into my final. The way Spotify asks for authorization makes it kind of a hurtle for developers. 

import os
import sys
import json
import datetime
import spotipy
import webbrowser
import spotipy.util as util 
from json.decoder import JSONDecodeError

#################################
### ✨✨✨Steps to run✨✨✨ ####
#################################
'''
1.) in terminal type the following commands out:

	export SPOTIPY_CLIENT_ID='978145a7435544fea5f428889763064c'
	export SPOTIPY_CLIENT_SECRET='b0846e012c0e4cab831af78afa6bd17d'
	export SPOTIPY_REDIRECT_URI='http://Google.com/'

2.) Next, run the practice_api.py file with the following command in terminal: 
	python practice_api.py kessen7832?si=RIO_iykXRF2ETUlBUaIM-A

3.) A browser window ~should~ pop up prompting the user to authorize the application. click the green okay button. 

4.) after clicking the green okay button you should be directed towards a google site that looks normal. DO NOT X OUT OF THIS GOOGLE PAGE. Copy and paste the entire URL at the top and place it in Terminal. After doing this the application will run the following lines of code below. 
'''

username = sys.argv[1]

#User ID: kessen7832?si=RIO_iykXRF2ETUlBUaIM-A

#Erase cache and prompt user permission
try: 
	token = util.prompt_for_user_token(username)
except:
	os.remove(f".cache-{username}")
	token = util.prompt_for_user_token(username)

#Create SpotifyObject 
spotifyObject =spotipy.Spotify(auth=token)

user=spotifyObject.current_user()
print(json.dumps(user, sort_keys=True, indent=4))

displayNAME= user['display_name']
followers = user['followers']['total']

while True: 

	print()
	print (">>> Welcome to Spotify " + displayNAME + "!")
	print (">>> You have " + str(followers) + "followers.")
	print()

#print(json.dumps(VARIABLE, sort_keys=TRUE, indent=4))



