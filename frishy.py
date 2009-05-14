#!/usr/bin/env python
from __future__ import absolute_import

import os
import urllib
import datetime
import time

import couchdb

import webify
from webify.templates.helpers import html
from webify.controllers import webargs

# sudo pip install Beaker
import beaker

app = webify.defaults.app()

@app.controller(path='/')
def index(req):
    yield u'Hello, world!'

@app.controller()
@webargs.add(webargs.SettingsArgParser('users_db'))
def signin(req, users_db):
    email = req.params.get('email', None)
    password = req.params.get('password', None)
    if email is not None:
        users = users_db.view('_design/users/_view/users_by_email',
                             key=email, include_docs=True)
        if len(users) < 1:
            yield 'No user found'
        else:
            user = list(users)[0]
            if password == user.doc[u'password']:
                session = req.environ['beaker.session']
                session[u'user'] = user.doc[u'user']
                session.save()
                yield u'signed in'
                #yield webify.http.status.redirect('/')
            else:
                yield u'failed password signin'
                yield u'email: %s' % email
                yield u'password-submitted: %s' % password
                yield u'password: %s' % user.doc[u'password']
    else:
        yield signin_form()

@app.controller()
def signout(req):
    session = req.environ[u'beaker.session']
    session[u'user'] = None
    session.save()
    yield u'Signed out'
    #yield webify.http.status.redirect('/')
    
def signin_form():
    yield u'<form action="" method="POST">'
    yield u'Email: <input type="text" name="email" />'
    yield u'<br />'
    yield u'Password: <input type="password" name="password" />'
    yield u'<br />'
    yield u'<input type="submit" value="Sign In" />'
    yield u'</form>'
    

@app.controller()
@webargs.add(webargs.SettingsArgParser('updates_db'))
@webargs.add(webargs.SettingsArgParser('users_db'))
def say(req, updates_db, users_db):
    session = req.environ['beaker.session']
    user = session[u'user'] if u'user' in session else None
    message = req.params.get('message', '')
    profile_id = req.params.get('profile', None)
    target_profile = users_db.get(profile_id)
    user_profiles = profiles_of_user(users_db, user)
    first_profile = user_profiles[user_profiles.keys()[0]]

    if first_profile.id in target_profile[u'friends']:
        update = {u'profile': target_profile.id,
                    u'creator': first_profile.id,
                    u'date': int(time.time()),
                    u'deleted': False,
                    u'message': message,
                    u'type': u'update'}
        new_id = updates_db.create(update)
        yield new_id
    else:
        yield u'You may not post to this profile'
        yield u'<br />'
        yield first_profile
        yield u'<br />'
        for f in profile[u'friends']:
            yield f
            yield u'<br />'


def profiles_of_user(users_db, user):
    user_profiles = {}
    if user is not None:
        users = users_db.view('_design/users/_view/profiles_by_user',
                               startkey=[user, 1], endkey=[user,{}], include_docs=True)
        for p in list(users):
            user_profiles[p.doc.id] = p.doc
    return user_profiles
    

@app.controller()
@webargs.add(webargs.RemainingUrl())
@webargs.add(webargs.SettingsArgParser('updates_db'))
@webargs.add(webargs.SettingsArgParser('users_db'))
def profile(req, remaining, updates_db=None, users_db=None):
    session = req.environ['beaker.session']
    session[u'counter'] = session.get('counter', 0) + 1
    session.save()
    yield u'Pageviews: %s' % session['counter']
    yield u'<br />'

    user = session[u'user'] if u'user' in session else None
    user_profiles = profiles_of_user(users_db, user)
    yield u'<br />'

    name, id, _ = remaining.split(u'/', 2)

    updates = updates_db.view('_design/updates/_view/updates_by_profile',
                              startkey=[id], endkey=[id, {}], include_docs=True)
    yield html.h1(name.replace('_', ' '))

    if user is not None:
        if id in user_profiles:
            yield u'<p>This is your profile</p>'
        else:
            yield u'<form action="%s" method="POST">' % '/say'
            yield u'<input type="hidden" name="profile" value="%s" />' % id
            yield u'<input type="text" name="message" value="is " />'
            yield u'<input type="submit" value="Say" />'
            yield u'</form>'
            yield u'<br />'
            yield u'<br />'

    for u in updates:
        yield u[u'value']
        yield u' <b style="font-size:smaller;">'
        yield webify.templates.helpers.time.fuzzy_time_diff(datetime.datetime.fromtimestamp(u.doc['date']))
        yield u' ago'
        yield u'</b>'
        yield u'<br />'

    friends = users_db.view('_design/users/_view/friends',
                            startkey=[id], endkey=[id, {}], include_docs=True)
    yield html.h2(u'Friends')
    for f in friends:
        if f[u'key'][1] == 1:
            yield html.a(profile.url(f.doc[u'name'].replace(' ', '_') + u'/' + f.doc.id + u'/'), f.doc[u'name'])
            yield u'<br />'


    

    
    

# Middleware
from webify.middleware import install_middleware, EvalException, SettingsMiddleware

# Server
from webify.http import server
if __name__ == '__main__':
    mail_server = webify.email.LocalMailServer()
    users_db = couchdb.client.Database('htp://localhost:5984/frishy-users')
    updates_db = couchdb.client.Database('htp://localhost:5984/frishy-updates')
    settings = {
                'mail_server': mail_server,
                'users_db': users_db,
                'updates_db': updates_db,
               }

    from beaker.middleware import SessionMiddleware

    wrapped_app = install_middleware(app, [
                                            SettingsMiddleware(settings),
                                            EvalException,
                                          ])
    wrapped_app = SessionMiddleware(wrapped_app, type='cookie', validate_key='randomstuff', key='mysession', secret='randomsecret')

    print 'Loading server...'
    server.paste_serve(wrapped_app, host='127.0.0.1', port=8085, reload=False)

