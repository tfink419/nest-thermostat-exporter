from flask import Flask, Response
import requests
import json
import datetime
import logging
import os
import sqlite3
from metric import Metric

# logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

GOOGLE_REFRESH_TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"

GOOGLE_ENTERPRISE = os.environ['GOOGLE_ENTERPRISE']
GOOGLE_DEVICE = os.environ['GOOGLE_DEVICE']
GOOGLE_DEVICE_URL = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{GOOGLE_ENTERPRISE}/devices/{GOOGLE_DEVICE}"

GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']
GOOGLE_REFRESH_TOKEN = os.environ['GOOGLE_REFRESH_TOKEN']

HOME_ASSISTANT_URL = "http://10.0.0.5:8123/api/states"
HOME_ASSISTANT_TOKEN = os.environ['HOME_ASSISTANT_TOKEN']

google_access_token = None
google_access_expires_at = datetime.datetime.now() - datetime.timedelta(seconds=1)

minutes_updated_at = datetime.datetime.now() - datetime.timedelta(minutes=1)

WEATHER_API_URL = "https://api.weather.gov/stations/KBKF/observations/latest"

nestTemperature = Metric("nest_ambient_temperature_celsius", "gauge", "Inside temperature")
nestHumidity = Metric("nest_humidity_percent", "gauge", "Inside humidty")
nestState = Metric("nest_hvac_state", "gauge", "HVAC status, -1 = cooling, 0 = idle, 1 = heating")
nestHvacMinutes = Metric("nest_hvac_status_minutes_total", "counter", "1 = in state, 0 = other")
nestSetpointHeating = Metric("nest_setpoint_temperature_heating_celsius", "gauge", "Setpoint temperature for heating")
nestSetpointCooling = Metric("nest_setpoint_temperature_cooling_celsius", "gauge", "Setpoint temperature for cooling")
nestUp = Metric("nest_up", "gauge", "Is Nest API connection successful")

weatherGovTemperature = Metric("weather_temperature_celsius", "gauge", "Outside temperature.")
weatherGovDewpoint = Metric("weather_dewpoint_celsius", "gauge", "Outside dewpoint.")
weatherGovHumidity = Metric("weather_humidity_percent", "gauge", "Outside humidity.")
weatherGovPressure = Metric("weather_pressure_pascal", "gauge", "Outside pressure.")
weatherGovWindspeed = Metric("weather_windspeed_km_per_hr", "gauge", "Outside windspeed.")
weatherGovPrecipitationLastHours = Metric("weather_precipitation_last_hour_meters", "gauge", "Outside precipitation in the last hour.")
weatherGovPrecipitationLast3Hours = Metric("weather_precipitation_last_3hours_meters", "gauge", "Outside precipitation in the last 3 hours.")
weatherGovPrecipitationLast6Hours = Metric("weather_precipitation_last_6hours_meters", "gauge", "Outside precipitation in the last 6 hours.")
weatherGovUp = Metric("weather_up", "gauge", "Is Weather.gov API connection successful.")

goveeIndoorTemperature = Metric("govee_outdoor_temperature_fahrenheit", "gauge", "Outside temperature.")
goveeIndoorHumidity = Metric("govee_outdoor_humidity_percent", "gauge", "Outside humidity.")
goveeOutdoorTemperature = Metric("govee_indoor_temperature_fahrenheit", "gauge", "Inside temperature.")
goveeOutdoorHumidity = Metric("govee_indoor_humidity_percent", "gauge", "Inside humidity.")
homeAssistantUp = Metric("home_assistant_up", "gauge", "Is Home Assistant API connection successful.")


@app.route('/')
def hello():
	conn = get_sqlite_conn()
	version_info = conn.execute('select sqlite_version();').fetchone()
	conn.close()
	return f'''
<html>
	<head>
		<title>Nest-Thermostat-Exporter</title>
	</head>
	<body>
		<h1>Hello World!</h1>
		<p>SQLite version: {version_info[0]}</p>
	</body>
</html>
'''

@app.route('/metrics')
def get_metrics():
	metrics = []
	process_google_stats(metrics)
	process_weather_stats(metrics)
	process_home_assistant_stats(metrics)

	metrics.append('')
	return Response("\n".join(metrics), mimetype='text/plain')

def process_google_stats(metrics):
	try:
		if datetime.datetime.now() > google_access_expires_at:
			refresh_google_access()
		
		google_stats = get_google_stats()
		room_name = google_stats['parentRelations'][0]['displayName'].replace(' ', '-')

		metrics += nestState.print_metrics(
			value = convert_nest_hvac_state(google_stats['traits']['sdm.devices.traits.ThermostatHvac']['status']),
			labels = { "label": room_name }
		)

		metrics += nestTemperature.print_metrics(
			value = google_stats['traits']['sdm.devices.traits.Temperature']['ambientTemperatureCelsius'],
			labels = { "label": room_name }
		)

		metrics += nestHumidity.print_metrics(
			value = google_stats['traits']['sdm.devices.traits.Humidity']['ambientHumidityPercent'],
			labels = { "label": room_name }
		)

		metrics += nestHvacMinutes.print_help_text()
		minutes = process_hvac_state_minutes(google_stats['traits']['sdm.devices.traits.ThermostatHvac']['status'])
		metrics += nestHvacMinutes.print_value_text(
			value = minutes[0],
			labels = {
				"label": room_name,
				"state": "COOLING"
			}
		)
		metrics += nestHvacMinutes.print_value_text(
			value = minutes[1],
			labels = {
				"label": room_name,
				"state": "OFF"
			}
		)
		metrics += nestHvacMinutes.print_value_text(
			value = minutes[2],
			labels = {
				"label": room_name,
				"state": "HEATING"
			}
		)

		metrics += nestSetpointHeating.print_metrics(
			value = google_stats['traits']['sdm.devices.traits.ThermostatTemperatureSetpoint']['heatCelsius'],
			labels = {
				"label": room_name
			}
		)
		metrics += nestSetpointCooling.print_metrics(
			value = google_stats['traits']['sdm.devices.traits.ThermostatTemperatureSetpoint']['coolCelsius'],
			labels = {
				"label": room_name
			}
		)

		metrics += nestUp.print_metrics(convert_nest_api_state(google_stats['traits']['sdm.devices.traits.Connectivity']['status']))
	except Exception as inst:
		logging.error("Google API Failure")
		logging.error(inst)
		metrics += nestUp.print_metrics(0)

def get_google_stats():
	headers = {
		'Content-Type': 'application/json',
		'Authorization': f"Bearer {google_access_token}"
	}

	response = requests.request("GET", GOOGLE_DEVICE_URL, headers=headers, data={})
	logging.debug(GOOGLE_DEVICE_URL)
	logging.debug(headers)
	logging.debug(response.text)

	return response.json()

def process_weather_stats(metrics):
	try:
		weather_stats = get_weather_stats()

		metrics += weatherGovTemperature.print_metrics(weather_stats['properties']['temperature']['value'])
		metrics += weatherGovHumidity.print_metrics(weather_stats['properties']['relativeHumidity']['value'])
		metrics += weatherGovDewpoint.print_metrics(weather_stats['properties']['dewpoint']['value'])
		metrics += weatherGovPressure.print_metrics(weather_stats['properties']['barometricPressure']['value'])
		metrics += weatherGovWindspeed.print_metrics(weather_stats['properties']['windSpeed']['value'])
		metrics += weatherGovPrecipitationLastHours.print_metrics(convert_precipitation(weather_stats['properties']['precipitationLastHour']['value']))
		metrics += weatherGovPrecipitationLast3Hours.print_metrics(convert_precipitation(weather_stats['properties']['precipitationLast3Hours']['value']))
		metrics += weatherGovPrecipitationLast6Hours.print_metrics(convert_precipitation(weather_stats['properties']['precipitationLast6Hours']['value']))
		metrics += weatherGovUp.print_metrics(1)
	except Exception as inst:
		logging.error("Weather.gov API Failure")
		logging.error(inst)
		metrics += weatherGovUp.print_metrics(0)


def get_weather_stats():
	response = requests.request("GET", WEATHER_API_URL, headers={}, data={})

	logging.debug(WEATHER_API_URL)
	logging.debug(response.text)

	return response.json()

def process_home_assistant_stats(metrics):
	try:
		home_assistant_stats = get_home_assistant_stats()

		metrics += goveeIndoorTemperature.print_metrics(home_assistant_stats['sensor.h5074_977b_temperature']['state'])
		metrics += goveeIndoorHumidity.print_metrics(home_assistant_stats['sensor.h5074_977b_humidity']['state'])
		metrics += goveeOutdoorTemperature.print_metrics(home_assistant_stats['sensor.h5074_4837_temperature']['state'])
		metrics += goveeOutdoorHumidity.print_metrics(home_assistant_stats['sensor.h5074_4837_humidity']['state'])
		metrics += homeAssistantUp.print_metrics(1)
	except Exception as inst:
		logging.error("Home Assistant API Failure")
		logging.error(inst)
		metrics += homeAssistantUp.print_metrics(0)

def get_home_assistant_stats():
	headers = {
		'Content-Type': 'application/json',
		'Authorization': f"Bearer {HOME_ASSISTANT_TOKEN}"
	}

	response = requests.request("GET", HOME_ASSISTANT_URL, headers=headers, data={})
	logging.debug(HOME_ASSISTANT_URL)
	logging.debug(headers)
	logging.debug(response.text)

	return {val['entity_id']: val for val in response.json()}

def refresh_google_access():
	global google_access_token, google_access_expires_at
	url_params = {
		'client_id': GOOGLE_CLIENT_ID,
		'client_secret': GOOGLE_CLIENT_SECRET,
		'refresh_token': GOOGLE_REFRESH_TOKEN,
		'grant_type': 'refresh_token'
	}
	url = f"{GOOGLE_REFRESH_TOKEN_URL}?{parameterize(url_params)}"
	response = requests.request("POST", url, headers={}, data={})
	logging.debug(url)
	logging.debug(response.text)
	google_access_token = response.json()['access_token']
	google_access_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=3595)


def parameterize(param_obj):
	return '&'.join([f"{key}={val}" for (key, val) in param_obj.items()])

def convert_nest_hvac_state(state_str):
	match state_str:
		case 'COOLING':
			return -1
		case 'OFF':
			return 0
		case 'HEATING':
			return 1

def process_hvac_state_minutes(state_str):
	global minutes_updated_at
	conn = get_sqlite_conn()
	m = list(conn.execute('SELECT cooling, off, heating FROM hvac_minutes;').fetchone())
	logging.debug("Minutes --------------------------------------------------")
	logging.debug(m)
	if datetime.datetime.now() >= minutes_updated_at + datetime.timedelta(seconds=55):
		minutes_updated_at = datetime.datetime.now()
		m[convert_nest_hvac_state(state_str)+1] += 1
		logging.debug(m)
		conn.execute(f"INSERT OR REPLACE INTO hvac_minutes(cooling, off, heating) VALUES ({m[0]}, {m[1]}, {m[2]});")
		conn.commit()
		logging.debug("Minutes --------------------------------------------------")
	conn.close()
	return m

def convert_nest_api_state(state_str):
	match state_str:
		case 'ONLINE':
			return 1
		case 'OFFLINE':
			return 0

def convert_nest_fan_state(state_str):
	match state_str:
		case 'ON':
			return 1
		case 'OFF':
			return 0

def convert_precipitation(weather_gov_response):
	if weather_gov_response:
		return weather_gov_response / 1000.0
	else:
		return 0

CREATE_TABLE = '''CREATE TABLE IF NOT EXISTS hvac_minutes (
heating INTEGER DEFAULT 0 UNIQUE,
cooling INTEGER DEFAULT 0 UNIQUE,
off INTEGER DEFAULT 0 UNIQUE
);
'''

def get_sqlite_conn():
	database = os.getenv('DATABASE', '/app/sqlite.db')
	return sqlite3.connect(database)

if __name__ == '__main__':
	conn = get_sqlite_conn()
	conn.execute(CREATE_TABLE)
	minutes = conn.execute('SELECT * FROM hvac_minutes;').fetchone()
	if minutes is None:
		minute = conn.execute('INSERT INTO hvac_minutes (heating, cooling, off) VALUES (0, 0, 0);')
		conn.commit()
	conn.close()
	app.run(host='0.0.0.0', port=8000)
