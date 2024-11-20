import asyncio
import logging
from signal import SIGINT, SIGTERM

from keensms2mqtt import KeenSMS2MQTT

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(level=logging.INFO)
    tool = KeenSMS2MQTT()
    if not tool.config_is_valid():
        logger.error("Configuration error, exiting")
        exit(1)
        return
    if tool.get_setting("logging.debug"):
        logging.basicConfig(level=logging.DEBUG)

    await tool.run()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(main())
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, main_task.cancel)

    try:
        loop.run_until_complete(main_task)
    except asyncio.CancelledError:
        print("Graceful stop")
    finally:
        loop.close()
