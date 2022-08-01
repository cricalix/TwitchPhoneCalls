#!/usr/bin/env python3

import functools
import logging
import os
import shutil
import sys
import time
from uuid import UUID

import click
from baresipy import BareSIP
from click_loglevel import LogLevel
from twitchAPI.helper import TWITCH_PUB_SUB_URL
from twitchAPI.pubsub import PubSub

from TTStreamBot.config import TTStreamBotConfig, configure_from
from TTStreamBot.lib import (
    connect_and_authenticate,
    create_audio_file,
    render_configuration,
)

logger: logging.Logger = logging.getLogger("bot")


def callback_on_redemption(
    user_id: UUID, data, config: TTStreamBotConfig, phone: BareSIP
) -> None:
    redemption_type = data["data"]["redemption"]["reward"]["title"]
    # Only pay attention to specific redemptions; case sensitive
    if redemption_type in config.phone.destinations.keys():
        message = data["data"]["redemption"]["user_input"]
        caller = data["data"]["redemtion"]["user"]["display_name"]
        wavfile = create_audio_file(caller=caller, message=message, config=config)
        dest = config.phone.destinations[redemption_type]
        logger.info(f"Calling {dest.sip} on behalf of {caller}")
        phone.call(dest.sip)
        while phone.running:
            time.sleep(0.5)
            if phone.call_established:
                time.sleep(0.5)
                logger.debug(f"Playback of {wavfile}")
                phone.send_audio(wavfile)
                phone.hang()


def default_files(config_dir: str) -> None:
    defaultfile = os.path.join(config_dir, "ttstreambot.toml")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    if not os.path.exists(defaultfile):
        shutil.copyfile("sample-config.toml", defaultfile)
        click.secho(
            message=(
                f"Default configuration created at {defaultfile}; "
                "please edit it and re-run the bot."
            ),
            fg="yellow",
        )
        sys.exit(1)


@click.command()
@click.option(
    "-c",
    "--config-dir",
    type=click.Path(),
    help="The configuration directory to use; will be auto-created if it doesn't exist",
    required=True,
    default=os.path.expanduser("~/.config/ttstreambot/"),
)
@click.option(
    "-l", "--log-level", type=LogLevel(), default=logging.INFO, help="Log level to use"
)
def main(config_dir: str, log_level: int) -> None:
    """TTStreamBot is a text to speech to SIP CLI.

    On first usage, the config-dir will be created, a default configuration
    file written, and then the program will exit.
    """
    logging.basicConfig(
        format="[%(levelname)-8s] %(message)s",
        level=log_level,
    )
    logging.getLogger("TTStreamBot").setLevel(log_level)
    default_files(config_dir)
    ttconfig = configure_from(os.path.join(config_dir, "ttstreambot.toml"))
    render_configuration(config=ttconfig)

    try:
        logger.info("Bringing up baresip")
        b = BareSIP(
            user="ttstreambot",
            pwd="service",
            gateway="192.168.0.222",
            debug=False,
            config_path=config_dir,
        )
        twitch, user_id = connect_and_authenticate(config=ttconfig)

        logger.info(f"Initializing PubSub listener to {TWITCH_PUB_SUB_URL}")

        pubsub = PubSub(twitch)
        pubsub.start()
        subscription = pubsub.listen_channel_points(
            user_id, functools.partial(callback_on_redemption, config=ttconfig, phone=b)
        )
        input("press ENTER to close...")
    except KeyboardInterrupt:
        # Listener is in a thread, have to Ctrl-C twice without this try block.
        pass
    finally:
        logger.error("You'll want to clean up /tmp/est*")
    logger.info("Closing down listener and exiting")
    pubsub.unlisten(subscription)
    pubsub.stop()
    logger.info("Shutting down baresip")
    # Stacktraces on exit. Library needs attention.
    b.quit()


if __name__ == "__main__":
    main()
