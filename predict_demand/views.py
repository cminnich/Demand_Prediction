#!/usr/bin/env python

from predict_demand import app, demand_main
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, make_response, jsonify
import datetime

@app.route('/api', methods=['POST'])
def post_data():
    """Adds json timestamps to database"""
    if not request.json:
        abort(400)
    if type(request.json) is list:
        return jsonify(demand_main.api_insert(request.json))
    elif type(request.json) is dict:
        if 'timestamp' in request.json.keys():
            single = True
            json_data = request.json['timestamp']
        elif 'timestamps' in request.json.keys():
            single = None
            json_data = request.json['timestamps']
        else:
            return make_response(jsonify( { 'error': 'Bad request, needs timestamp/timestamps key', 
                'timestamp_example': '2012-03-01T00:05:55+00:00',
                'timestamps':['2012-03-01T00:05:55+00:00', '2012-03-01T00:06:23+00:00']} ), 400)
        return jsonify(demand_main.api_insert(json_data,single))
    else:
       abort(400)

@app.route('/api', methods=['GET'])
def get_predicted():
    """Gets predicted demand for next 15 days"""
    return jsonify(demand_main.api_predict())

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/')
def show_entries():
    pred = demand_main.get_predictions()
    hist = demand_main.get_login_history()
    if not hist and not pred:
        return render_template('show_entries.html', show_db=0)
    else:
        return render_template('show_entries.html', show_db=1, entries=pred, history=hist)

@app.route('/clear')
def clear_loaded_db():
    if not session.get('logged_in'):
        abort(401)
    demand_main.initialize()
    flash('Reinitializing...DB now empty')
    return redirect(url_for('show_entries'))
    
@app.route('/read')
def read_json():
    if not session.get('logged_in'):
        abort(401)
    # Add to input data client login database
    if request.form['Submit'] == 'Add File':
        # Adding entire file of login data
        errorMsg = demand_main.load_json_file(request.form['json_filename'])
        if errorMsg is not None:
            flash(errorMsg)
        else:
            flash('Login data added to database. Predictions should be updated')
        demand_main.delete_predictions_with_actuals()
    else:
        # Adding single data point
        error_msg = demand_main.add_single_login(request.form['client_login_time'])
        if 'error' in error_msg.keys():
            flash(error_msg)
        else:
            flash('Data point updated database. Predictions should be updated')
        demand_main.delete_predictions_with_actuals()
    return redirect(url_for('show_entries'))
    
@app.route('/outlier')
def add_outlier():
    if not session.get('logged_in'):
        abort(401)
    # Track manually inputted outliers
    # Load outlier database with predetermined dates
    if request.form['Submit'] == 'Load Outliers':
        demand_main.mark_predetermined_outliers()
        flash('Outliers marked')
    else:
        error_msg = demand_main.mark_outlier(request.form['outlier_id'], request.form['reason'])
        if error_msg is not None:
            flash(error_msg)
        else:
            flash('Outlier marked')
    return redirect(url_for('show_entries'))

@app.route('/analysis')
def analysis_plots():
    if not session.get('logged_in'):
        abort(401)
    demand_main.run_analytics()
    lin_reg_pred_plots = 1 # None: skips plots, much faster
    demand_main.plot_predictions(lin_reg_pred_plots)
    flash('Analysis Complete & Plots Saved')
    return redirect(url_for('show_entries'))

@app.route('/predict')
def update_prediction():
    if not session.get('logged_in'):
        abort(401)
    #demand_main.plot_predictions()
    demand_main.predict_demand(2012,05,01,15)
    flash('Updated Predicted Demand')
    return redirect(url_for('show_entries'))

@app.route('/writecsv')
def write_csv():
    if not session.get('logged_in'):
        abort(401)
    error_msg = demand_main.write_predictions_to_csv()
    if error_msg is not None:
        flash(error_msg)
    else:
        flash('Wrote predictions to file')
    return redirect(url_for('show_entries'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)
    
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('User logged out')
    return redirect(url_for('show_entries'))

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)
 
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)