#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file implements the following
#   reading in and storing client login data, 
#   running algorithms on stored data,
#   & outputting predicted results.
#
# The data training set (where data is client logins represented by UTC timestamps) can be
#   initialized (emptied),
#   read from JSON file,
#   or read from individual UTC timestamp client login data.
# Note: Once data has been loaded once, subsequent data will be appended to the
# current dataset.  Data initialization should be correctly used (to prevent duplication).
#
# Plotting functions used for in-depth analysis.
# Useful for manual identification and tagging of outlier hours.
#
# Runs algorithm to predict demand by
#  filtering (removes manually tagged outliers and algorithmically identified), 
#  clustering (primarily by day of week & hour of day, secondarily by slope/trend
#   of neighboring hours), and
#  prediction (linear regression to find slope/trend in data over weeks, and smoothed
#   over neighboring hours, then re-extrapolated based on the weighted mean).
#

from predict_demand import db_helper as dbh, demand_formatter as defo, \
    demand_plotter as depl, demand_predictor as depr 
import os
import csv
import sqlite3
import json
from collections import deque

def api_insert(json_data, single=None):
    if single:
        return add_single_login(json_data)
    else:
        return add_multiple_logins(json_data)

def api_predict(num_days_to_predict):
    if num_days_to_predict <= 0:
        return {'error':'Number of days to predict must be positive'}
    if num_days_to_predict >= 100:
        return {'error':'Cannot predict more than 99 days forward'}
    delete_predictions_with_actuals()
    mark_predetermined_outliers()
    db = dbh.get_db()
    cur = db.cursor()
    # For now (smaller dataset), loading all 3 tables in memory is not a problem
    cur.execute('SELECT id FROM login_history ORDER BY id DESC')
    latest = cur.fetchone()
    if latest:
        next_year, next_month, next_day = defo.tp_add_x_days_to_id(latest['id'], 1)
        return predict_demand(next_year,next_month,next_day,num_days_to_predict)
    else:
        return {'error':'No data in login_history DB'}

def initialize():
    """Clears the existing data, reloads the SQL tables"""
    dbh.init_db()

def get_login_history():
    """Returns the entire contents of the read-in historic client
    login data from the login_history database"""
    try:
        logins = dbh.query_db('SELECT id, num_logins FROM login_history ORDER BY id DESC')
        return logins
    except ValueError as err:
        print "Error in get_login_history"
        print err
        return []

def get_predictions():
    """Returns the entire contents of the future predicted data from the
    login_predictions database.
    Formats the prediction data into a list of dictionaries,
    where the two keys for each dict are 'id' and 'num_logins'.
    dict['id'] will return a timestamp
    aka 2012−05−01T00, 21.00
    """
    try:
        predictions = dbh.query_db('SELECT id, num_logins FROM login_predictions ORDER BY id ASC')
        return predictions
    except ValueError as err:
        print "Error in get_login_history"
        print err
        return []

def load_json_file(json_filename):
    """Loads the client login data from the specified JSON file,
    example of the json datastructure:
      ["2012-03-01T00:05:55+00:00", "2012-03-01T00:06:23+00:00", 
       "2012-03-01T00:06:52+00:00", "2012-03-01T00:11:23+00:00", 
       ...
       "2012-04-30T23:57:43+00:00", "2012-04-30T23:59:29+00:00"]
    Groups data in hour chunks and writes data to login_history
    Returns error message if anything goes wrong.
    """
    if json_filename[-4:].lower() != "json":
        json_filename = json_filename + ".json"
        print "Adding '.json' ext to filename"
    # Validate json file exists & is valid
    if not os.path.isfile(json_filename):
        return "Could not find %s"%json_filename
    
    login_data = []
    with open(json_filename, 'r') as infile:
        print "Reading %s..." % json_filename
        login_data = json.load(infile)
    
    if not login_data:
        return 'Nothing in json file..'
    else:
        print 'Formatting json data...'
        logins_added = add_multiple_logins(login_data)
        if 'error' in logins_added.keys():
            return logins_added['error']
            
    return None

def add_multiple_logins(login_data):
    login_dict = defo.datetimes_to_dict(login_data)
    if not login_dict:
        return { 'error': 'No valid timestamps', 
            'timestamps_example': '["2012-03-01T00:05:55+00:00", "2012-03-01T00:06:23+00:00"]'}
    else:
        latest_dt = None
        db = dbh.get_db()
        cur = db.cursor()
        added_logins = {}
        for id_str,hour in login_dict.items():
            #print "Read in hour: %s"%(id_str)
            cur_hour = len(hour) # simple count of logins in this hour
            cur.execute('SELECT * FROM login_history WHERE id=?',(id_str,))
            match = cur.fetchone()
            if match:
                print 'Updating hour count: %d + %d' % (match['num_logins'], cur_hour)
                cur.execute('UPDATE login_history SET num_logins=? WHERE id=?', (match['num_logins']+cur_hour, id_str))
                added_logins['update'] = added_logins.get('update',0) + 1
            else:
                print 'Adding %s with %d logins' % (id_str,len(hour))
                cur.execute('INSERT INTO login_history ' + \
                    '(id, day_name, hour, num_logins) ' + \
                    'values (?, ?, ?, ?)', \
                    (id_str, defo.get_day_2char(id_str), defo.get_hour(id_str), cur_hour))
                added_logins['insert'] = added_logins.get('insert',0) + 1
        # Commit changes
        db.commit()
        added_logins['timestamps'] = login_dict.keys()
        return added_logins
    

def add_single_login(login_timestamp):
    """Loads one client login data point i.e. "2012-03-01T00:05:55+00:00",
    into the database.  If hour entry exists, adds 1 to existing value.
    Returns error message if anything goes wrong.
    """
    login_dt = defo.validate_login_string(login_timestamp)
    if login_dt is None:
        return { 'error': 'Invalid timestamp', 
             'timestamp_example': '2012-03-01T00:05:55+00:00' }
    db = dbh.get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM login_history WHERE id=?', (login_dt,))
    match = cur.fetchone()
    print login_dt
    print 'Match is:'
    print match
    added_login = {}
    if match:
        # Update hour entry, add 1 to existing value
        print match['num_logins']
        cur.execute('UPDATE login_history SET num_logins=? WHERE id=?', (1+match['num_logins'], login_dt))
        added_login['update'] = 1
    else:
        # Entry does not exist
        cur.execute('INSERT INTO login_history ' + \
            '(id, day_name, hour, num_logins) ' + \
            'values (?, ?, ?, ?)', \
            (login_dt,defo.get_day_2char(login_dt), defo.get_hour(login_dt),1))
        added_login['insert'] = 1
    db.commit()
    added_login['timestamp'] = login_timestamp
    return added_login
  
def run_analytics(debug=1):
    """Runs linear regression and smoothing models, outlier identification, and
    stores results in database for prediction to use.
    Pass empty array [] to turn off debug printouts"""
    db = dbh.get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM login_history ORDER BY id ASC')
    all_data = cur.fetchall()
    cur.execute('SELECT * FROM history_outliers')
    outlier_data = cur.fetchall()
    cur.execute('SELECT * FROM prediction_outliers')
    predicted_outlier_data = cur.fetchall()
    if not all_data:
        print "No data loaded in DB"
        return
    predicted_ids,predictions,predicted_slopes=depr.lin_reg_by_hour(all_data,outlier_data,debug)
    depl.scatter_plot(range(len(predicted_slopes)),predicted_slopes,'Predicted_Slopes','Hour','Slope',predicted_ids[-1])
    
def plot_logins():
    """Use the loaded history of client login data to create plots,
    which are saved within the predict_demand/plots folder.
    Used for manual analysis"""
    print "Running analytics on DB\n"
    db = dbh.get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM login_history ORDER BY id ASC')
    all_data = cur.fetchall()
    if not all_data:
        print "No data loaded in DB"
        return
    
    # Tabulate by hour
    hour_x = []
    hour_y = []
    base_day = None
    
    ## Get first predicted day (1 day past last history day)
    pred_year,pred_month,pred_day = defo.tp_add_x_days_to_id(all_data[-1]['id'],1)
    
    ## Plot trends per day over time (for first week predictions)
    for i in range(7):
        pred_day_str = defo.get_day_str(pred_year, pred_month, pred_day)
        hist_day = filter(lambda x: x['day_name']==pred_day_str, all_data)
        pred_id = defo.get_id_str(pred_year, pred_month, pred_day, 00)
        depl.plot_day_trend(pred_id, hist_day)
        pred_year,pred_month,pred_day = defo.tp_add_x_days(pred_year,pred_month,pred_day,1)
    # Weekday analysis
    depl.plot_weekdays([(x['id'],x['num_logins']) for x in all_data \
        if x['day_name'] in ['Mo', 'Tu', 'We', 'Th']])
    
    ## Tabulate by day
    depl.plot_each_day(all_data)
    # Creates dictionaries for each day, 
    #  where the keys are each hour of that day,
    #  and values are a list of tuple pairs (id, count)
    cur.execute('SELECT MAX(num_logins) FROM login_history')
    max_login = cur.fetchone()[0]
    # Monday
    mo_dict = defo.get_hours_dict()
    map(lambda y: mo_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='Mo', all_data))
    depl.plot_day_dict(mo_dict, '1_Monday', max_login)
    # Tuesday
    tu_dict = defo.get_hours_dict()
    map(lambda y: tu_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='Tu', all_data))
    depl.plot_day_dict(tu_dict, '2_Tuesday', max_login)
    # Wednesday
    we_dict = defo.get_hours_dict()
    map(lambda y: we_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='We', all_data))
    depl.plot_day_dict(we_dict, '3_Wednesday', max_login)
    # Thursday
    th_dict = defo.get_hours_dict()
    map(lambda y: th_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='Th', all_data))
    depl.plot_day_dict(th_dict, '4_Thursday', max_login)
    # Friday
    fr_dict = defo.get_hours_dict()
    map(lambda y: fr_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='Fr', all_data))
    depl.plot_day_dict(fr_dict, '5_Friday', max_login)
    # Saturday
    sa_dict = defo.get_hours_dict()
    map(lambda y: sa_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='Sa', all_data))
    depl.plot_day_dict(sa_dict, '6_Saturday', max_login)
    # Sunday
    su_dict = defo.get_hours_dict()
    map(lambda y: su_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='Su', all_data))
    depl.plot_day_dict(su_dict, '7_Sunday', max_login)
    day_dict = {}
    base_year = None
    
    ## Tabulate by week
    # Creates list of most recent week (7 consecutive days)
    last_complete_week_id = None
    temp_complete = deque([])
    min_id = None
    
    for entry in all_data:
        # Getting keys of most recent consecutive week
        if not temp_complete:
            #print 'Starting w/ %d' % entry_doy
            temp_complete.append(entry['id']) # add subsequent day
        else:
            day_delta = defo.dy_subtract_ids(entry['id'],temp_complete[-1])
            if day_delta == 1:
                temp_complete.append(entry['id']) # add subsequent day
                if len(temp_complete) > 7: # can also use while
                    temp_complete.popleft()
                # Save id corresponding to day (hour 0) that has a complete weeks
                # worth of previous data
                if len(temp_complete) == 7:
                    last_complete_week_id = entry['id']
            elif day_delta != 0: # current entry is not the same or a subsequent day
                temp_complete = deque([entry['id']])
        # Save minimum (start) ID key
        if min_id is None or min_id > entry['id']:
            min_id = entry['id']
        
        # Create dictionary with key as the day of year
        # Handle multiple years in database
        year_str = defo.get_year(entry['id'])
        if base_year is None:
            base_year = year_str # if multiple years, assuming years are monotonically increasing
        if year_str != base_year:
            days = (int(year_str)-int(base_year))*365 # Doesn't account for leap years...
        else:
            days = 0
        days = days+int(defo.get_day_of_year(entry['id']))
        day_dict[days] = day_dict.get(days,0) + entry['num_logins']
        if base_day is None:
            base_day = days
        hours = (days - base_day)*24 + entry['hour']
        hour_x.append(hours)
        hour_y.append(entry['num_logins'])
    depl.scatter_plot(hour_x, hour_y)
    depl.plot_by_day(day_dict)
    
    # Need at least 1 consecutive week's worth of data
    if last_complete_week_id is not None: 
        print 'Plotting week data...'
        end_id = last_complete_week_id[:-2]+'23' # Last hour of the day
        start_id = defo.subtract_one_week(end_id)
        print "%s to %s"%(start_id,end_id)
        # Plot full weeks starting at the latest complete week,
        #  where complete means there is at least one data point for 7 consecutive days
        # Lexigraphical (default) string comparison should work with ID format yyyy-hh-ddThh
        while end_id > min_id:
            cur.execute('SELECT id, num_logins FROM login_history WHERE id>? AND id <=? ' \
                + 'ORDER BY id ASC', (start_id, end_id))
            wk_data = cur.fetchall() # Data from an entire week, sorted by most recent first
            # Find the time delta in hours (compute negative x values so  
            #  the most recent is on the right)
            if wk_data:
                last_time = wk_data[-1][0]
                time_delta = map(lambda entry: defo.hr_subtract_ids(entry[0], last_time), wk_data)
                id_list,val_list = [list(entry) for entry in zip(*wk_data)]
                depl.plot_by_week(time_delta, val_list, id_list, max_login)
                
            end_id = start_id
            start_id = defo.subtract_one_week(end_id)
    else:
        print('WARNING: Database does not have continuous week of data')

def predict_demand(year,month,day,num_days,enable_plots=None):
    """
    Given a valid database DB with saved formatted *.json files,
    runs the enabled algorithms to produce predictions for all the days within
    the (inclusive) time span [(beg_year,beg_month,beg_day) to (end_year,end_month,end_day)]
    Returns error string if something goes wrong, None if prediction successful.
    """
    print "Predicting Demand for %d days starting on %d/%d/%d" % (num_days,month,day,year)
    db = dbh.get_db()
    cur = db.cursor()
    # For now (smaller dataset), loading all 3 tables in memory is not a problem
    cur.execute('SELECT * FROM history_outliers')
    outlier_data = cur.fetchall()
    cur.execute('SELECT * FROM prediction_outliers')
    predicted_outlier_data = cur.fetchall()
    cur.execute('SELECT * FROM login_history ORDER BY id ASC')
    all_data = cur.fetchall()
    if not all_data:
        return {'error':'No data in login_history DB'}
    if len(all_data) < 7*24:
        return {'error':'Not enough data to accurately predict demand'}
    predicted_ids,predictions,predicted_slopes=depr.lin_reg_by_hour(all_data,outlier_data)
    cur_pred_id = defo.get_id_str(year, month, day, 0)
    end_pred_id = defo.add_x_hours(cur_pred_id,24*(num_days+1))
    delta_days = defo.dy_delta_days(predicted_ids[0],cur_pred_id)
    # Filter predicted outlier ids to those within prediction timespan
    ol_dict = {}
    demand_predictions = {}
    if predicted_outlier_data:
        map(lambda y: ol_dict.update({str(y['id']):float(y['multiplier'])}), \
            filter(lambda x: x['id']>=cur_pred_id and x['id']<end_pred_id, predicted_outlier_data))
    for count in range(num_days):
        # Calculate the number of weeks to extrapolate on
        extrap_weeks = int(delta_days+count/7)
        #print 'Predicting %s, %d weeks from (%s,%s) predictions'%(cur_pred_id,extrap_weeks,predicted_ids[0],predicted_ids[-1])
        pred_day_str = defo.get_day_str(year, month, day)
        prediction_list = []
        pred_id_list = []
        pred_data = []
        for hour in range(24):
            cur_pred_id = defo.get_id_str(year, month, day, hour)
            offset = int(defo.hr_subtract_ids(cur_pred_id,predicted_ids[0])%(24*7))
            prediction = predictions[offset] + extrap_weeks*predicted_slopes[offset]
            if cur_pred_id in ol_dict.keys():
                prediction *= ol_dict[cur_pred_id]
                #print 'Predicted (%fx) Multiplier'%ol_dict[cur_pred_id]
            #print 'Prediction ID: %s, Logins: %f (%s: %fx%dWeeks + %f)'%(cur_pred_id,prediction,
            #    predicted_ids[offset],predicted_slopes[offset],extrap_weeks,predictions[offset])
            pred_data.append((cur_pred_id,prediction))
            demand_predictions[cur_pred_id] = prediction
        # Add to database, doing predictions on a day at a time basis (always 24 entries/hours)
        cur.executemany("INSERT or REPLACE into login_predictions (id, num_logins) values (?, ?)",\
            pred_data)
        # Move to next day
        year, month, day = defo.tp_add_x_days(year, month, day, 1)
    db.commit()
    return demand_predictions

def plot_predictions(update_plots=None):
    """Updates the predictions (if update_plots is not None) which will also plot
    the linear regression predictions with past data,
    and Plots (saved to file) each predicted day in login_predictions"""
    db = dbh.get_db()
    cur = db.cursor()
    if update_plots is not None:
        num_days_predicted=15
        delete_predictions_with_actuals()
        # Find start day for predictions (=1+last day of actuals)
        cur.execute("SELECT id FROM login_history ORDER BY id DESC")
        latest = cur.fetchone()
        if latest:
            start_year, start_month, start_day = defo.tp_add_x_days_to_id(latest[0], 1)
            predict_demand(start_year, start_month, start_day, num_days_predicted, 1)

    cur.execute("SELECT * FROM login_predictions ORDER BY id ASC")
    pred_data = cur.fetchall()
    if not pred_data:
        print "No predictions in database! Nothing to plot"
        return
    # Get list of days that have been predicted
    pred_dict = {}
    max_pred = 0 # Save max prediction to set identical y axis scales
    for hours in pred_data:
        if hours['num_logins'] > max_pred:
            max_pred = hours['num_logins']
        day_id = hours['id'][:-3]
        if day_id in pred_dict:
            pred_dict[day_id].append(hours)
        else:
            pred_dict[day_id] = [hours]
    for day_id,pred_list in pred_dict.items():
        depl.plot_single_day(pred_list, 'predicted/'+defo.get_year_month_day_str(day_id+'T00'), max_pred)
        
    pred_start = pred_data[0]['id']
    pred_end = pred_data[-1]['id']
    pred_week_start = defo.subtract_one_week(pred_end)
    while pred_week_start > pred_start:
        # Plot predicted weeks
        pred_y = [x['num_logins'] for x in pred_data if x['id']>pred_week_start and x['id']<=pred_end]
        pred_id = [x['id'] for x in pred_data if x['id']>pred_week_start and x['id']<=pred_end]
        if pred_id:
            depl.plot_by_week(x_list=range(-1*len(pred_y),0),y_list=pred_y,id_list=pred_id,
                fix_y=max_pred,savename='predicted/Week_'+pred_end[:10])
        pred_end = pred_week_start
        pred_week_start = defo.subtract_one_week(pred_end)
    
    if pred_end > pred_start: 
        # Print part predicted, part actual
        hist_start = defo.subtract_one_week(pred_end)
        cur.execute("SELECT id, num_logins FROM login_history WHERE id>? ORDER BY id ASC ",(hist_start,))
        hist_data = cur.fetchall()
        if hist_data:
            hist_y = [x['num_logins'] for x in hist_data] # Shouldn't have overlap between actual & predicted
            hist_id = [x['id'] for x in hist_data]
            pred_y = [x['num_logins'] for x in pred_data if x['id']<=pred_end]
            pred_id = [x['id'] for x in pred_data if x['id']<=pred_end]
            plot_y = hist_y+pred_y
            depl.plot_by_week(x_list=range(-1*len(plot_y),0),y_list=plot_y,id_list=hist_id+pred_id,
                fix_y=max_pred,savename='predicted/Week_'+pred_end[:10],split=len(hist_y))
    
def delete_predictions_with_actuals():
    """Finds any predicted hours that have actual data in the login_history table,
    removes matching entries from login_predictions"""
    db = dbh.get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM login_predictions")
    pred_ids = cur.fetchall()
    cur.execute("SELECT id FROM login_history ORDER BY id ASC")
    hist_ids = cur.fetchall()
    if hist_ids:
        all_ids = [x['id'] for x in hist_ids]
        for id in pred_ids:
            if id['id'] in all_ids:
                cur.execute("DELETE FROM login_predictions WHERE id=?",\
                    (id['id'],))
        db.commit()
    
def clear_existing_predictions(year, month, day):
    """Delete all predictions associated with the input day
    from the login_predictions database"""
    if defo.validate_id(defo.get_id_str(year,month,day,0)) is not None:
        db = dbh.get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM login_predictions WHERE id LIKE '",\
            (str(defo.get_id_str(year, month, day, 00))[:-2]+"__'",))
        db.commit()
    else:
        print "Invalid Input to clear_existing_predictions"

def write_predictions_to_csv():
    """Write all predictions to a csv file.
    Convert id to ISO-formatted timestring by appending
    ':00:00' to the id string"""
    predictions = get_predictions()
    if predictions:
        writer = csv.writer(open("predictions.csv", 'w'))
        for row in predictions:
            writer.writerow((row['id']+':00:00',row['num_logins']))
        return None
    else:
        return "No predictions. Try loading data or updating predictions"
    
def mark_outlier(outlier_id, reason='DefaultOutlier'):
    """Add analyzed (manual input) insights to database, marking outliers
    to ignore from predictions"""
    print "Marking outlier: %s" % outlier_id
    # Error check user input
    outlier_id = defo.validate_id(outlier_id)
    if outlier_id is None:
        return "Outlier ID Format Invalid"
    
    db = dbh.get_db()
    cur = db.cursor()
    cur.execute('SELECT * FROM login_history WHERE id=?',(outlier_id,))
    match = cur.fetchone()
    if not match:
        return "ID not in database"
    else:
        print "Outlier Demand=%d"%(match['num_logins'])
        cur.execute('SELECT * FROM history_outliers WHERE id=?',(outlier_id,))
        match = cur.fetchone()
        if match:
            # Replace matching entry in outlier table
            #print 'Updating %s in Outlier DB' % (outlier_id,)
            cur.execute('UPDATE history_outliers SET reason=? WHERE id=?', (str(reason), outlier_id))
        else:
            #print 'Adding %s in Outlier DB' % (str(outlier_id))
            cur.execute('INSERT INTO history_outliers (id, reason) values (?, ?)', (outlier_id, str(reason)))
        db.commit()
    return None

def mark_predicted_outlier(outlier_id, multiplier, reason='DefaultOutlier'):
    """Add analyzed (manual input) insights to database, marking predicted
    future outliers to adjust predictions"""
    # Error check user input
    outlier_id = defo.validate_id(outlier_id)
    if outlier_id is None:
        return "Outlier ID Format Invalid"
    multiplier = float(multiplier)
    print "Marking predicted (future) outlier: %s, with %f multiplier" %(outlier_id,multiplier)
    
    db = dbh.get_db()
    cur = db.cursor()
    cur.execute("INSERT or REPLACE into prediction_outliers (id, multiplier, reason) values (?, ?, ?)",\
            (outlier_id, float(multiplier), reason))
    db.commit()
    return None

def mark_predetermined_outliers():
    """Load known outlier dates to increase accuracy of demand prediction.
    Hardcoded for now...implement as reading in *.json text file"""

    mark_outlier('2012-03-01T00', '#YelpDrinksDC')
    mark_outlier('2012-03-01T02', '#YelpDrinksDC')
    mark_outlier('2012-03-03T03', '#YelpDrinksDC')
    mark_outlier('2012-03-03T04', '#YelpDrinksDC')
    mark_outlier('2012-03-03T05', '#YelpDrinksDC')
    mark_outlier('2012-03-03T06', '#YelpDrinksDC')
    mark_outlier('2012-03-14T04', 'Uber Down')
    mark_outlier('2012-03-14T05', 'Uber Down')
    mark_outlier('2012-03-14T06', 'Uber Down')
    mark_outlier('2012-03-14T07', 'Uber Down')
    mark_outlier('2012-03-14T08', 'Uber Down')
    mark_outlier('2012-04-07T17', 'Easter')
    mark_outlier('2012-04-07T18', 'Easter')
    mark_outlier('2012-04-07T19', 'Easter')
    mark_outlier('2012-04-07T20', 'Easter')
    mark_outlier('2012-04-07T21', 'Easter')
    mark_outlier('2012-04-07T22', 'Easter')
    mark_outlier('2012-04-07T23', 'Easter')
    mark_outlier('2012-04-08T01', 'Easter')
    mark_outlier('2012-04-08T02', 'Easter')
    mark_outlier('2012-04-08T03', 'Easter')
    mark_outlier('2012-04-08T04', 'Easter')
    mark_outlier('2012-04-21T22', 'GWWIB Conference')
    mark_outlier('2012-04-21T23', 'GWWIB Conference')
    mark_outlier('2012-04-22T00', 'GWWIB Conference')
    mark_outlier('2012-04-22T01', 'GWWIB Conference')
    mark_outlier('2012-04-22T02', 'GWWIB Conference')
    mark_outlier('2012-04-22T03', 'GWWIB Conference')
    mark_outlier('2012-04-22T17', 'Earth Day')
    mark_outlier('2012-04-22T18', 'Earth Day')
    mark_outlier('2012-04-22T19', 'Earth Day')
    mark_outlier('2012-04-22T20', 'Earth Day')
    mark_outlier('2012-04-22T21', 'Earth Day')
    mark_outlier('2012-04-22T22', 'Earth Day')    
    mark_outlier('2012-04-25T19', 'Tech Cocktail Session')
    mark_outlier('2012-04-25T20', 'Tech Cocktail Session')
    mark_outlier('2012-04-25T21', 'Tech Cocktail Session')
    mark_outlier('2012-04-25T22', 'Tech Cocktail Session')
    
    for hour in range(12,18+1):
        # Festival in DC is 12 to 6
        mark_predicted_outlier('2012-05-05T'+str(hour), 1.4, 'Cinco de Mayo Festival')
    mark_predicted_outlier('2012-05-05T20', 1.2, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-05T20', 1.4, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-05T21', 1.5, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-05T22', 1.5, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-05T23', 1.4, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-06T00', 1.4, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-06T01', 1.4, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-06T02', 1.4, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-06T03', 1.3, 'Cinco de Mayo')
    mark_predicted_outlier('2012-05-06T04', 1.1, 'Cinco de Mayo')
    
    mark_predicted_outlier('2012-05-13T15', 0.9, 'Mothers Day')
    mark_predicted_outlier('2012-05-13T16', 0.8, 'Mothers Day')
    mark_predicted_outlier('2012-05-13T17', 0.8, 'Mothers Day')
    mark_predicted_outlier('2012-05-13T18', 0.8, 'Mothers Day')
    mark_predicted_outlier('2012-05-13T19', 0.8, 'Mothers Day')
    mark_predicted_outlier('2012-05-13T20', 0.8, 'Mothers Day')
    mark_predicted_outlier('2012-05-13T20', 0.9, 'Mothers Day')
    