#!/usr/bin/env python

from predict_demand import app
from flask import Flask, g
import sqlite3

def connect_db():
    """Connects to the specific database."""
    # Setting the detect_types paramater to better handle datetimes
    rv = sqlite3.connect(app.config['DATABASE'])
    #,detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    rv.row_factory = sqlite3.Row # allows both index-based and case-insensitive name-based access to columns
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db
    
def init_db():
    """Initialize the database from the schema.sql file"""
    print "In init_db"
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            print "Creating database from schema.sql"
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv
    