from flask import Flask
from flask import render_template, url_for, session, request, redirect, flash
from flask_oauthlib.client import OAuth
from flask_sqlalchemy import SQLAlchemy
import os, json

CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class TwitterBot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String, unique=True, nullable=False)

    def __repr__(self):
        return '<Bot ID: %r>' % self.userid

oauth = OAuth()
twitter = oauth.remote_app('twitter',
                           base_url='https://api.twitter.com/1.1/',
                           request_token_url='https://api.twitter.com/oauth/request_token',
                           access_token_url='https://api.twitter.com/oauth/access_token',
                           authorize_url='https://api.twitter.com/oauth/authorize',
                           consumer_key=CONSUMER_KEY,
                           consumer_secret=CONSUMER_SECRET
                           )

@twitter.tokengetter
def get_twitter_token(token=None):
    return session.get('twitter_token')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    callback_url = url_for('oauthorized', next=request.args.get('next'))
    return twitter.authorize(callback=callback_url or request.referrer or None)

@app.route('/oauthorized')
@twitter.authorized_handler
def oauthorized(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)

    access_token = resp['oauth_token']
    session['access_token'] = access_token
    session['screen_name'] = resp['screen_name']

    session['twitter_token'] = (
        resp['oauth_token'],
        resp['oauth_token_secret']
    )

    return redirect(url_for('index'))

@app.route('/botkill')
def botkill():
    botlist =  TwitterBot.query.all()
    for bot in botlist:
        resp = twitter.post('blocks/create.json', data={
            'screen_name': bot.userid,
            'include_entities': 'false',
            'skip_status': 'true'
        })
        print(resp)
    return json.dumps({
        'killed_bots': len(botlist)
    })

@app.route('/initdb')
def initdb():
    db.create_all()
    with open('testbotlist.txt', 'r') as f:
        for line in f.readlines():
            newbot = TwitterBot(userid=line[:-1])
            db.session.add(newbot)
        db.session.commit()
    return 'Bots updated'