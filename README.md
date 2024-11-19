# Keenetic SMS to MQTT

Simple service that reads SMS messages from KeeneticOS-based router(that has mobile network capabilities) and routes them to MQTT server. It was implemented as a part of home automation system, to allow send simple commands(e.g. "open gate") via SMS messages.

## Requirements:

  - Python 3.11+
  - [aiomqtt](https://aiomqtt.bo3hm.com/introduction.html)
  - [aiohttp](https://docs.aiohttp.org/en/stable/)

## Sample configuration

`keensms2mqtt.yaml`:
```yaml
keenetic:
  host: "router.local"
  username: "admin"
  password: "admin"
  # if messages are not marked read,
  # they will be re-processed on each new query
  mark_as_read: true
  request_interval: 5 #seconds
mqtt:
  host: "mqtt-server.home"
  topic: "keensms/messages"
  # before publishing any message, subscription
  # request with the given subscriber_id will be
  # issued, to ensure MQTT broker  stores published
  # messages
  subscriber_id: "keensms-subscriber"
access:
  # only SMS from phones listed here will be processed
  phones:
    - "+79010012345"

```
