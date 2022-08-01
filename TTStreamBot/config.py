import enum
import logging
import os
import sys
from random import randint

import click
import hashring
import pydantic
import pydantic.dataclasses as dc
import toml

logger: logging.Logger = logging.getLogger(__name__)


class VoiceSelection(enum.Enum):
    random = "random"
    hashed = "hashed"


@dc.dataclass
class TwitchConfig:
    """Configuration for the Twitch API module"""

    # Client ID from registering an application
    client_id: str

    # Client secret from registering an application
    client_secret: str

    # Twitch username of the person running this program
    username: str

    @pydantic.validator("client_id")
    def client_id_must_not_be_empty_string(cls, v):
        if len(v) == 0:
            raise ValueError("[twitch] 'client_id' must have a value")
        return v

    @pydantic.validator("client_secret")
    def client_secret_must_not_be_empty_string(cls, v):
        if len(v) == 0:
            raise ValueError("[twitch] 'client_secret' must have a value")
        return v

    @pydantic.validator("username")
    def username_must_not_be_empty_string(cls, v):
        if len(v) == 0:
            raise ValueError("'[twitch] username' must have a value")
        return v


@dc.dataclass
class Voice:
    """Defines a voice for configuring Festival"""

    # The voice name, without the 'voice_' prefix
    name: str

    # Any custom stretch value for Festival's Duration_Stretch
    stretch: float | None = None


@dc.dataclass
class FestivalConfig:
    """Configuration for the Festival calls"""

    # All of the voices that should be used
    voices: list[Voice]

    # Override voice selection based on usernames/handles
    voices_override: dict[str, Voice]

    # What stretch to apply by default to voices
    stretch: float | None = 1.0

    # How to select a voice, default is hashring
    selection: VoiceSelection = VoiceSelection.hashed

    # Whether to make names easier for Festival to read
    replace_name_underscores: bool = False

    class Config:
        # Allow the self._hr bit.
        extra = "allow"

    @pydantic.validator("voices")
    def at_least_one_voice(cls, v):
        if not v:
            raise ValueError("[festival] At least one voice must be configured")
        return v

    def __post_init__(self):
        # Set up a hashring for the loaded voices
        self._hr = hashring.HashRing(range(len(self.voices)))

    def voice_for(self, caller: str) -> tuple[Voice, bool]:
        """Uses the hashring to pick a consistent voice for the caller"""
        try:
            logger.debug("Attempting override for %s", caller)
            return self.voices_override[caller], True
        except KeyError:
            pass
        if self.selection == VoiceSelection.hashed:
            logger.debug("Using hashring selection for %s", caller)
            return self.voices[self._hr.get_node(caller)], False
        else:
            logger.debug("Using random selection for %s", caller)
            return self.voices[randint(0, len(self.voices))], False


@dc.dataclass
class Destination:
    """Defines a destination for SIP usage"""

    # Hostname (fully qualified) or IP address to send the SIP call to
    host: str
    # Username at the host that should receive the call.
    user: str

    @property
    def sip(self) -> str:
        """Build a sip address for this destination"""
        return f"sip:{self.user}@{self.host}"


@dc.dataclass
class PhoneConfig:
    """What redemptions go to what Destination"""

    # Maps a destination from twitch.redemptions to a Destination
    destinations: dict[str, Destination]

    @pydantic.validator("destinations")
    def at_least_one_destination(cls, v):
        if not v:
            raise ValueError(
                "[phone] At least one redemption destination must be defined"
            )
        return v


@dc.dataclass
class BareSipConfig:
    """Configuration parameters for the embedded baresip program"""

    # Where to keep config, accounts, etcetera
    config_dir: str | None = os.path.expanduser("~/.config/ttstreambot/")


@dc.dataclass
class TTStreamBotConfig:
    """Top level object for the storage of the decoded TOML configuration"""

    twitch: TwitchConfig
    festival: FestivalConfig
    phone: PhoneConfig
    baresip: BareSipConfig


def configure_from(path: str) -> TTStreamBotConfig:
    logger.debug("Loading configuration from %s", path)
    config = toml.load(path)
    # Validate it via pydantic, and produce a configuration for the bot
    try:
        return TTStreamBotConfig(**config)
    except pydantic.error_wrappers.ValidationError as ex:
        click.secho(ex, fg="red")
        sys.exit(1)
