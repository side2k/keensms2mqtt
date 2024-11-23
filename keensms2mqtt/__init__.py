import asyncio
import json
import logging
import os
from datetime import datetime

import aiomqtt
import yaml
from simple_keenetic_client import SimpleKeeneticClient

from keensms2mqtt.mqtt import create_stub_session
from keensms2mqtt.utils import deep_merge, host_root_url

logger = logging.getLogger(__name__)


class KeenSMS2MQTT:
    DEFAULT_CONFIG = {
        "logging": {
            "debug": False,
        },
        "keenetic": {
            "request_interval": 5,
            "host": "router.local",
            "username": "admin",
            "password": "admin",
            "mark_as_read": True,
            "delete_processed": False,
            "datetime_format": "%a %b %d %H:%M:%S %Y",
        },
        "access": {"phones": []},
        "mqtt": {
            "host": "mqtt.local",
            "port": 1883,
            "topic": "keensms/messages",
            "subscriber_id": None,
            "publisher_id": "keensms-publisher",
        },
    }
    client = None

    def __init__(self):
        self.get_config()
        # cache for messages that we do not want to process (e.g. from unknown numbers),
        # but also do not want to mark them read or delete
        self._cache_for_skipped = set()

    def get_config(self) -> dict:
        config = {}
        config.update(self.DEFAULT_CONFIG)

        config_filename = os.environ.get("KEENSMS_CONFIG", "keensms2mqtt.yaml")
        if os.path.exists(config_filename):
            logger.debug("{config_file} exists, loading configuration")
            with open(config_filename, "r") as config_file:
                file_data = yaml.load(config_file, Loader=yaml.Loader)
                config = deep_merge(config, file_data)

        self.config = config

        return config

    def get_setting(self, setting_path):
        """Returns settings from config via their path, e.g.: `access.phones` or
        `keenetic.host`. Returns None if setting is absent of one of the intermediate
        stops is not dict(to avoid exceptions on .get())
        """
        scope = self.config
        parts = setting_path.split(".")
        path_len = len(parts)
        for part_index, part in enumerate(parts):
            scope = scope.get(part)
            if part_index == path_len - 1:
                return scope
            if scope is None:
                logger.debug(f"setting {setting_path} not found")
                return None

            if not issubclass(type(scope), dict):
                return None

    def config_is_valid(self):
        """Returns True is self.config has minimal required settings for the tool to
        do its job
        """
        for required_setting in [
            "keenetic.host",
            "keenetic.username",
            "keenetic.password",
        ]:
            if self.get_setting(required_setting) is None:
                logger.error(f"Missing required setting: {required_setting }")
                return False

        return True

    async def sms_fetch_loop(self):
        base_url = host_root_url(self.get_setting("keenetic.host"))
        logger.info(f"Connecting to {base_url=}")

        async with SimpleKeeneticClient(
            base_url,
            username=self.get_setting("keenetic.username"),
            password=self.get_setting("keenetic.password"),
        ) as client:
            self.client = client
            interfaces = await self.client.get_mobile_interfaces()

            request_interval = self.get_setting("keenetic.request_interval")
            logger.info(
                f"Fetching unread messages with interval of {request_interval} sec"
            )
            while True:
                unread_messages = await self.get_unread_sms(
                    interface_names=interfaces.keys()
                )
                logger.debug(f"{unread_messages=}")
                await self.process_messages(unread_messages)
                await asyncio.sleep(request_interval)

    async def mqtt_publish(self, payload, qos=1):
        host = self.get_setting("mqtt.host")
        port = self.get_setting("mqtt.port")
        topic = self.get_setting("mqtt.topic")
        subscriber_id = self.get_setting("mqtt.subscriber_id")
        publisher_id = self.get_setting("mqtt.publisher_id")

        if subscriber_id:
            await create_stub_session(host, port, subscriber_id, topic)
        async with aiomqtt.Client(
            host, port=port, identifier=publisher_id, clean_session=False
        ) as publisher:
            await publisher.publish(topic, payload, qos=qos)

    async def run(self):
        if not self.config_is_valid():
            raise Exception("Invalid configuration")

        await asyncio.gather(
            self.sms_fetch_loop(),
        )

    async def get_unread_sms(self, interface_names):

        messages = []

        for if_name in interface_names:
            sms_data = await self.client.get_sms_by_interface(if_name)
            for msg_id, msg in sms_data["sms"]["list"].get("messages", {}).items():
                if msg["read"]:
                    continue
                messages.append((if_name, msg_id, msg))

        return messages

    async def process_message(self, msg_id, msg) -> bool:
        """Returns True if message fits criterias to be processed, so can be deleted
        after function was successfully executed
        """
        logger.debug(f"Processing message: {msg}")
        if msg["from"] in self.get_setting("access.phones"):
            serialized_msg = self.serialize_sms(msg_id, msg)
            await self.mqtt_publish(serialized_msg)
            return True
        return False

    async def process_messages(self, unread_messages):
        processed = {}

        for if_name, msg_id, msg in unread_messages:
            if msg_id in self._cache_for_skipped:
                continue
            is_processed = await self.process_message(msg_id, msg)
            if is_processed:
                by_interface = processed.setdefault(if_name, [])
                by_interface.append(msg_id)
            else:
                self._cache_for_skipped.add(msg_id)

        if self.get_setting("keenetic.delete_processed"):
            for interface_name, msg_ids in processed.items():
                await self.client.delete_sms(interface_name, msg_ids)
            return

        if self.get_setting("keenetic.mark_as_read"):
            for interface_name, msg_ids in processed.items():
                await self.client.mark_sms_as_read(interface_name, msg_ids)

    def serialize_sms(self, msg_id, msg):
        timestamp = datetime.strptime(
            msg["timestamp"], self.get_setting("keenetic.datetime_format")
        )
        return json.dumps(
            {
                "id": msg_id,
                "from": msg["from"],
                "text": msg["text"],
                "timestamp": timestamp.isoformat(),
            },
            ensure_ascii=False,
        )
