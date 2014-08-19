Demand_Prediction
=================

Predicts future demand based on historical data.  Given JSON formatted timestamps (where each timestamp represents a client login datapoint), predicts the number of logins per hour for future days.  This project was implemented with Python, Flask, and SQLite3.  

Users can interact through either a Command-Line RESTful API, or Web interface.  Start a local server instance (running on Port 5000 in the following examples) by running the following command `python runserver.py`

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


![alt tag](https://raw.github.com/cminnich/Demand_Prediction/master/Plots/Predicted_Slopes.png)
