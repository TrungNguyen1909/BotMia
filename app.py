#!/usr/bin/env python

import urllib
import json
import os
import pywu
from flask import Flask
from flask import request
from flask import make_response
from datetime import datetime

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    print("ProcessingRequest")
    if req.get('result').get('action') == "weather.search":
        print("weather.search Action chose")
        filename = '/tmp/pywu.cache.json'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        print("checked file & directory")
        if req.get('result').get('parameters').get('geo-city') is None:
            args = type('obj', (object,), {'verbose' : False,'apikey':'97fca79bb0f45e0e','location':'autoip','language':'EN' , 'sub':"fetch"})
        else:
            args = type('obj', (object,), {'verbose' : False,'apikey':'97fca79bb0f45e0e','location':req.get('result').get('parameters').get('geo-city'),'language':'EN' , 'sub':"fetch"})
        print("args made.")
        a=pywu.ForecastData(args)
        print("Fetched Data")
        if req.get('result').get('parameters').get('date') != None:
            if datetime.strptime(req.get('result').get('parameters').get('date'),'%Y-%m-%d') > datetime.now():
                time="future"
            else: time="present"
        else:
            time="present"
        print(time)
        data=a.read_forecast()
        if time=="future":
            data=a.read_forecast()
            for i in data:
                if datetime.strptime(req.get('result').get('parameters').get('date'),'%Y-%m-%d') ==datetime.strptime(i.get('shortdate'),'%m/%d/%Y'):
                    data=i
                    break
        else:
            data=a.read_current()
        res = makeWebhookResult(data,time,req)
        return res

def makeWeatherWebhookResult(data,time,req):
    print(time)
    condition = data.get('condition')
    if condition is None:
        print("Condition is None")
        return {}

    # print(json.dumps(item, indent=4))
    if time=="present" and req.get('result').get('parameters').get('geo-city') is not None :
        speech = "Today in " + req.get('result').get('parameters').get('geo-city') + " is " + data.get('condition') + \
             ", the temperature is " + str(data.get('temp_c')) +"C"
    if time=="present" and req.get('result').get('parameters').get('geo-city') is None:
        speech = "Today at current location " + " is " + data.get('condition') + \
             ", the temperature is " + str(data.get('temp_c')) +"C"
    if time == "future" and req.get('result').get('parameters').get('geo-city') is not None:  
        speech = "The weather forecast in "+ req.get('result').get('parameters').get('geo-city') + " is " + data.get('condition') + \
             ", the lowest temperature is " + str(data.get('low_c')) + "C and the highest one is " + str(data.get('high_c')) +"C"
    if time == "future" and req.get('result').get('parameters').get('geo-city') is None:  
        speech = "The weather forecast at current location " + " is " + data.get("condition") + \
             ", the lowest temperature is " + str(data.get('low_c')) + "C and the highest one is " + str(data.get('high_c'))+"C"
    print("Response:")
    print(speech)
    if time=="present":
        slack_message = {
            "text": speech,
            "attachments": [
                {
                    "title": "Weather from The Weather Channel, LLC",
                    "title_link": "https://www.wunderground.com/?apiref=c2f87008ef83fd36",
                    "color": "#36a64f",

                    "fields": [
                        {
                            "title": "Condition",
                            "value": "Temp " + str(data.get('temp_c'))+"C",
                            "short": "false"
                        },
                        {
                            "title": "Wind",
                            "value": data.get('wind'),
                            "short": "true"
                        },
                        {
                            "title": "Atmosphere",
                            "value": "Humidity " + data.get('humidity') +
                                    " pressure " + data.get('pressure_mb'),
                            "short": "true"
                        }
                    ]
                }
            ]
        }
    if time=="future":
        slack_message = {
            "text": speech,
            "attachments": [
                {
                    "title": "Weather from The Weather Channel, LLC",
                    "title_link": "https://www.wunderground.com/?apiref=c2f87008ef83fd36",
                    "color": "#36a64f",

                    "fields": [
                        {
                            "title": "Condition",
                            "value": "Temp low/high " + str(data.get('low_c')) + "C/" + str(data.get('high_c'))+"C",
                            "short": "false"
                        }
                    ]
                }
            ]
        }
    facebook_message = {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": [
                    {
                        "title": "Weather from The Weather Channel LLC:",
                        "image": data.get('icon'),
                        "subtitle": speech,
                        "buttons": [
                            {
                                "type": "web_url",
                                "url": "https://www.wunderground.com/?apiref=c2f87008ef83fd36",
                                "title": "View Details"
                            }
                        ]
                    }
                ]
            }
        }
    }

    print(json.dumps(slack_message))

    return {
        "speech": speech,
        "displayText": speech,
        "data": {"slack": slack_message, "facebook": facebook_message},
        # "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
