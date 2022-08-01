
# Setup

It's best to run this bot using a Python virtualenv, so that you don't clutter your system with conflicting pip-installed libraries.

```bash
virtualenv ~/venvs ttstreambot
source ~/venvs/ttstreambot/bin/activate
pip install -r requirements.txt
```

> **Warning**
>
> As of 2022-08-01 this code does not work correctly; modifications are needed to the baresipy library. In short, change the `self._login` assignment to set `;regint=0` so that baresip does not try to register an account.

## Getting a voice list

The sample configuration file does not specify any voices; you will need to run Festival and determine what voices are available.

    festival

At the `festival>` prompt, check what voices are available.

    (voice.list)

The output will show all of the available voices; here we're highlighting the one used for this project.

    (... cmu_us_slt_artic_hts ...)

Pick a voice name (note the prefix of `voice_` on the name)

    (voice_cmu_us_slt_artic_hts)

Play a sample

    (SayText "Daisy, Daisy, this is Twitch Chat calling")

Close Festival

    (quit)

Make a note of which voices you want to use. You'll need a minimum of one voice.

Additional voices are available; on Ubuntu the package names start with `festvox-`.

## Creating the configuration file

Run the bot program. It'll create the configuration file for you on the first run.

```bash
python bot.py

Default configuration created at /home/$USER/.config/ttstreambot/ttstreambot.toml; please edit it and re-run the bot.
```

## Application registration

- Go to https://dev.twitch.tv/console
- Register an application
- The URL is `http://localhost:17563`; ignore the instructions to use port 3000
- Generate a secret, making a note of the secret and the client ID.
- Save the application

## Configure the bot

Edit `$HOME/.config/ttstreambot.toml`.

* Uncomment the `client_id`, `client_secret`, `username` items in `[twitch]` and fill them in.
* Set up the `voices` item in `[festival]` based on the voice list you got from Festival earlier. 
* Set up the `destinations` item in `[phone]`.

## Running the bot (testing)

If you want to test that the SIP side works, use the `--test-baresip` argument to the program.

This loads `redemption.json`, and calls the function that

* checks if the redemption is valid (from the **ttstreambot.toml** `[phone]` destinations),
* picks a voice to use based on the **user** `display_name` in the JSON,
* tells baresip to call the relevant destination,
* plays the generated WAV file to the destination phone

The program will exit when it has finished playing the audio file.

## Running the bot (production)

```bash
source ~/venvs/ttstreambot/bin/activate
python3 bot.py
```

The bot will 

* authenticate to Twitch with the credentials provided, 
* open a browser window for you to authenticate the bot's access to your account,
* connect to Twitch's PubSub,
* start listening for redemption events.

On receiving a redemption event, the bot calls the relevant callback which

* checks if the redemption is valid (from the **ttstreambot.toml** `[phone]` destinations),
* picks a voice to use based on the **user** `display_name` in the JSON,
* tells baresip to call the relevant destination,
* plays the generated WAV file to the destination phone

The bot will then sit waiting for the next redemption event.

> **Note**
>
> If the browser window does not say "Thanks for Authenticating with pyTwitchAPI", and instead has a connection error, the port number in the Twitch Application registration form is wrong. Edit that, set it to `17563`. Restart the bot.

On startup, the bot will print out the configuration from the `.toml` file. It will look something like

```
[twitch]
╔════════════════════╦═══════════════════════════════════╗
║ Option             ║ Value                             ║
╠════════════════════╬═══════════════════════════════════╣
║ Twitch username    ║ my_username                       ║
║ Client ID          ║ 53jaxxxxxxxxxxxxxxxxxxxxxxa3oc    ║
║ Client Secret      ║ g74ixxxxxxxxxxxxxxxxxxxxxx7tpp    ║
╚════════════════════╩═══════════════════════════════════╝

[festival]
Voices override
╔══════════════╦═══════════════╦════════════╗
║ Username     ║ Voice         ║ Stretch    ║
╠══════════════╬═══════════════╬════════════╣
║ some_user    ║ us1_mbrola    ║ 1.0        ║
╚══════════════╩═══════════════╩════════════╝
Voice selection: hashed

[phone]
╔═══════════════════╦═════════════════════════════╗
║ Redemption        ║ Destination                 ║
╠═══════════════════╬═════════════════════════════╣
║ something here    ║ sip:service@sipura.local    ║
╚═══════════════════╩═════════════════════════════╝

[baresip]
╔═══════════════╦═════════════════════════════════════╗
║ Option        ║ Value                               ║
╠═══════════════╬═════════════════════════════════════╣
║ Config dir    ║ /home/dhill/.config/ttstreambot/    ║
╚═══════════════╩═════════════════════════════════════╝
```

# Known error messages

## Incorrect auth credentials
```
twitchAPI.pubsub - DEBUG - got response for nonce 956461d3-e2a7-4c4b-9964-7f69f2e8456d: PubSubResponseError.BAD_AUTH
```

There's something wrong with your username / client_id / client_secret settings.

## Bad file descriptor on Ctrl-C/bot exit

```
baresipy:quit:185 - INFO - Exiting
Exception in thread Thread-1:
Traceback (most recent call last):
...
OSError: [Errno 9] Bad file descriptor
```

The thread running baresip doesn't have handling for the subprocess exiting. Should only happen on bot exit, and it's harmless.

## Incorrect DNS hostname for a SIP destination

```
baresipy:handle_call_ended:307 - DEBUG - Reason: Destination address required
```

Check that you can resolve the `host` portion of the destination configured for a redemption.