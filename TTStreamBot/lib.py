import logging

import click
import festival
import prettytable
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.types import AuthScope

from .config import TTStreamBotConfig

logger: logging.Logger = logging.getLogger(__name__)

# Voices that cannot be Duration_Stretched
NO_STRETCH: tuple[str, ...] = ("cmu_us_slt_arctic_hts",)


def fec(command: str) -> None:
    logger.debug("Festival> %s", command)
    festival.execCommand(command)


def create_audio_file(caller: str, message: str, config: TTStreamBotConfig) -> str:
    voice, override = config.festival.voice_for(caller)
    logger.info(f"Picked {voice.name} for {caller}{' (override)' if override else ''}")
    fec(f"(voice_{voice.name})")
    if voice.name in NO_STRETCH and voice.stretch != 1.0:
        logger.warn(f"Cannot change stretch of {voice.name}")
    else:
        stretch = (
            voice.stretch if voice.stretch is not None else config.festival.base_stretch
        )
        fec(f"(Parameter.set 'Duration_Stretch {stretch})")

    wavfile = festival.textToWavFile(f"{caller} said {message}")
    logger.debug(f"Festival created {wavfile}")
    return wavfile


def connect_and_authenticate(config: TTStreamBotConfig) -> tuple[Twitch, str]:
    twitch = Twitch(
        app_id=config.twitch.client_id,
        app_secret=config.twitch.client_secret,
    )
    account = twitch.get_users(logins=[config.twitch.username])
    display_name = account["data"][0]["display_name"]
    user_id = account["data"][0]["id"]
    logger.info(f"Connecting via account {display_name} ({user_id})")

    target_scope = [AuthScope.CHANNEL_READ_REDEMPTIONS]
    auth = UserAuthenticator(twitch, target_scope, force_verify=False)

    logger.info("Triggering browser for authentication")
    token, refresh_token = auth.authenticate()
    twitch.set_user_authentication(token, target_scope, refresh_token)
    return twitch, user_id


def get_prettytable(field_names: list[str]) -> prettytable.PrettyTable:
    p = prettytable.PrettyTable(right_padding_width=4)
    p.set_style(prettytable.DOUBLE_BORDER)
    p.field_names = field_names
    p.align = "l"
    return p


def obfuscate(value: str) -> str:
    return value[0:4] + "x" * (len(value) - 8) + value[-4:]


def render_configuration(config: TTStreamBotConfig) -> None:
    """Display the configuration of the program"""
    render_configuration_twitch(config)
    click.echo()
    render_configuration_festival(config)
    click.echo()
    render_configuration_phone(config)
    click.echo()
    render_configuration_baresip(config)
    click.echo()


def render_configuration_twitch(config: TTStreamBotConfig) -> None:
    """Display the [twitch] section"""
    click.secho("[twitch]", fg="bright_green", bold=True)
    p = get_prettytable(["Option", "Value"])
    p.add_row(["Twitch username", config.twitch.username])
    p.add_row(["Client ID", obfuscate(config.twitch.client_id)])
    p.add_row(["Client Secret", obfuscate(config.twitch.client_secret)])
    click.secho(message=p, fg="blue")


def render_configuration_festival(config: TTStreamBotConfig) -> None:
    """Display the [festival] section"""
    click.secho("[festival]", fg="bright_green", bold=True)
    if config.festival.voices_override:
        p = get_prettytable(["Username", "Voice", "Stretch"])
        for username, voice in config.festival.voices_override.items():
            p.add_row(
                [
                    username,
                    voice.name,
                    voice.stretch if voice.stretch else config.festival.base_stretch,
                ]
            )
        click.secho(message="Voices override", fg="blue")
        click.secho(message=p, fg="blue")
    else:
        click.secho(message="No overrides present for redemptions")
    click.secho(message=f"Voice selection: {config.festival.selection.name}", fg="blue")


def render_configuration_phone(config: TTStreamBotConfig) -> None:
    """Display the [phone] section"""
    click.secho("[phone]", fg="bright_green", bold=True)
    p = get_prettytable(["Redemption", "Destination"])
    for redemption, destination in config.phone.destinations.items():
        p.add_row([redemption, f"sip:{destination.user}@{destination.host}"])
    click.secho(message=p, fg="blue")


def render_configuration_baresip(config: TTStreamBotConfig) -> None:
    """Display the [baresip] section"""
    click.secho("[baresip]", fg="bright_green", bold=True)
    p = get_prettytable(["Option", "Value"])
    p.add_row(["Config dir", config.baresip.config_dir])
    click.secho(message=p, fg="blue")
