#!/usr/bin/env python

import os
import re
import calendar
import datetime

# Format of the id's stored in the database (i.e. 2012-03-01T23)
DATETIME_ID_FORMAT = '%Y-%m-%dT%H'
# Format of the login times read in through *.json files
JSON_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

def datetimes_to_dict(login_data):
    """Takes the client login json data, which is of the format:
    [u'2012-04-30T23:59:29+00:00',...]
    and group login times by hour:
    where each hour contains a list of all the logins
    {
        '2012-04-30T23': ['2012-04-30T23:59:29+00:00','2012-04-30T23:59:49+00:00']
        ...
    }"""
    binned_data = {}
    for time in login_data:
        try:
            # Ignore timezone information for now
            login_dt = datetime.datetime.strptime(time[0:19], JSON_DATETIME_FORMAT)
            dt_id = login_dt.strftime(DATETIME_ID_FORMAT)
            if dt_id in binned_data:
                binned_data[dt_id].append(dt_id)
            else:
                binned_data[dt_id] = [dt_id]
                
        except ValueError, e:
            print "Skipping unhandled datetime"
            print e
    return binned_data

def validate_login_string(client_login_id):
    """Takes a client login id, which is of the format:
    2012-04-30T23:59:29
    and returns the associated id which can be stored in the database, formatted:
    2012-04-30T23
    Tries the database format, if no format matches returns None"""
    client_login_id = str(client_login_id)
    try:
        if len(client_login_id) < 19:
            # Try 2012-04-30T23 format
                login_dt = datetime.datetime.strptime(client_login_id, DATETIME_ID_FORMAT)
                if login_dt:
                    return login_dt.strftime(DATETIME_ID_FORMAT)
        else:
            login_dt = datetime.datetime.strptime(client_login_id[0:19], JSON_DATETIME_FORMAT)
            if login_dt:
                return login_dt.strftime(DATETIME_ID_FORMAT)
        return None
    except:
        return None
    
def add_month(year, month):
    """Returns a new dictionary object to represent a month,
    the input is datetime class."""
    month_dict = {}
    #num_days = calendar.monthrange(add_datetime.year,add_datetime.month)[1]
    num_days = calendar.monthrange(year,month)[1]
    for d in range(1,num_days+1):
        month_dict[d] = get_hours_dict()
    return month_dict

def get_hours_dict():
    """Returns a dictionary of 24 hours"""
    return {0:[],1:[],2:[],3:[],4:[],5:[],6:[],7:[],8:[],9:[],10:[],11:[],
            12:[],13:[],14:[],15:[],16:[],17:[],18:[],19:[],20:[],21:[],22:[],23:[]}
    
def get_day_num(dt_id):
    """Returns the weekday as a number for this id"""
    dt = datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT)
    return dt.strftime('%u')

def get_hour(dt_id):
    """Returns the hour of day for this id"""
    dt = datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT)
    return dt.strftime('%H')
    
def get_year(dt_id):
    """Returns the year for this id"""
    dt = datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT)
    return dt.strftime('%Y')

def matching_day_hour(day_num, hour, match_id):
    """Returns true if the day_num (1-7) and hour (0-23)
    matches the match_id, false otherwise"""
    if get_day_num(match_id) == day_num and get_hour(match_id) == hour:
        return True
    else:
        return False

def get_day_2char(id_str):
    """Returns the 2 letter representation of this day of the week"""
    dt_id = datetime.datetime.strptime(str(id_str), DATETIME_ID_FORMAT)
    return get_day_str(dt_id.year,dt_id.month,dt_id.day)
    
def get_day_str(year, month, day):
    """Returns the 2 letter representation of this day of the week"""
    num_chars = 2
    week_hdr = calendar.weekheader(num_chars)
    day_idx = calendar.weekday(int(year), int(month), int(day))
    return week_hdr[day_idx*(num_chars+1) : day_idx*(num_chars+1) + num_chars]

def get_id_str(year, month, day, hour):
    """Converts the given year/month/day/hours into a string of the format:
    yyyy-mm-ddThh where
    yyyy is the year
    mm is the month (from 1 to 12)
    dd is the date (from 1 to 31)
    hh is the hour (from 0 to 23)"""
    dt = datetime.datetime(year,month,day,hour,0,0)
    return dt.strftime(DATETIME_ID_FORMAT)

def get_later_day(datetime1, year2, month2, day2):
    """Returns the id associated with the later year/month/day
    Note: ingores hours (sets the output hours field to 0)"""
    #dt1 = datetime.datetime(year1,month1,day1,0,0)
    dt1 = datetime.datetime.strptime(str(datetime1)[0:11]+'00', DATETIME_ID_FORMAT)
    dt2 = datetime.datetime(year2,month2,day2,0,0)
    if dt2 > dt1:
        return dt2.strftime(DATETIME_ID_FORMAT)
    else:
        return dt1.strftime(DATETIME_ID_FORMAT)

def get_week_str(starting_at_id):
    """Returns a list of 2 letter representation of days for this week,
    starting at the given input day of the form yyymmddhh"""
    num_chars = 2
    week_hdr = calendar.weekheader(num_chars)
    strt_dt = datetime.datetime.strptime(str(starting_at_id), DATETIME_ID_FORMAT)
    strt_idx = calendar.weekday(strt_dt.year,strt_dt.month,strt_dt.day)
    day_list = []
    for d in range(7):
        day_idx = (strt_idx + d) % 7
        day_list.append(week_hdr[day_idx*(num_chars+1) : day_idx*(num_chars+1) + num_chars])
    return day_list

def is_nonzero_dt(dt_id):
    """Returns true if datetime id is not year 0, month 0, and day 0"""
    dt = datetime.datetime.strptime(str(starting_at_id), DATETIME_ID_FORMAT)
    if dt.year > 0 or dt.month > 0 or dt.day > 0:
        return True
    else:
        return False

def add_x_hours(starting_at_id, num_hours):
    """Returns an id that is num_hours from the given input id"""
    new_hour = (datetime.datetime.strptime(str(starting_at_id), DATETIME_ID_FORMAT) + \
                datetime.timedelta(hours=num_hours))
    return new_hour.strftime(DATETIME_ID_FORMAT)
    
def subtract_one_week(starting_at_id):
    """Returns an id exactly 1 week before the given input id"""
    new_dt = datetime.datetime.strptime(str(starting_at_id), DATETIME_ID_FORMAT) - datetime.timedelta(days=7)
    return new_dt.strftime(DATETIME_ID_FORMAT)

def add_one_week(starting_at_id):
    """Returns an id exactly 1 week after the given input id"""
    new_dt = datetime.datetime.strptime(str(starting_at_id), DATETIME_ID_FORMAT) + datetime.timedelta(days=7)
    return new_dt.strftime(DATETIME_ID_FORMAT)

def tp_add_x_days_to_id(dt_id, days_to_add):
    """Returns (later_year,later_month,later_day) where later_* is
    days_to_add # of days after the input datetime id"""
    later_day = (datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT) + \
                 datetime.timedelta(days=days_to_add))
    return (later_day.year, later_day.month, later_day.day)

def tp_add_x_days(year, month, day, days_to_add):
    """Returns (later_year,later_month,later_day) where later_* is
    days_to_add # of days after the input year, month, day"""
    later_day = datetime.date(year,month,day) + datetime.timedelta(days=days_to_add)
    return (later_day.year, later_day.month, later_day.day)
    
def hr_subtract_ids(id_hi, id_lo):
    """Returns difference in hours between the two ids"""
    delta = datetime.datetime.strptime(str(id_hi), DATETIME_ID_FORMAT) - datetime.datetime.strptime(str(id_lo), DATETIME_ID_FORMAT)
    return delta.total_seconds() / 3600

def dy_delta_days(start_id, end_id):
    """Returns the number of days from start_id to end_id,
    returns positive value,
    overwrites hours portion of ids (difference in days only)"""
    start_id = str(start_id)[0:11]+'00'
    end_id = str(end_id)[0:11]+'00'
    start_day = datetime.datetime.strptime(start_id, DATETIME_ID_FORMAT)
    end_day = datetime.datetime.strptime(end_id, DATETIME_ID_FORMAT)
    return (end_day - start_day).days

def dy_subtract_ids(id_hi, id_lo):
    """Returns difference in calendar days between the two ids:
    return # days = yyyy-mm-ddTxx (id_hi) - yyyy-mm-ddTxx (id_lo)
    where xx is Don't Care"""
    day_hi = datetime.datetime.strptime(str(id_hi)[0:11]+'00', DATETIME_ID_FORMAT)
    day_lo = datetime.datetime.strptime(str(id_lo)[0:11]+'00', DATETIME_ID_FORMAT)
    return (day_hi - day_lo).days
    
def get_day_of_year(dt_id):
    """Returns the day of year, from 001 to 366"""
    dt = datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT)
    return dt.strftime('%j')

def get_year_month_day_str(dt_id):
    """Returns the a string (format: yyyy_mm_dd) of dt_id
    ie. 2012_03_10"""
    dt = datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT)
    return dt.strftime('%Y_%m_%e')
    
def get_day_of_week(dt_id):
    """Returns the full day of year i.e. Tuesday"""
    dt = datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT)
    return dt.strftime('%u_%A')

def month_day_year_from_id(id_int):
    """Given id (yyyymmddhh), returns a pretty string of the date.
    i.e. month_day_year_from_id(2012031200) returns 'Mon March 3, 2012'"""
    dt = datetime.datetime.strptime(str(id_int), DATETIME_ID_FORMAT)
    return dt.strftime('%a %B %e, %Y')

def get_week_of_year(dt_id):
    """Returns the week number within the year (1-53)"""
    dt = datetime.datetime.strptime(str(dt_id), DATETIME_ID_FORMAT)
    return dt.strftime('%W')
    
def day_hour_from_id(id_int):
    """Given id (yyyymmddhh), returns a pretty string of the date.
    i.e. day_hour_from_id(2012031211) returns '3/12, 11am'"""
    dt = datetime.datetime.strptime(str(id_int), DATETIME_ID_FORMAT)
    return dt.strftime('%m/%d, %I%p')

def xtick_week_str(starting_at_id):
    """Returns a list for the x-axis labeling for plotting a week"""
    num_chars = 2
    hour_inc = 6 #broken into 6 hour increments
    week_hdr = calendar.weekheader(num_chars)
    start_dt = datetime.datetime.strptime(str(starting_at_id), DATETIME_ID_FORMAT)
    strt_idx = calendar.weekday(start_dt.year,start_dt.month,start_dt.day)
    # hour of starting_at_id sets the first element
    strt_hour = start_dt.hour
    day_list = []
    d = 0
    for x in range(7*hour_inc):
        hour = (strt_hour + x*hour_inc) % 24
        # Append name of day near noon
        if abs(hour - 12) <= 3: # if first element is 3, both 9 and 12 will be the day...
            day_idx = (strt_idx + d) % 7
            day_list.append(week_hdr[day_idx*(num_chars+1) : day_idx*(num_chars+1) + num_chars])
            if hour != 9:
                d = d + 1
        # Append time of day
        else:
            day_list.append(str(hour))
    return day_list

def validate_id(check_id):
    """Returns None if id is not the correct format"""
    # TBD: add conversion to correct id
    try:
        dt = datetime.datetime.strptime(str(check_id)[0:13], DATETIME_ID_FORMAT)
        return dt.strftime(DATETIME_ID_FORMAT)
    except:
        print "Input ID invalid"
        return None
    