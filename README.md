# InkyPal AI

`InkyPal` is a tiny smart companion on e-ink.

It presents a friendly face, exposes a small HTTP API, and shows short updates on screen.

## Hardware

- Raspberry Pi Zero 2 W H (SPI enabled on Raspberry Pi OS)
- Waveshare 2.13 inch e-Paper Display V4

## Setup

Clone the project into `~/inkypal`:

```bash
git clone <your-repo-url> ~/inkypal
cd ~/inkypal
```

Install the Python dependencies with `requirements.txt`:

```bash
python3 -m pip install -r requirements.txt
```

If you prefer Raspberry Pi OS packages, you can also install:

```bash
sudo apt update
sudo apt install python3-pil python3-gpiozero python3-spidev
```

You also need to enable the Raspberry Pi SPI interface for the display:

```bash
sudo raspi-config
```

In `raspi-config`, enable:

- `Interface Options` -> `SPI`

`InkyPal` is designed to run as a `systemd` service so it starts automatically on boot and stays running.

Copy the service file:

```bash
sudo cp systemd/inkypal@.service /etc/systemd/system/inkypal@.service
```

Enable and start it for your username:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now inkypal@$(whoami).service
```

Check status:

```bash
sudo systemctl status inkypal@$(whoami).service
```

Restart after changes:

```bash
sudo systemctl restart inkypal@$(whoami).service
```

Read recent logs:

```bash
sudo journalctl -u inkypal@$(whoami).service -n 20 --no-pager
```

## API

When `InkyPal` starts, it listens on a random local port, shows the IP and port on the display, and is meant to be controlled through the API.

### GET /

Returns the current companion state.

Example:

```bash
curl http://PI_IP:PORT/
```

### GET /health

Returns the health state of the running service and display session.

Example:

```bash
curl http://PI_IP:PORT/health
```

### GET /status

Returns the current companion state, including the current face, message, IP, and port.

Example:

```bash
curl http://PI_IP:PORT/status
```

### GET /faces

Returns the list of available built-in face names.

Example:

```bash
curl http://PI_IP:PORT/faces
```

### POST /render

Updates the companion display.

JSON body fields:

- `face` - optional built-in face name
- `message` - optional message shown below the face

Unknown built-in face names return `400`. Use `GET /faces` as the source of truth for the current built-in list.

Example with a built-in face:

```bash
curl -X POST http://PI_IP:PORT/render \
  -H 'Content-Type: application/json' \
  -d '{"face":"alert","message":"API update"}'
```

### POST /off

Clears the display to white and keeps the running service ready for the next API update.

Example:

```bash
curl -X POST http://PI_IP:PORT/off
```

## Development

Quick local syntax check:

```bash
python3 -m compileall inkypal
```

## References

- [Waveshare official e-Paper repository](https://github.com/waveshareteam/e-Paper)
- [Upstream `epd2in13_V4.py` driver](https://github.com/waveshareteam/e-Paper/blob/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd2in13_V4.py)
- [Waveshare 2.13inch e-Paper HAT (G) Manual](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_(G)_Manual)

## Credits

_InkyPal_ is made with ♥ by [derogab](https://github.com/derogab) and it's released under the [GPL-3.0 license](./LICENSE).

### Contributors

<a href="https://github.com/derogab/inkypal/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=derogab/inkypal" />
</a>

### Tip
If you like this project or directly benefit from it, please consider buying me a coffee:  
🔗 `bc1qd0qatgz8h62uvnr74utwncc6j5ckfz2v2g4lef`  
⚡️ `derogab@sats.mobi`  
💶 [Sponsor on GitHub](https://github.com/sponsors/derogab)

### Stargazers over time
[![Stargazers over time](https://starchart.cc/derogab/inkypal.svg?variant=adaptive)](https://starchart.cc/derogab/inkypal)



