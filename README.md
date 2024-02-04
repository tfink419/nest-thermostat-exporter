## Nest Thermostat Prometheus Exporter

## Deploy with docker compose

```
$ docker compose up -d
```

## Expected result
After the application starts, navigate to `http://localhost:8000` in your web browser or run:
```
$ curl localhost:8000/metrics
HELP nest_ambient_temperature_celsius Inside temperature.
TYPE nest_ambient_temperature_celsius gauge
nest_ambient_temperature_celsius 16.899994
HELP nest_humidity_percent Inside humidity.
TYPE nest_humidity_percent gauge
nest_humidity_percent 35
HELP nest_hvac_state HVAC status, -1 = cooling, 0 = off, 1 = heating.
TYPE nest_hvac_state gauge
nest_hvac_state 0
HELP nest_fan_state HVAC Fan status
TYPE nest_fan_state gauge
nest_fan_state 0
HELP nest_setpoint_temperature_heating_celsius Setpoint temperature for heating.
TYPE nest_setpoint_temperature_heating_celsius gauge
nest_setpoint_temperature_heating_celsius 16.173447
HELP nest_setpoint_temperature_cooling_celsius Setpoint temperature for cooling.
TYPE nest_setpoint_temperature_cooling_celsius gauge
nest_setpoint_temperature_cooling_celsius 22.5
HELP nest_up Is Nest API connection successful.
TYPE nest_up gauge
nest_up 1
```

Stop and remove the containers
```
$ docker compose down
```
