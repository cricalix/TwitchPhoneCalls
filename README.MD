# Twitch Phone Call Bot

This is a bit of Python code that
* spawns a baresip instance,
* subscribes to Twitch's PubSub,
* listens for redemptions,
* converts the message of the redemption to speech using Festival,
* instructs baresip to call a SIP phone,
* plays the speech file when the phone picks up

Required software (outside of Python modules)
 - `Festival` for TTS
 - `ffmpeg` for converting audio files

## Features
* toml-driven configuration file
* automatic creation of sample config file in ~/.config/ttstreambot
* automatic creation of baresip configuration in ~/.config/ttstreambot
* multiple voices supported
* speed control per voice
* random or hashed voice selection
* overrides of voice per Twitch username, with speed control (overrides random and hashed selection)
* different destinations (sip:user@host) per redemption
* optional replacement of underscores in usernames for better speech

# Hardware

You will need
- a Plain Old Telephone System phone; you get more style points for older phones
- some form of Analog Telephone Adapter (ATA) with FXS ports; examples include a Linksys/Cisco SPA2102 or Grandstream HT801

Since the phone is only being used to receive calls, it can be a rotary/pulse phone.

Alternately, you can use a SIP softphone that accepts calls without registration.

# Getting Started

You will need
- A Twitch account that is Affiliate or Partner level (to have channel points and thus redemptions)
- An application registered at https://dev.twitch.tv/console
- Python 3
- Festival TTS and Festival TTS development headers
- FFmpeg
- baresip

## Application registration

- Go to https://dev.twitch.tv/console
- Register an application
- The URL is `http://localhost:17563`; ignore the instructions to use port 3000
- Generate a secret, making a note of the secret and the client ID.
- Save the application

# Software

## Ubuntu packages
- Festival TTS and headers - `apt install festival festvox-us-slt-hts festival-dev`
- FFmpeg - `apt install ffmpeg` (needed for baresipy dependency)
- BareSIP - `apt install baresip`

Other voice packs are available; `apt search festvox-`

See [SETUP.md](SETUP.md) for details on configuring the bot.