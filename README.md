# InkyPal AI

<p align="center">
  <img src=".github/assets/display.png" alt="InkyPal e-ink display" width="100%" />
</p>

`InkyPal` is a tiny smart companion on e-ink.

It presents a friendly face, exposes a small HTTP API, and shows short updates on screen.

## Hardware

- Raspberry Pi Zero 2 W H (SPI enabled on Raspberry Pi OS)
- Waveshare 2.13 inch e-Paper Display V4

## Faces

| Preview | Name | Mood |
|---------|------|------|
| `(O_O)` | alert | Surprised or alarming |
| `(>_<)` | angry | Frustrated or upset |
| `(B_B)` | cool | Impressive or chill |
| `(o_O)` | curious | Intrigued or wondering |
| `(x_x)` | debug | Error or crash |
| `(^_^)` | excited | Enthusiastic or great news |
| `(o_o)` | happy | Friendly, positive, or neutral (default) |
| `(o3o)` | love | Heartwarming or affectionate |
| `(O_o)` | look_left | Idle animation |
| `(o_o)` | look_center | Idle animation |
| `(o_O)` | look_right | Idle animation |
| `(u_u)` | sad | Disappointing or bad news |
| `(-_-)` | sleepy | Tired, calm, or bored |

When AI is enabled, InkyPal automatically picks a face that matches the tone of its message. You can also set a face manually via the `POST /message` API.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `INKYPAL_PORT` | Fixed API port (optional). If not set, a random free port is used. | - |
| `GOTIFY_URL` | Gotify server base URL (optional). When set together with `GOTIFY_TOKEN`, non-empty messages shown by `POST /message` are also forwarded to Gotify. | - |
| `GOTIFY_TOKEN` | Gotify application token (optional). Used together with `GOTIFY_URL` to forward displayed messages to Gotify. | - |
| `OPENAI_API_KEY` | API key to enable AI message transformation (optional). When set, content sent to `POST /message` is rewritten into a short friendly sentence before being displayed. Any OpenAI-compatible v1 provider works ([OpenRouter](https://openrouter.ai), OpenAI, local LLMs, etc.). | - |
| `OPENAI_BASE_URL` | Base URL for the OpenAI-compatible API (optional). | https://openrouter.ai/api/v1 |
| `OPENAI_MODEL` | Model to use for AI message transformation (optional). | auto |
| `DEBUG_MODE` | Enable verbose debug logging (optional). Accepts `1`, `true`, or `yes`. When enabled, every API request is logged. | - |

## Setup

Download the latest release binary for your system:

```bash
curl -L -o inkypal <release-binary-url>
```

Install it to `/usr/local/bin`:

```bash
chmod +x inkypal
sudo mv inkypal /usr/local/bin/inkypal
```

You also need to enable the Raspberry Pi SPI interface for the display:

```bash
sudo raspi-config
```

In `raspi-config`, enable:

- `Interface Options` -> `SPI`

`InkyPal` is designed to run as a `systemd` service so it starts automatically on boot and stays running.

Create `/etc/inkypal.env`:

```bash
sudo tee /etc/inkypal.env >/dev/null <<'EOF'
# Optional: set a fixed API port instead of a random one.
# INKYPAL_PORT=8080

# Optional: forward displayed messages to Gotify.
# GOTIFY_URL=https://push.example.com
# GOTIFY_TOKEN=your-app-token

# Optional: enable AI message transformation.
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
# OPENAI_MODEL=auto
EOF
```

Create the service file:

```bash
sudo tee /etc/systemd/system/inkypal@.service >/dev/null <<'EOF'
[Unit]
Description=InkyPal smart companion bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%i
EnvironmentFile=-/etc/inkypal.env
ExecStart=/usr/local/bin/inkypal
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
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

When `InkyPal` starts, it listens on a random local port by default, shows the IP and port on the display, and is meant to be controlled through the API.

If `INKYPAL_PORT` is set in the service environment, that port is used instead of a random one.

### GET /

Returns a small API index with `running: true` and the list of available endpoints.

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

### POST /message

Updates the companion display.

Custom face/content updates are temporary. After 1 minute, the content is cleared and the idle face animation resumes.

JSON body fields:

- `face` - optional built-in face name
- `content` - optional message shown below the face
- `bypass_ai` - optional boolean; set to `true` to show `content` directly even when AI is configured

When AI is configured (see `OPENAI_API_KEY` above), the `content` value is automatically transformed into a short friendly sentence before being displayed. Set `bypass_ai` to `true`, or leave AI unconfigured, to show the raw content as-is.

When `GOTIFY_URL` and `GOTIFY_TOKEN` are both configured, the final non-empty message shown on the display is also forwarded to Gotify. If AI is enabled, Gotify receives the transformed display text.

When AI is configured, it also picks a face expression that matches the tone of its response. If you provide an explicit `face` in the request, your choice takes priority. Unknown face names are silently ignored.

Example with a built-in face:

```bash
curl -X POST http://PI_IP:PORT/message \
  -H 'Content-Type: application/json' \
  -d '{"face":"alert","content":"API update"}'
```

### POST /off

Clears the display to white and pauses the idle animation until the next `POST /message` update.

Example:

```bash
curl -X POST http://PI_IP:PORT/off
```

## Development

- Local source checkout:

```bash
git clone https://github.com/derogab/inkypal ~/inkypal
cd ~/inkypal
```

- Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

- Source code: `src/inkypal/`
- Tests: `tests/`

Quick local syntax check:

```bash
python3 -m compileall src/inkypal tests
```

Run the test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## References

- [Waveshare official e-Paper repository](https://github.com/waveshareteam/e-Paper)
- [Upstream `epd2in13_V4.py` driver](https://github.com/waveshareteam/e-Paper/blob/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epd2in13_V4.py)
- [Upstream `epdconfig.py` driver support module](https://github.com/waveshareteam/e-Paper/blob/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epdconfig.py)
- [Waveshare 2.13inch e-Paper HAT (G) Manual](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_(G)_Manual)

## Inspiration

Even though InkyPal is a much smaller project with a different goal, it is inspired by [pwnagotchi](https://github.com/evilsocket/pwnagotchi).

## Credits

_InkyPal_ is made with ♥ by [derogab](https://github.com/derogab) and it's released under the [GPL-3.0 license](./LICENSE).

## Contributors

<a href="https://github.com/derogab/inkypal/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=derogab/inkypal" />
</a>

## Tip
If you like this project or directly benefit from it, please consider buying me a coffee:  
🔗 `bc1qd0qatgz8h62uvnr74utwncc6j5ckfz2v2g4lef`  
⚡️ `derogab@sats.mobi`  
💶 [Sponsor on GitHub](https://github.com/sponsors/derogab)

## Stargazers over time
[![Stargazers over time](https://starchart.cc/derogab/inkypal.svg?variant=adaptive)](https://starchart.cc/derogab/inkypal)
