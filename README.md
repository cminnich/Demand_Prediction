Demand_Prediction
=================

Predicts future demand based on historical data

 - Input timestamp data
  - Within example dataset, each timestamp represents a client login
 - Analyze historical demand data through various visualizations and plots
 - Predicts the future demand (# of logins per hour)

This project was implemented with Python, Flask, and SQLite3.  I analyzed a dataset from Uber that represents all the client login attempts from March 1st to May 1st, 2012 in the Washington DC area.

#Analysis
I found that the data exhibited a strong weekly seasonality pattern.  To take advantage of this, I structured my database so that I could easily organize data by day of the week and hour of the day.

The following code, taken from demand\_main.py, is an example of some analysis that I performed on the data.  It illustrates how I utilized the schema design to easily access, manipulate, and visualize the data.  
I first grab the entire login history from the database (manageable size of example dataset does not impose memory constraints here) and save this to all\_data  
```python
    cur.execute('SELECT * FROM login_history ORDER BY id ASC')
    all_data = cur.fetchall()
```
To look at just the data from Wednesday (stored in database using 'We' abbreviation) specifically, the following line filters and reshapes the data to a dictionary format that is grouped by hour.
```python
    map(lambda y: we_dict[y['hour']].append((y['id'],y['num_logins'])), \
        filter(lambda x: x['day_name']=='We', all_data))
```
I then use my plotting function within demand\_plotter.py (renamed to depl) to save the box-and-whisker plot for all data from Wednesday.
```python
    depl.plot_day_dict(we_dict, '3_Wednesday', max_login)
```
The following Box-and-whisker plots visually highlight the significant differences in demand that could be expected between a Wednesday and a Saturday.
 - Red line at median
 - Box shows quartiles
 - Whiskers show the entire range, with pluses as outliers
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/days/ByHour_3_Wednesday.png "Wednesday data by hour")
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/days/ByHour_6_Saturday.png "Saturday data by hour")

This scatter plot shows one week's worth of data, where I programmatically relabel the x-axis ticks and automatically find and annotate the peak hour of demand in the week. 
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/weeks/2012_03_19.png "Week ending on March 19, 2012")

##Outliers
I built in the ability to manually tag outliers, so they could be excluded from skewing the predictions.  I identified and tagged a variety of outlier data points whose extreme (high or low) demand could be attributed to a justifiable reason.  One specific example from the dataset I analyzed: there is no data from 4am to 8am on March 14, which was due to Uber pushing out an app update with the [surge pricing feature](https://blog.uber.com/2012/03/14/clear-and-straight-forward-surge-pricing/).

Associated with each outlier is a tag field.  This short description acts to save a known reasoning for the outlier, as well as provides a way to group and associate outliers.  I imagine a potentially valuable use of these outliers is to help determine the extent to which certain outliers increased (or decreased) demand, and use this information to help bias predicted demand instead of simply excluding the tagged outlier data.  For example, by tagging all hours that were impacted by Yelp promotions (i.e. with a "Yelp" tag), we can get measure the extent to which these promotions impacted demand, as well as help predict how future Yelp promotions might increase demand.  
- [x] Tag outliers  
- [x] Exclude outliers from prediction  
- [ ] Analyze specific tags  
- [ ] Influence prediction based on matching tags

##Prediction Approach
Historic Login data grouped by days of the week (Mon, Tues, etc.) and hours of the day (0-23). Algorithm applies the following steps to each hour (i.e. Friday at 4)  

1. Utilize user-curated outlier data by removing them from the prediction dataset
2. Statistical identification and removal of outliers
  * Using Median Absolute Deviation (more robust than standard deviation) to set tolerance window for valid data
  * Outlier if more than 5*MAD from median
  * Outlier if less than 20% of median
3. Least Squares Linear Regression on remaining valid history data (where the # of delta weeks is the x-axis, and # of logins is the y-axis)
  * Produces a slope, or trend in the data over weeks
4. Weighted Mean computation to calculate and save a xy point
  * XY Point used as “pivot” in step 7: prediction is calculated using the smoothed slope from this xy point
  * Exponential weighting biases mean towards data closer to the present
5. 2-Pass Smoothing of slopes of neighboring hours – using an “optimistic” approach
  * Optimistic approach emphasizes positive trend in data (i.e. tend towards increase in demand)
  * See below for details
6. Use smoothed slope and weighted mean xy point to calculate prediction
7. Possibly apply "Future Outlier" multiplier to result
  * User can specify a multiplier for hours that are expected to have increased demand
    * i.e. Cinco de Mayo might have a 1.5x multiplier on demand at 11pm

One major problem with this simple linear regression technique is that it is highly sensitive to noise, and predicts a decrease in demand (negative slope) for some chunks of hours that have relatively little demand.  Particularly because this dataset is for Washington D.C. not too long after Uber was launched in the city (and had relatively sparse demand), we really don't expect the demand to decrease.  The following plot shows the calculated slope - representing the predicted change to demand on future weeks for a given hour and day of the week.
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/Predicted_Slopes_0pass.png "Linear Regression, No Smoothing")

To address this, I implemented an "Optimistic Smoothing" algorithm. It performs 2 passes of this smoothing technique on the slopes generated through linear regression.  Conceptually, the smoothing allows the trend (or slope) exhibited by neighboring hours to be factored into the expected trend at the current hour. It optimistically emphasizes positive trends in the data, by not doing a simple average of the current and before/after (neighboring) hours under the following conditions:  
  * If current slope is local min, exclude current slope from average (only use neighbors)
  * If neighbor slope is negative, use the slope 2 hours away (if it is greater than neighbor)

Visually, we can see the difference this Optimistic Smoothing produces on the slope trends.  This plot shows the calculated slope after applying the 2-Pass Optimistic Smoothing.  Note that there are no longer any negative slopes (predicted decrease in demand).
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/Predicted_Slopes.png "After 2-Pass Optimistic Smoothing")

##Predictions
The following plots show the first 8 days worth of predicted number of logins.  The green datapoints are the actuals, and the blue datapoints are the predictions.  
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/predicted/Week_2012-05-01.png "6 days (Actuals) & 1 day (Predicted)")
This week includes a future predicted outlier, Cinco De Mayo.  I predicted a 1.5x multiplier for a specific chunk of hours on this day.  
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/predicted/Week_2012-05-08.png "7 days (Predicted)")

#Usage
Interact through command line REST API or web interface as detailed below.

Start a local server instance (running on Port 5000 in the following examples) by running the following command from the top level directory  
`python runserver.py`

##REST API - POST Demand History
Use the POST request to add Client Login Timestamp Data.  
Timestamps must be ISO-formatted, i.e. the form  
**2012−05−01T00:00:00**
######Resource URL:  
`http://localhost:5000/api/demand`

Insert a list of client logins within a JSON object:  
`curl -i -H "Content-Type: application/json" -X POST -d @uber_demand_prediction_challenge.json http://localhost:5000/api/demand`

Insert a single client login timestamp datapoint using 'timestamp':  
`curl -i -H "Content-Type: application/json" -X POST -d '{"timestamp":"2012-03-01T00:05:55+00:00"}' http://localhost:5000/api/demand`

Insert a list of client logins using 'timestamps':  
`curl -i -H "Content-Type: application/json" -X POST -d '{"timestamps":["2012-03-01T00:05:55+00:00", "2012-03-01T00:06:23+00:00","2012-03-01T00:06:55+00:00"]}' http://localhost:5000/api/demand`

Along with the appropriate HTTP Status Code response, returns an additional json status from the POST with:
- error details will be specified if the input is invalid (within an 'error' key, whose value can specify more details)
- "timestamp" key will have list of hours that were affected (or just a single hour)
- if the affected hour already exists in the database, the "update" key will hold the count of the appended entries
- if a new hour record was created, the "insert" key will hold the count of the new entries

Example response for inserting 1 timestamp when that hour already exists within the database, includes 201 CREATED HTTP status code to indicate a successful creation along with each timestamp inserted and count of 1 hour that was "updated":  
```
HTTP/1.0 201 CREATED
Content-Type: application/json
Content-Length: 62
Server: Werkzeug/0.9.6 Python/2.7.7
Date: Tue, 26 Aug 2014 03:44:30 GMT

{
  "timestamp": "2012-03-01T00:05:55+00:00", 
  "update": 1
}
```

##REST API - PUT Update Predictions Based on History
Use the PUT request to update the Predictions. Number of logins predicted per hour for days in the future.  
Predictions start on the day immediately following the latest historical datapoint.  Additionally clears out old predictions (when there is actual data for that day) and loads in the predetermined outliers.  Will return identical response (besides HTTP Status Code) as corresponding GET request.  
######Resource URL:  
`http://localhost:5000/api/predict`

By default, will predict forward 15 days:  
`curl -i -X PUT http://localhost:5000/api/demand`

To predict a specific number of days (i.e. 3 days):  
`curl -i -X PUT http://localhost:5000/api/demand/3`

Along with the appropriate HTTP Status Code response, returns the json prediction of each hour that was updated to the database.  
Example response for updating 1 day's predictions, includes 201 CREATED HTTP status code to indicate a successful update along with each hour and predicted number of logins:  
```
HTTP/1.0 201 CREATED
Content-Type: application/json
Content-Length: 957
Server: Werkzeug/0.9.6 Python/2.7.7
Date: Mon, 01 Sep 2014 22:35:10 GMT

{
  "2012-05-01T00": 18.566893281115636, 
  "2012-05-01T01": 21.83782416617116, 
  ...
  "2012-05-01T22": 22.846377369169147, 
  "2012-05-01T23": 23.125764596138033
}
```

##REST API - GET Demand Predictions
Use the GET request to get Client Login Predictions currently in the database.  
######Resource URL:  
`http://localhost:5000/api/predict`

By default, will return all predictions in the database:  
`curl -i http://localhost:5000/api/predict`

To get a specific number of days (i.e. 3 days of predictions):  
`curl -i http://localhost:5000/api/predict/3`

Along with the appropriate HTTP Status Code response, returns the json prediction of each hour and the corresponding predicted number of logins.  

##Web Interface
Using the lightweight Flask framework, I built a simple web interface with more functionality than offered through the command line API.  

![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/WebInterface.png "Web Interface")

Without logging in, the currently loaded historical data and future predictions will be displayed.  

After logging in (username: 'user', password: 'predict'), the following additional administrative functionality is available:
- Read client login data to update the database by either creating a new hour entry, or appends (+1 count) to an existing hour entry in the database
  - From local *.json files
  - From specified individual ISO timestamp
- Load Outlier Data
  - Predetermined hours (hardcoded) for explainable data points to remove
  - Manually enter timestamp of hour with reasoning tag
- Generate Plots: saved locally within project directory
- Update Predictions: for the next 15 days worth of data from the latest datapoint
- Write Predictions to CSV file
- Clear Database (reinitialize everything)
