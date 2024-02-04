from flask import Flask, Response
import requests
import json
import datetime
import logging
import os

# logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

GOOGLE_REFRESH_TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"

GOOGLE_ENTERPRISE = os.environ['GOOGLE_ENTERPRISE']
GOOGLE_DEVICE = os.environ['GOOGLE_DEVICE']
GOOGLE_DEVICE_URL = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{GOOGLE_ENTERPRISE}/devices/{GOOGLE_DEVICE}"

GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']
GOOGLE_REFRESH_TOKEN = os.environ['GOOGLE_REFRESH_TOKEN']

google_access_token = None
google_access_expires_at = datetime.datetime.now()

WEATHER_API_URL = "https://api.weather.gov/stations/KBKF/observations/latest"

INSIDE_TEMPERTURE_NAME = "nest_ambient_temperature_celsius"
INSIDE_TEMPERTURE_HELP = f"# HELP {INSIDE_TEMPERTURE_NAME} Inside temperature."
INSIDE_TEMPERTURE_TYPE = f"# TYPE {INSIDE_TEMPERTURE_NAME} gauge"
# nest_ambient_temperature_celsius{label="Living-Room"} 23.5

HVAC_STATE_NAME = "nest_hvac_state"
HVAC_STATE_HELP = f"# HELP {HVAC_STATE_NAME} HVAC status, -1 = cooling, 0 = off, 1 = heating."
HVAC_STATE_TYPE = f"# TYPE {HVAC_STATE_NAME} gauge"
# nest_hvac_state{label="Living-Room"} 0

FAN_STATE_NAME = "nest_fan_state"
FAN_STATE_HELP = f"# HELP {FAN_STATE_NAME} HVAC Fan status"
FAN_STATE_TYPE = f"# TYPE {FAN_STATE_NAME} gauge"
# nest_hvac_state{label="Living-Room"} 0

INSIDE_HUMIDITY_NAME = "nest_humidity_percent"
INSIDE_HUMIDITY_HELP = f"# HELP {INSIDE_HUMIDITY_NAME} Inside humidity."
INSIDE_HUMIDITY_TYPE = f"# TYPE {INSIDE_HUMIDITY_NAME} gauge"
# nest_humidity_percent{label="Living-Room"} 55

SETPOINT_HEATING_NAME = "nest_setpoint_temperature_heating_celsius"
SETPOINT_HEATING_HELP = f"# HELP {SETPOINT_HEATING_NAME} Setpoint temperature for heating."
SETPOINT_HEATING_TYPE = f"# TYPE {SETPOINT_HEATING_NAME} gauge"
# nest_setpoint_temperature_heating_celsius{label="Living-Room"} 18

SETPOINT_COOLING_NAME = "nest_setpoint_temperature_cooling_celsius"
SETPOINT_COOLING_HELP = f"# HELP {SETPOINT_COOLING_NAME} Setpoint temperature for cooling."
SETPOINT_COOLING_TYPE = f"# TYPE {SETPOINT_COOLING_NAME} gauge"
# nest_setpoint_temperature_cooling_celsius{label="Living-Room"} 22

NEST_UP_NAME = "nest_up"
NEST_UP_HELP = f"# HELP {NEST_UP_NAME} Is Nest API connection successful."
NEST_UP_TYPE = f"# TYPE {NEST_UP_NAME} gauge"
# nest_up 1

WEATHER_TEMPERATURE_NAME = "weather_temperature_celsius"
WEATHER_TEMPERATURE_HELP = f"# HELP {WEATHER_TEMPERATURE_NAME} Outside temperature."
WEATHER_TEMPERATURE_TYPE = f"# TYPE {WEATHER_TEMPERATURE_NAME} gauge"
# weather_temperature_celsius 17.57

WEATHER_DEWPOINT_NAME = "weather_dewpoint_celsius"
WEATHER_DEWPOINT_HELP = f"# HELP {WEATHER_DEWPOINT_NAME} Outside dewpoint."
WEATHER_DEWPOINT_TYPE = f"# TYPE {WEATHER_DEWPOINT_NAME} gauge"
# weather_dewpoint_celsius 17.57

WEATHER_HUMIDITY_NAME = "weather_humidity_percent"
WEATHER_HUMIDITY_HELP = f"# HELP {WEATHER_HUMIDITY_NAME} Outside humidity."
WEATHER_HUMIDITY_TYPE = f"# TYPE {WEATHER_HUMIDITY_NAME} gauge"
# weather_humidity_percent 82

WEATHER_PRESSURE_NAME = "weather_pressure_pascal"
WEATHER_PRESSURE_HELP = f"# HELP {WEATHER_PRESSURE_NAME} Outside pressure."
WEATHER_PRESSURE_TYPE = f"# TYPE {WEATHER_PRESSURE_NAME} gauge"
# weather_pressure_pascal 101600

WEATHER_WINDSPEED_NAME = "weather_windspeed_km_per_hr"
WEATHER_WINDSPEED_HELP = f"# HELP {WEATHER_WINDSPEED_NAME} Outside windspeed."
WEATHER_WINDSPEED_TYPE = f"# TYPE {WEATHER_WINDSPEED_NAME} gauge"
# weather_windspeed_km_per_hr 12

WEATHER_PRECIPITATION_LAST_HOUR_NAME = "weather_precipitation_last_hour_meters"
WEATHER_PRECIPITATION_LAST_HOUR_HELP = f"# HELP {WEATHER_PRECIPITATION_LAST_HOUR_NAME} Outside precipitation in the last hour."
WEATHER_PRECIPITATION_LAST_HOUR_TYPE = f"# TYPE {WEATHER_PRECIPITATION_LAST_HOUR_NAME} gauge"
# weather_windspeed_km_per_hr 0.01

WEATHER_PRECIPITATION_LAST_3HOURS_NAME = "weather_precipitation_last_3hours_meters"
WEATHER_PRECIPITATION_LAST_3HOURS_HELP = f"# HELP {WEATHER_PRECIPITATION_LAST_3HOURS_NAME} Outside precipitation in the last 3 hours."
WEATHER_PRECIPITATION_LAST_3HOURS_TYPE = f"# TYPE {WEATHER_PRECIPITATION_LAST_3HOURS_NAME} gauge"
# weather_windspeed_km_per_hr 0.03

WEATHER_PRECIPITATION_LAST_6HOURS_NAME = "weather_precipitation_last_6hours_meters"
WEATHER_PRECIPITATION_LAST_6HOURS_HELP = f"# HELP {WEATHER_PRECIPITATION_LAST_6HOURS_NAME} Outside precipitation in the last 6 hours."
WEATHER_PRECIPITATION_LAST_6HOURS_TYPE = f"# TYPE {WEATHER_PRECIPITATION_LAST_6HOURS_NAME} gauge"
# weather_windspeed_km_per_hr 0.05

WEATHER_UP_NAME = "weather_up"
WEATHER_UP_HELP = f"# HELP {WEATHER_UP_NAME} Is Weather.gov API connection successful."
WEATHER_UP_TYPE = f"# TYPE {WEATHER_UP_NAME} gauge"
# weather_up 1

@app.route('/')
def hello():
	return "Hello World!"

@app.route('/metrics')
def get_metrics():
	metrics = []
	try:
		if datetime.datetime.now() > google_access_expires_at:
			refresh_google_access()
		
		google_stats = get_google_stats()
		room_name = google_stats['parentRelations'][0]['displayName'].replace(' ', '-')
		label=f"{{label=\"{room_name}\"}}"

		metrics.extend([INSIDE_TEMPERTURE_HELP, INSIDE_TEMPERTURE_TYPE])
		metrics.append(f"{INSIDE_TEMPERTURE_NAME}{label} {google_stats['traits']['sdm.devices.traits.Temperature']['ambientTemperatureCelsius']}")
		metrics.extend([INSIDE_HUMIDITY_HELP, INSIDE_HUMIDITY_TYPE])
		metrics.append(f"{INSIDE_HUMIDITY_NAME}{label} {google_stats['traits']['sdm.devices.traits.Humidity']['ambientHumidityPercent']}")
		metrics.extend([HVAC_STATE_HELP, HVAC_STATE_TYPE])
		metrics.append(f"{HVAC_STATE_NAME}{label} {convert_nest_hvac_state(google_stats['traits']['sdm.devices.traits.ThermostatHvac']['status'])}")
		metrics.extend([FAN_STATE_HELP, FAN_STATE_TYPE])
		metrics.append(f"{FAN_STATE_NAME}{label} {convert_nest_fan_state(google_stats['traits']['sdm.devices.traits.Fan']['timerMode'])}")
		metrics.extend([SETPOINT_HEATING_HELP, SETPOINT_HEATING_TYPE])
		metrics.append(f"{SETPOINT_HEATING_NAME}{label} {google_stats['traits']['sdm.devices.traits.ThermostatTemperatureSetpoint']['heatCelsius']}")
		metrics.extend([SETPOINT_COOLING_HELP, SETPOINT_COOLING_TYPE])
		metrics.append(f"{SETPOINT_COOLING_NAME}{label} {google_stats['traits']['sdm.devices.traits.ThermostatTemperatureSetpoint']['coolCelsius']}")
		metrics.extend([NEST_UP_HELP, NEST_UP_TYPE])
		metrics.append(f"{NEST_UP_NAME} {convert_nest_api_state(google_stats['traits']['sdm.devices.traits.Connectivity']['status'])}")
	except:
		logging.error("Google API Failure")
		metrics.extend([NEST_UP_HELP, NEST_UP_TYPE])
		metrics.append(f"{NEST_UP_NAME} 0")

	try:
		weather_stats = get_weather_stats()

		metrics.extend([WEATHER_TEMPERATURE_HELP, WEATHER_TEMPERATURE_TYPE])
		metrics.append(f"{WEATHER_TEMPERATURE_NAME} {weather_stats['properties']['temperature']['value']}")

		metrics.extend([WEATHER_HUMIDITY_HELP, WEATHER_HUMIDITY_TYPE])
		metrics.append(f"{WEATHER_HUMIDITY_NAME} {weather_stats['properties']['relativeHumidity']['value']}")

		metrics.extend([WEATHER_DEWPOINT_HELP, WEATHER_DEWPOINT_TYPE])
		metrics.append(f"{WEATHER_DEWPOINT_NAME} {weather_stats['properties']['dewpoint']['value']}")

		metrics.extend([WEATHER_WINDSPEED_HELP, WEATHER_WINDSPEED_TYPE])
		metrics.append(f"{WEATHER_WINDSPEED_NAME} {weather_stats['properties']['windSpeed']['value']}")

		metrics.extend([WEATHER_PRESSURE_HELP, WEATHER_PRESSURE_TYPE])
		metrics.append(f"{WEATHER_PRESSURE_NAME} {weather_stats['properties']['barometricPressure']['value']}")

		metrics.extend([WEATHER_PRECIPITATION_LAST_HOUR_HELP, WEATHER_PRECIPITATION_LAST_HOUR_TYPE])
		metrics.append(f"{WEATHER_PRECIPITATION_LAST_HOUR_NAME} {convert_precipitation(weather_stats['properties']['precipitationLastHour']['value'])}")

		metrics.extend([WEATHER_PRECIPITATION_LAST_3HOURS_HELP, WEATHER_PRECIPITATION_LAST_3HOURS_TYPE])
		metrics.append(f"{WEATHER_PRECIPITATION_LAST_3HOURS_NAME} {convert_precipitation(weather_stats['properties']['precipitationLast3Hours']['value'])}")

		metrics.extend([WEATHER_PRECIPITATION_LAST_6HOURS_HELP, WEATHER_PRECIPITATION_LAST_6HOURS_TYPE])
		metrics.append(f"{WEATHER_PRECIPITATION_LAST_6HOURS_NAME} {convert_precipitation(weather_stats['properties']['precipitationLast6Hours']['value'])}")

		metrics.extend([WEATHER_UP_HELP, WEATHER_UP_TYPE])
		metrics.append(f"{WEATHER_UP_NAME} 1")
	except:
		logging.error("Weather.gov API Failure")
		metrics.extend([WEATHER_UP_HELP, WEATHER_UP_TYPE])
		metrics.append(f"{WEATHER_UP_NAME} 0")


	metrics.append('')
	return Response("\n".join(metrics), mimetype='text/plain')

def get_weather_stats():
	response = requests.request("GET", WEATHER_API_URL, headers={}, data={})

	logging.debug(WEATHER_API_URL)
	logging.debug(response.text)

	return response.json()

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
		return weather_gov_response / 1000
	else:
		return 0

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8000)
