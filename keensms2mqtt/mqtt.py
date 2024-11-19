import aiomqtt


class StubSubscriberClient(aiomqtt.Client):
    """A wrapper class for MQTT Client.
    MQTT specs do not require server to keep any messages if there are no active
    subscription sessions. A session is created per subscriber, but subscriber needs to
    connect and subscribe first. Even if it goes offline afterwards, MQTT broker will
    keep storing messages with QoS > 1 into its session.
    So, this class is a stub, that connects, subscribes, but do not ack any messages -
    for the broker to not lose any messages that weren't fetched by the actual subscriber
    yet.
    """

    def __init__(self, *args, manual_ack=True, clean_session=False, **kwargs):
        super().__init__(*args, clean_session=clean_session, **kwargs)
        self._client.manual_ack_set(manual_ack)


async def create_stub_session(host, port, subscriber_id, topic, qos=1):
    async with StubSubscriberClient(host, port, identifier=subscriber_id) as client:
        await client.subscribe(topic, qos=qos)
