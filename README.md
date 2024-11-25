# Keenetic SMS to MQTT

Simple service that reads SMS messages from KeeneticOS-based router(that has mobile network capabilities) and routes them to MQTT server. It was implemented as a part of home automation system, to allow send simple commands(e.g. "open gate") via SMS messages.

## Requirements:

  - Python 3.11+
  - [aiomqtt](https://aiomqtt.bo3hm.com/introduction.html)
  - [aiohttp](https://docs.aiohttp.org/en/stable/)

## Sample configuration

`keensms2mqtt.yaml`:
```yaml
logging:
  debug: true
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
  # if subscriber_id is set, before publishing any message, subscription
  # request with the given subscriber_id will be issued, to ensure MQTT
  # broker stores published messages
  subscriber_id: "keensms-subscriber"
access:
  # only SMS from phones listed here will be processed
  phones:
    - "+79010012345"

```
## Running

For now this project can be run only as a standalone application.

### Running with bare Python

If you're familiar with Python and do not afraid to use Poetry, here is the simple and short solution, that requires only Python 3.11 or higher installed:

```bash
# go to the project dir
cd keensms2mqtt

# installing Poetry (https://python-poetry.org/docs/)
curl -sSL https://install.python-poetry.org | python3 -

# creating environment and installing dependencies
poetry install

# running keensms2mqtt
poetry run python run.py
```

### Using Docker Compose

This is shorter and simpler, but requires [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/) installed

```bash
docker compose up keensms2mqtt
```

On first run, it will build an image, which takes some time. Then it will simply run. To run it in background mode, just use `-d` switch:

```bash
docker compose up -d keensms2mqtt
```

## Connecting to Home Assistant

Can be done via [MQTT integration](https://www.home-assistant.io/integrations/mqtt/).

- event configuration example:
```yaml
mqtt:
  - event:
      name: "sms message"
      state_topic: "keensms/messages"
      qos: 1
      event_types:
        - sms_message
      value_template: |
        {
          "event_type": "sms_message",
          "from": "{{ value_json.from }}",
          "text": "{{ value_json.text }}"
        }
```

- automation example. Personally, I'm using [Yandex.Station automation](https://github.com/AlexxIT/YandexStation) via [HACS](https://www.hacs.xyz/), but hopefully you'll find enough data in this demo to use it whenever you want:
```yaml
automation:
  - id: '123456789'
    alias: autotest-ui
    description: 'SMS message notification'
    triggers:
    - trigger: event
      event_type: state_changed
      event_data:
        entity_id: event.sms_message
    conditions: []
    actions:
    - action: media_player.play_media
      metadata: {}
      data:
        media_content_type: text
        media_content_id: received SMS message {{ trigger.event.data.new_state.attributes.text }}
      target:
        device_id: 12345abcdef
```
