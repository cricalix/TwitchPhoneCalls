#!/usr/bin/env python3

import functools
import json
import logging
import os
import shutil
import sys
import time

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
    channel_id: str, data, config: TTStreamBotConfig, phone: BareSIP
) -> None:
    redemption_type = data["data"]["redemption"]["reward"]["title"]
    logger.debug("Received redemption '%s'", redemption_type)
    # Only pay attention to specific redemptions; case sensitive
    if redemption_type in config.phone.destinations.keys():
        message = data["data"]["redemption"]["user_input"]
        caller = data["data"]["redemption"]["user"]["display_name"]
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
                os.unlink(wavfile)
                phone.hang()
                return


def default_files(config_dir: str) -> None:
    default_toml = os.path.join(config_dir, "ttstreambot.toml")
    default_baresip = os.path.join(config_dir, "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    if not os.path.exists(default_baresip):
        shutil.copyfile("baresip-config", default_baresip)
    if not os.path.exists(default_toml):
        shutil.copyfile("sample-config.toml", default_toml)
        click.secho(
            message=(
                f"Default configuration created at {default_toml}; "
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
    default=os.path.expanduser("~/.config/ttstreambot"),
)
@click.option(
    "--baresip-debug", is_flag=True, default=False, help="Enable baresip debug logs"
)
@click.option(
    "-l", "--log-level", type=LogLevel(), default=logging.INFO, help="Log level to use"
)
@click.option(
    "--test-baresip",
    is_flag=True,
    default=False,
    help="Don't connect to Twitch, just use the redemption callback",
)
def main(
    baresip_debug: bool, config_dir: str, log_level: int, test_baresip: bool
) -> None:
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
        phone = BareSIP(
            user="ttstreambot",
            pwd="service",
            gateway="192.168.0.222",
            debug=baresip_debug,
            config_path=config_dir,
        )
        if test_baresip:
            with open("redemption.json") as f:
                data = json.load(f)
            callback_on_redemption(
                channel_id="12345", data=dict(data), config=ttconfig, phone=phone
            )
            phone.quit()
            sys.exit(0)

        twitch, channel_id = connect_and_authenticate(config=ttconfig)
        logger.info(f"Initializing PubSub listener to {TWITCH_PUB_SUB_URL}")
        pubsub = PubSub(twitch)
        pubsub.start()
        subscription = pubsub.listen_channel_points(
            channel_id,
            functools.partial(callback_on_redemption, config=ttconfig, phone=phone),
        )
        input("press ENTER to close...")
    except KeyboardInterrupt:
        # Listener is in a thread, have to Ctrl-C twice without this try block.
        pass

    logger.info("Closing down listener and exiting")
    pubsub.unlisten(subscription)
    pubsub.stop()
    logger.info("Shutting down baresip")
    # Stacktraces on exit. Library needs attention.
    phone.quit()


if __name__ == "__main__":
    main()
