#!/usr/bin/env python

import os
import matplotlib.pyplot as plt
import numpy as np
import datetime
from predict_demand import demand_formatter as defo

def scatter_plot(x_list, y_list, save_name='Hour_Analysis', \
    x_label='Hour', y_label='Login Count [per hour]', id_str=None):
    """Given a list of hours and list of client login counts,
    plots the time vs. count data"""
    fig = plt.figure()
    if id_str is not None: #len(y_list) == 24*7
        fig.add_subplot(111, autoscale_on=False, xlim=(-1,24*7+1), ylim=(min(y_list)-.5,max(y_list)+.5))
    plt.plot(x_list, y_list)
    plt.scatter(x_list, y_list)
    plt.ylabel(y_label)
    plt.xlabel(x_label)
    plt.grid()
    if id_str is not None: #len(y_list) == 24*7
        #use get_week_str
        day_list = defo.xtick_week_str(id_str)
        plt.xticks( range(0,24*7,6), day_list, fontsize = 7 )
        plt.xlabel('Time')
    save(save_name)
    plt.close()

def plot_by_day(day_dict):
    """Given a dictionary where the key is day of year,
    and the value is the client login count for that entire day,
    plots the time vs. count data"""
    x_list = []
    y_list = []
    for key in sorted(day_dict):
        x_list.append(key)
        y_list.append(day_dict[key])
    
    plt.figure()
    plt.plot(x_list, y_list)
    plt.ylabel('Login Count [per day]')
    plt.xlabel('Day of year')
    save('Day_Analysis')
    plt.close()

def plot_by_week(x_list, y_list, id_list, fix_y=None, predicted_color=None, \
                 savename=None, split=None):
    """Given a list of hours and list of client login counts,
    plots the time vs. count data and uses the id_list for
    formatting x tick labels and saving correctly"""
    fig = plt.figure()
    if fix_y is None:
        fix_y = max(y_list)+3
    ax = fig.add_subplot(111, autoscale_on=False, xlim=(-25*7,8), ylim=(-3,fix_y+8))
    if split is not None:
        ax.scatter(x_list[:split], y_list[:split], color='green')
        ax.scatter(x_list[split:], y_list[split:], color='blue')
    else:
        if predicted_color is None:
            scatter_color = 'green'
        else:
            scatter_color = 'blue'
        ax.scatter(x_list, y_list, color=scatter_color)
    # Label high peak
    peak_idx = y_list.index(max(y_list))
    ax.annotate(defo.day_hour_from_id(id_list[peak_idx]), 
                xy=(x_list[peak_idx]+.5, y_list[peak_idx]+.5),
                xytext=(x_list[peak_idx]+10, y_list[peak_idx]+3),
                arrowprops=dict(facecolor='black', shrink=0.01))
    plot_title = defo.month_day_year_from_id(id_list[-1])
    plt.title('Week ending on '+plot_title)
    plt.ylabel('Login Count [per hour]')
    # Only do x tick relabeling when there's a complete week
    if len(id_list) == 24*7:
        #use get_week_str
        #plt.xticks( range(-24*7,1,24), [day_list[-1]]+day_list )
        day_list = defo.xtick_week_str(id_list[0])
        plt.xticks( range(-24*7,1,6), day_list, fontsize = 7 )
        plt.xlabel('Time')
    else:
        print "In plot by week, size: %d"%(len(id_list))
        print id_list[0] + ' to ' + id_list[-1]
        plt.xticks( range(-24*7,1,12) ) # Every 12 hours for readability
        plt.xlabel('Hours')
    plt.grid()
    if savename is None:
        save('weeks/'+defo.get_year_month_day_str(id_list[-1]))
    else:
        save(savename)
    plt.close(fig)

def plot_by_hour(x_list, y_list, id_list):
    """Given the data for a given hour/day and a list of client login counts,
    plots the week vs. count data and uses the id_list for
    formatting x tick labels and saving correctly"""
    plt.figure()
    plt.scatter(x_list, y_list)
    plt.ylabel('Login Count [per hour]')
    plt.xlabel('Time')
    if len(id_list) == 24*7: # only do x tick relabeling when there's a complete week
        day_list = defo.get_week_str(id_list[0])
        plt.xticks( range(-24*7,1,24), [day_list[-1]]+day_list )
    save('weeks/'+str(id_list[-1])[:-2])
    plt.close()

def plot_each_day(all_data):
    """Given the entire history database, plot each day separately and
    save as a new image file"""
    max_pred = 0 # Save max prediction to set identical y axis scales
    day_dict = {}
    for hours in all_data:
        if hours['num_logins'] > max_pred:
            max_pred = hours['num_logins']
        day_id = hours['id'][:-3]
        if day_id in day_dict:
            day_dict[day_id].append(hours)
        else:
            day_dict[day_id] = [hours]
    for day_id,day_list in day_dict.items():
        plot_single_day(day_list, 'days/'+defo.get_year_month_day_str(day_id+'T00'), max_pred)

def plot_single_day(id_cnt_list, savename, ymax=None):
    """Given a list of tuples (id, cnt) for a 24 hours,
    plots the hour vs. count data"""
    predictions = [x['num_logins'] for x in id_cnt_list]
    ids = [x['id'] for x in id_cnt_list]
    hours = [int(defo.get_hour(x)) for x in ids]
    fig = plt.figure()
    if ymax is not None:
        ax = fig.add_subplot(111, autoscale_on=False, xlim=(-.5,23.5), ylim=(-.5,ymax+5))
    plt.plot(hours, predictions)
    plt.ylabel('Login Count [per hour]')
    plt.xlabel('Hour')
    plt.title(defo.month_day_year_from_id(ids[-1]))
    plt.grid()
    plt.xticks( range(24) )
    save(savename)
    plt.close()

def plot_day_dict(day_dict, day_str, fix_y=None, enable_scatter=False):
    """Given input data for a single day in the form of a dictionary, where 
    the keys are hours (0 to 23) and
    the values are lists of login counts per hour,
    scatter plots the values and creates a summary box plot on top"""
    fig = plt.figure()
    if fix_y is not None:
        ax = fig.add_subplot(111, autoscale_on=False, xlim=(-1,24), ylim=(-1,fix_y+2))
    else:
        ax = fig.add_subplot(111)
    plot_data = []
    for hour in sorted(day_dict.keys()):
        vals = [ entry[1] for entry in day_dict[hour] ]
        plot_data.append(vals)
        if enable_scatter:
            ax.scatter([hour]*len(vals), vals)
    ax.boxplot(plot_data, positions=sorted(day_dict.keys()))
    # Add a horizontal grid to the plot, but make it very light in color
    # so we can use it for reading data values but not be distracting
    ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
                  alpha=0.5)
    # Hide these grid behind plot objects
    ax.set_axisbelow(True)
    ax.set_title("{}'s distribution of logins by hour".format(day_str))
    plt.ylabel('Login Count [per hour]')
    plt.xlabel('Hour of Day')
    save('days/ByHour_'+day_str)
    plt.close(fig)

def prediction_analysis(year, month, day, hour, history):
    """Given a date to predict, and the past history of client login data,
    plot the normalized (by mean) drift over time for the given hour"""
    plt.figure()
    plt.close()
    
def correlation(x_list, y_list, title):
    """Perform correlation between different weeks"""
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    ax1.xcorr(x_list, y_list, usevlines=True, maxlags=75, normed=True, lw=2) #
    ax1.grid(True)
    #ax1.axhline(0, color='black', lw=2)
    save(title)
    plt.close(fig)

def plot_day_trend(predicted_id, hist_day):
    """Given a date to predict, and the past history of client login data,
    plot the normalized (by mean) drift over time for each hour of the given day.
    Group the box plots by week, where the datapoints for each box/week consist
    of all 24 hours (difference from corresponding hour's mean).
    An increase in the mean over time/weeks (x axis), shows the amount of demand
    increase over time (broken down by day, normalized by mean of each individual hour)."""
    fig = plt.figure()
    ax = fig.add_subplot(111)
    # Limit number of weeks back in time to 11 (data must be within last 11 weeks)
    limit_past = 11 # [weeks]
    max_week_idx = None
    min_week_idx = None
    week_arr = np.empty((limit_past,24)) # 11 (max) arrays of 24 [hours]
    for hour in range(24):
        hist_hour = filter(lambda x: x['hour']==hour and defo.dy_delta_days(x['id'],predicted_id)/7 < limit_past, hist_day)
        delta_weeks = map(lambda x: defo.dy_delta_days(x['id'],predicted_id)/7, hist_hour)
        if max_week_idx is None:
            # Assuming history has sequential weeks
            max_week_idx = max(delta_weeks)
            min_week_idx = min(delta_weeks)
        login_list = map(lambda x: x['num_logins'], hist_hour)
        x_arr = np.array(delta_weeks)
        y_arr = np.array(login_list)
        mean_y = np.mean(y_arr)
        #ax.plot(x_arr, (y_arr-mean_y)/mean_y)
        for wk,cnt in zip(x_arr,y_arr):
            week_arr[wk][hour] = (cnt-mean_y)/mean_y
    #boxplot_arr = np.array(max_week_idx-min_week_idx,24)
    boxplot_arr = []
    wk_rng = range(max_week_idx,min_week_idx-1,-1)
    x_lbl = []
    for wk in wk_rng:
        boxplot_arr.append(week_arr[wk])
    ax.boxplot(boxplot_arr)
    #ax.boxplot(week_arr[min_week_idx:max_week_idx])
    # TBD - use weights for known outliers
    #weights_arr = np.ones(y_arr.shape)
    day_str = defo.get_day_of_week(predicted_id)
    ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
                  alpha=0.5)
    ax.set_title(day_str)
    plt.ylabel('(Delta from Mean)/Mean')
    plt.xlabel('Past Weeks [---> Present]')
    save('days/ByWeek_'+day_str)
    plt.close(fig)
    
def plot_weekdays(wkday_data):
    """Given all the weekday data (Mon->Thurs), 
    saves a boxplot binned by hours"""
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plot_data = []
    for hour in range(24):
        hour_data = map(lambda x: x[1], filter(lambda x: int(defo.get_hour(x[0]))==hour, wkday_data))
        plot_data.append(hour_data)
    ax.boxplot(plot_data)
    # Add a horizontal grid to the plot, but make it very light in color
    # so we can use it for reading data values but not be distracting
    ax.yaxis.grid(True, linestyle='-', which='major', color='lightgrey',
                  alpha=0.5)
    # Hide these grid behind plot objects
    ax.set_axisbelow(True)
    ax.set_title("Weekday [Mon-Thurs] distribution of logins by hour")
    plt.ylabel('Login Count [per hour]')
    plt.xlabel('Hour of Day')
    save('WeekdayHour')
    plt.close(fig)

def linear_regression_plot(xi, line, data, prediction, pred_id):
    """Plots the best fit linear regression line and data points
    for this time prediction"""
    plt.figure()
    plt.plot(xi, line, 'r-', xi, data,'o', 0, prediction, '*')
    plt.xlim((min(xi),1))
    plt.xlabel('# Weeks from Prediction')
    plt.title('Linear regression for '+defo.day_hour_from_id(pred_id))
    save('day_predict/'+pred_id)
    plt.close()
    
def save(name, ext='png'):
    """Save pyplot figure to top level Plots folder."""
    # If the directory does not exist, create it
    directory = 'plots'
    dirpath,filename = os.path.split(os.path.join(directory, name))
    if filename:
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        # Save figure to the current directory
        savepath = os.path.join(dirpath, filename)
        # Actually save the figure
        plt.savefig(savepath)
    else:
        print 'WARNING: Invalid input in saving '+name