#!/usr/bin/env python

import os
from predict_demand import demand_formatter as defo, demand_plotter as depl
import numpy as np

def mad(arr):
    """Median Absolute Deviation - identify the median of the 
    absolute distance from the dataset's median;
    more "robust" version of standard deviation"""
    arr = np.ma.array(arr).compressed() # faster to not use masked arrays.
    med = np.median(arr)
    return np.median(np.abs(arr - med))

def slope_smoothing(pred_slope_list):
    """Smoothes slopes with neighbors (adjacent hours of the same day).
    Optimistic approach to skew trend (slope) positive as demand is increasing
    and any negative slopes (esp with logins so close to 0) are not likely to continue.
    If at a local minimum, take the average of the two surrounding neighbors as the
    smoothed slope for this hour.  
    Otherwise, try to average all 3 neighbors: if a neighbor is negative, check 
    that neighbor's neighbor (2 hours away) and if it is a higher value, use that
    slope instead."""
    pred_slope_smoothed = []
    for idx,sl in enumerate(pred_slope_list):
        #print 'Idx:%d, Slope:%f'%(idx,sl)
        prev_sl = pred_slope_list[idx-1]
        next_sl = pred_slope_list[(idx+1)%len(pred_slope_list)]
        # If at local min, ignore current slope and take average of neighbors
        # Optimistic forecasting, assuming lower slope hour is due to noise/outliers
        if sl < prev_sl and sl < next_sl:
            avg_sl = (prev_sl+next_sl) / 2.0
        else:
            # If neighboring hours have negative slopes, look at next neighbor
            # and use it's slope if it is higher
            if prev_sl < 0.0 and prev_sl < pred_slope_list[idx-2]:
                prev_sl = pred_slope_list[idx-2]
            if next_sl < 0.0 and next_sl < pred_slope_list[(idx+2)%len(pred_slope_list)]:
                next_sl = pred_slope_list[(idx+2)%len(pred_slope_list)]
            avg_sl = (sl+prev_sl+next_sl) / 3.0
        pred_slope_smoothed.append(avg_sl)
    return pred_slope_smoothed

def weighted_mean_calc(weeks, logins):
    """Calculate a weighted mean with exponential favoring towards dates closer
    in time.
    Use weighted mean to set initial xy point to base predictions off of
    Create weights, exponential favoring to dates closer in time; 
    Assumes data is all at least 1 week in the past
    ## For 1-(x^2-1)/150
    # 1 week ago = 1
    # 2 weeks = .98
    # 3 weeks = .947
    # 4 weeks = .9
    # ...
    # 10 weeks = .34
    # 12 weeks = .05
    """
    weights = np.array([max(0.0,1.0-((x*x-1.0)/150.0)) for x in weeks])
    if sum(weights) <= 0.0:
        weighted_mean = np.average(logins) # Don't use weighted mean if weight set sums to zero
    else:
        weighted_mean = np.average(logins, weights=weights)
    return weighted_mean
        
def lin_reg_by_hour(all_data,outlier_data,debug=[]):
    """Group data into same hour and day of week.
    Remove manually tagged outliers (in outlier_data),
    statistically identify other outliers through MAD-based approach and remove,
    run least squares linear regression on remaining valid data,
    calculate weighted mean xy point and save with slope,
    run smoothing algorithm on calculated slopes to average values with neighboring hours (& skew towards positive trend),
    get prediction based on weighted mean and smoothed slope.
    Returns (id_list, predicted_logins, slope_list) tuple of 
    for an entire week (starting with hour immediately after last hour in all_data)"""
    # Remove outliers from data
    if debug: print 'Data size before: %d'%len(all_data)
    outlier_ids = [x['id'] for x in outlier_data]
    all_data = [x for x in all_data if x['id'] not in outlier_ids]
    if debug: print 'Data size after: %d'%len(all_data)
        
    # Get first predicted hour (1 hour past last history entry)
    pred_id = defo.add_x_hours(all_data[-1]['id'],1)
    pred_slope_list = []
    pred_list = []
    pred_point_list = [] # list of tuples (1 xy tuple per slope) so we can recalculate y-intercept after smoothing
    pred_id_list = []
    outlier_count = 0
    negative_slope_count = 0
    
    # Loop over 24 hours for the next 7 days from pred_id
    for dy in range(7):
        cur_day_name = defo.get_day_2char(pred_id)
        for hr in range(24):
            # Get data for this hour
            cur_hour = int(defo.get_hour(pred_id))
            #print "%s Hr %d"%(cur_day_name,cur_hour)
            hour_data = [x for x in all_data if x['day_name']==cur_day_name and x['hour']==cur_hour]
            # Get number of weeks difference with predicted hour
            weeks = [defo.dy_delta_days(x['id'],pred_id)/7 for x in hour_data] # positive values: i.e. [9 8 ... 1]
            logins = [x['num_logins'] for x in hour_data]
            weeks_arr = np.array(weeks)
            logins_arr = np.array(logins)
            
            ## Find and remove MAD based outliers
            hour_mad = mad(logins_arr)
            if hour_mad == 0.0:
                hour_mad = np.std(logins_arr) # Use standard deviation if MAD is zero
            # Indices for data points > -5*MAD and < 5*MAD
            # Additionally exclude all points <= 20% of the median
            med_logins = np.median(logins_arr)
            low_mad_idx = logins_arr > max(med_logins - (4*hour_mad), 0.20*med_logins)
            high_mad_idx = logins_arr < med_logins + (4*hour_mad)
            logins_mad_idx = low_mad_idx & high_mad_idx
            if logins_mad_idx == []:
                logins_mad_idx = abs(logins_arr-weighted_mean) < 5*hour_mad
                print 'WARNING: No points within MAD threshold! Increasing tolerance'
            for is_valid in logins_mad_idx:
                if not is_valid:
                    outlier_count = outlier_count + 1
                    
            # Least squares linear regression
            A = np.array([ -1*weeks_arr[logins_mad_idx], np.ones(weeks_arr[logins_mad_idx].size)])
            lst_sq_pt = np.linalg.lstsq(A.T,logins_arr[logins_mad_idx])[0]
            
            # Weighted mean calculation for baseline xy point (used with smoothed slope)
            weighted_mean = weighted_mean_calc(weeks_arr[logins_mad_idx],logins_arr[logins_mad_idx])
            weighted_mean_x = (weighted_mean - lst_sq_pt[1])/lst_sq_pt[0] # Solve for x position
            weighted_mean_x = min(-1.0,max(-1.0*(np.amax(weeks_arr[logins_mad_idx])),weighted_mean_x))# Bound x to be a possible week
            pred_point_list.append((weighted_mean_x,weighted_mean))
            pred_slope_list.append(lst_sq_pt[0])
            pred_id_list.append(pred_id)
            pred_id = defo.add_x_hours(pred_id,1)
            if lst_sq_pt[0] < 0.0:
                negative_slope_count = negative_slope_count+1
            if debug: 
                print "Predicting %s%d: %f Median %f Mean, %f MAD"%(cur_day_name,cur_hour,med_logins,weighted_mean,hour_mad)
                print logins_arr
                print logins_arr[logins_mad_idx]
                print "  %fx+%f"%(lst_sq_pt[0],lst_sq_pt[1])
            
    # 2-pass optimistic smoothing
    # Smooth slope line with neighboring hours (before/after current hour)
    if debug:
        orig_slope_list = pred_slope_list
    pred_slope_list = slope_smoothing(pred_slope_list)
    pred_slope_list = slope_smoothing(pred_slope_list)
    
    # Recalculate y-intercept (prediction) based on smoothed slope and weighted mean xy point
    for idx,xy in enumerate(pred_point_list):
        pred_list.append(max(0.0, xy[1]+(0.0 - xy[0])*pred_slope_list[idx]))
        if debug: 
            print '%s: Mean (%f,%f), %f Prediction (%f->Smoothed->%f)'%(pred_id_list[idx],
                xy[0],xy[1],pred_list[-1],orig_slope_list[idx],pred_slope_list[idx])
    if debug:
        print 'Outlier count: %d, negative slope: %d'%(outlier_count,negative_slope_count)
        
    return (pred_id_list, pred_list, pred_slope_list)
    