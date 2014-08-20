Demand_Prediction
=================

Predicts future demand based on historical data.  Given JSON formatted timestamps (where each timestamp represents a client login datapoint), predicts the number of logins per hour for future days.  This project was implemented with Python, Flask, and SQLite3.  

My approach was to build a framework for inputting, analyzing, visualizing, and predicting demand.  Users can interact through either a Command-Line RESTful API, or Web interface.  Analyzing the data through relevant plots was an integral step in formulating the prediction algorithm, but is not available to users through the REST API.

#Analysis
One goal I had with the analysis was to explore the data programmatically.  Meaning, I wanted to codify my data exploration and plots so that they might apply to different data sets as well.  
I found that the data exhibited strong weekly seasonality (7-day autoregression).  These box-and-whisker plots highlight the degree to which the data can be grouped by matching days of the week and hours of the day (i.e. Friday at 8 am).
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/days/ByHour_5_Friday.png "All Friday data, by hour")

##Outliers
I built in the ability to manually tag outliers, so they could be excluded from skewing the predictions.  One specific example from the dataset I analyzed: there is no data from 4am to 8am on March 14, which was due to Uber pushing out an app update with the [surge pricing feature](https://blog.uber.com/2012/03/14/clear-and-straight-forward-surge-pricing/).

Associated with each outlier is a tag field.  This short description acts to save a known reasoning for the outlier, as well as provides a way to group and associate outliers.  I imagine a potentially valuable use of these outliers is to help determine the extent to which certain outliers increased (or decreased) demand, and use this information to help bias predicted demand instead of simply excluding the tagged outlier data.  For example, by tagging all hours that were impacted by Yelp promotions (i.e. with a "Yelp" tag), we can get measure the extent to which these promotions impacted demand, as well as help predict how future Yelp promotions might increase demand.
[x] Tag outliers
[x] Exclude outliers from prediction
[ ] Analyze specific tags
[ ] Influence prediction based on matching tags

##Prediction Approach

![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/Predicted_Slopes_0pass.png "LinReg - Trend by Hour")
One major problem with this simple linear regression technique is that it is highly sensitive to noise, and predicts a decrease in demand (negative slope) for some hours.  Particularly because this dataset is for Washington D.C. not too long after Uber was launched in the city (and had relatively sparse demand), we really don't expect the demand to decrease.  

To address this, I implemented an "Optimistic Smoothing" algorithm. It performs 2 passes of this smoothing technique on the slopes generated through linear regression.  Conceptually, the smoothing allows the trend (or slope) exhibited by neighboring hours to be factored into the expected trend at the current hour. It optimistically emphasizes positive trends in the data, by not doing a simple average of the current and before/after (neighboring) hours under the following conditions:
  * If current slope is local min, exclude current slope from average (only use neighbors)
  * If neighbor slope is negative, use the slope 2 hours away (if it is greater than neighbor)

Visually, we can see the difference this Optimistic Smoothing produces on the slope trends.  
![alt tag](https://raw.githubusercontent.com/cminnich/Demand_Prediction/master/plots/Predicted_Slopes.png "After 2-Pass Optimistic Smoothing")

#Usage
Start a local server instance (running on Port 5000 in the following examples) by running the following command from the top level directory  
`python runserver.py`

##Adding Client Login Timestamp Data - REST API
Allow POSTing of ISO-formatted UTC timestamps, i.e. the form  
**2012−05−01T00:00:00**

Insert a list of client logins within a JSON object:

`curl -i -H "Content-Type: application/json" -X POST -d @uber_demand_prediction_challenge.json http://localhost:5000/api/demand`

Insert a single client login datapoint:

`curl -i -H "Content-Type: application/json" -X POST -d '{"timestamp":"2012-03-01T00:05:55+00:00"}' http://localhost:5000/api/demand`

Insert a list of client logins:

`curl -i -H "Content-Type: application/json" -X POST -d '{"timestamps":["2012-03-01T00:05:55+00:00", "2012-03-01T00:06:23+00:00","2012-03-01T00:06:55+00:00"]}' http://localhost:5000/api/demand`

Returns json status of the post:
- error details will be specified if the input is invalid (within an 'error' key, whose value can specify more details)
- "timestamp" key will have list of hours that were affected (or just a single hour)
- if the affected hour already exists in the database, the "update" key will hold the count of the appended entries
- if a new hour record was created, the "insert" key will hold the count of the new entries

##Getting Client Login Predictions - REST API
Allow GETing of predicted number of logins (per hour) for days in the future.  Predictions will start on the day immediately following the latest historical datapoint.

By default will predict forward 15 days:

`curl -i http://localhst:5000/api/demand`

To predict a specific number of days (i.e. 3 days):

`curl -i http://localhst:5000/api/demand/3`

##Web Interface
I built a simple web interface with more functionality, as an alternate GUI based approach that allows for additional administrative tasks.  



