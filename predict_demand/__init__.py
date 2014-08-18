#!/usr/bin/env python

from flask import Flask
import os

# Creating Flask application
app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'predict_client_demand.db'),
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='uber',
    PASSWORD='logisticstyle'
))

# [optional] Set this env variable to override config settings
app.config.from_envvar('PREDICT_DEMAND_SETTINGS', silent=True)

# Then import views
import predict_demand.views
