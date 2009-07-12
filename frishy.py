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
import markdown

# sudo pip install Beaker
import beaker

app = webify.defaults.app()

@app.subapp(path='/')
@webify.urlable()
def index(req, p):
    users_db = req.settings[u'users_db']
    p(u'Frishy.  Squish your friends!')
    p(u'<br />')
    p(html.a('/signin', 'sign in'))
    profiles = users_db.view('_design/users/_view/user_profiles', 
                             limit=10, include_docs=True)
    p(html.h2('Profiles:'))
    p(u'<ul>')
    for p in profiles:
        p(u'<li>')
        p(html.a(profile.url(p.doc[u'name'].replace(' ', '_') + u'/' + p.doc.id + u'/'), p.doc[u'name']))
        p(u'</li>')
    p(u'</ul>')



@app.subapp()
@webify.urlable()
def signin(req, p):
    users_db = req.settings[u'users_db']
    email = req.params.get('email', None)
    password = req.params.get('password', None)
    if email is not None:
        users = users_db.view('_design/users/_view/users_by_email',
                             key=email, include_docs=True)
        if len(users) < 1:
            p('No user found')
        else:
            user = list(users)[0]
            if password == user.doc[u'password']:
                session = req.environ['beaker.session']
                session[u'user'] = user.doc[u'user']
                session.save()
                p(u'signed in')
                #webify.http.status.redirect('/')
            else:
                p(u'failed password signin')
                p(u'email: %s' % email)
                p(u'password-submitted: %s' % password)
                p(u'password: %s' % user.doc[u'password'])
    else:
        p(signin_form())

@app.subapp()
@webify.urlable()
def signout(req, p):
    session = req.environ[u'beaker.session']
    session[u'user'] = None
    session.save()
    p(u'Signed out')
    #webify.http.status.redirect('/')
    
def signin_form():
    yield u'<form action="" method="POST">'
    yield u'Email: <input type="text" name="email" />'
    yield u'<br />'
    yield u'Password: <input type="password" name="password" />'
    yield u'<br />'
    yield u'<input type="submit" value="Sign In" />'
    yield u'</form>'
    

@app.subapp()
@webify.urlable()
def say(req, p):
    users_db = req.settings[u'users_db']
    updates_db = req.settings[u'updates_db']
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
        p(new_id)
    else:
        p(u'You may not post to this profile')
        p(u'<br />')
        p(first_profile)
        p(u'<br />')
        for f in profile[u'friends']:
            p(f)
            p(u'<br />')


def profiles_of_user(users_db, user):
    user_profiles = {}
    if user is not None:
        users = users_db.view('_design/users/_view/profiles_by_user',
                               startkey=[user, 1], endkey=[user,{}], include_docs=True)
        for p in list(users):
            user_profiles[p.doc.id] = p.doc
    return user_profiles
    

@app.subapp()
@webargs.RemainingUrlableAppWrapper()
def profile(req, p, remaining):
    users_db = req.settings[u'users_db']
    updates_db = req.settings[u'updates_db']
    session = req.environ['beaker.session']
    session[u'counter'] = session.get('counter', 0) + 1
    session.save()

    user = session[u'user'] if u'user' in session else None
    user_profiles = profiles_of_user(users_db, user)
    p(u'<br />')

    name, id, _ = remaining.split(u'/', 2)

    updates = updates_db.view('_design/updates/_view/updates_by_profile',
                              startkey=[id], endkey=[id, {}], include_docs=True)
    p(html.h1(name.replace('_', ' ')))

    if user is not None:
        p(u'<form action="%s" method="POST">' % '/say')
        p(u'%s ' % name.replace('_', ' '))
        p(u'<input type="hidden" name="profile" value="%s" />' % id)
        p(u'<input type="text" name="message" value="is "')
        if id in user_profiles:
            p(u'disabled="true"')
        p(u'/>')
        p(u'<input type="submit" value="Say"')
        if id in user_profiles:
            p(u'disabled="true"')
        p(u' />')
        p(u'</form>')
        if id in user_profiles:
            p(u'<p style="font-size:smaller"><em>This is your profile</em>. You may not edit your profile.</p>')
        p(u'<br />')
        p(u'<br />')

    updates = list(updates)
    updates.reverse()
    for u in updates:
        p(u[u'value'])
        p(u' <b style="font-size:x-small;">')
        p(webify.templates.helpers.time.fuzzy_time_diff(datetime.datetime.fromtimestamp(u.doc['date'])))
        p(u' ago')
        p(u' <a href="/" style="font-size:xx-small">(by Joseph)</a>')
        p(u'</b>')
        p(u'<br />')

    friends = users_db.view('_design/users/_view/friends',
                            startkey=[id], endkey=[id, {}], include_docs=True)
    p(html.h2(u'Friends:'))
    p(u'<ul>')
    for f in friends:
        if f[u'key'][1] == 1:
            p(u'<li>')
            p(html.a(profile.url(f.doc[u'name'].replace(' ', '_') + u'/' + f.doc.id + u'/'), f.doc[u'name']))
            p(u'</li>')
    p(u'</ul>')


    p(u'Pageviews: %s' % session['counter'])
    p( u'<br />')

    

    
    

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

    wsgi_app = webify.wsgify(app)

    wrapped_app = install_middleware(wsgi_app, [
                                                SettingsMiddleware(settings),
                                                EvalException,
                                               ])
    wrapped_app = SessionMiddleware(wrapped_app, type='cookie', validate_key='randomstuff', key='mysession', secret='randomsecret')

    print 'Loading server...'
    server.serve(wrapped_app, host='127.0.0.1', port=8085, reload=True)

