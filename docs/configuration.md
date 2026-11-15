# Configuration

Settings are in `.env`, which `./agybox` creates from [`.env.example`](../.env.example) on its first run. Values are
literal, as `docker compose` reads them. A variable set in your shell wins over `.env`, so you can change one for one
run:

```sh
AGYBOX_BACKEND=apptainer AGYBOX_NETWORK=learn ./agybox
```

| Setting | Default | What it does |
|---|---|---|
| `AGYBOX_BACKEND` | `bwrap` | `bwrap`, `apptainer` or `docker`. See [Backends](backends.md) |
| `AGYBOX_NETWORK` | `proxy` | `proxy`, `learn`, `none` or `open`. See [Network](network.md) |
| `WORKSPACE_DIR` | `./workspace` | The one folder agy can read and write. Relative to this folder. It may not be your home, or hold this folder |
| `AGYBOX_PASS_ENV` | `GH_TOKEN` | Variables from your shell to pass in, separated by commas, if they are set. The agent can read them |
| `AGY_TOOL_EXECUTION_POLICY` | empty | agy's tool policy, written to its settings at every start: `always-proceed`, `request-review`, `proceed-in-sandbox` or `strict`. Empty leaves agy's own setting, which `/permissions` changes |
| `AGYBOX_MEMORY` | empty | A memory limit, such as `8G`. Swap is not allowed past it. When it is reached, the process that asked for more is killed, not the session |
| `AGYBOX_CPUS` | empty | A CPU limit, such as `4` or `1.5` |
| `AGYBOX_PIDS` | empty (`4096` with docker) | A limit on processes and threads |
| `AGYBOX_DISABLE_USERNS` | `0` | bwrap only. `1` turns off user namespaces inside, which breaks agy's commands. See [Hardening](hardening.md#user-namespaces-inside) |

For bwrap and apptainer, the limits use a systemd scope (`systemd-run --user --scope`), which needs systemd in WSL:
`systemd=true` under `[boot]` in `/etc/wsl.conf`, the default on Ubuntu 24.04. Docker uses its own.

## The environment inside

The sandbox starts with an empty environment, and gets:

| Variable | Value |
|---|---|
| `HOME` | `/home/agent` |
| `USER`, `LOGNAME` | `agent` |
| `PATH` | `/opt/agy`, `~/.local/bin`, then the system's |
| `TERM`, `LANG`, `TZ`, `COLORTERM`, `TERM_PROGRAM` | From your shell, if set |
| `HTTPS_PROXY`, `HTTP_PROXY` (and lower case) | `http://127.0.0.1:3128`, with the proxy |
| `NO_PROXY` (and lower case) | `localhost,127.0.0.1,::1` |
| `AGYBOX`, `AGYBOX_BACKEND`, `AGYBOX_NETWORK` | So scripts can tell they are in the sandbox |

Plus each variable named in `AGYBOX_PASS_ENV`. A value with a newline in it is refused.

## Files

| Path | What | Kept between runs |
|---|---|---|
| `.env` | Your settings | Yes |
| `allow/local.txt` | Your additions to the allow list | Yes |
| `.state/home/` | The sandbox's home: agy's settings, sign-in, conversations, `~/.local` | Yes. Delete it to start afresh |
| `.state/proxy.log` | Every request the proxy allowed or refused | Yes. Delete it whenever you like |
| `.state/run/PID/` | A run's proxy socket | No |
| `.runtime/agy/VERSION/agy` | agy, and the previous version | Until the next update |
| `.runtime/agy/current` | Points at the version in use. `ln -sfn 1.5.8 .runtime/agy/current` goes back | Yes |
| `.runtime/bwrap/` | bubblewrap, if it was not installed | Yes |
| `.runtime/agybox.sif` | The Apptainer image | Until its recipe changes |

## The images

The docker and apptainer images both run [`container/packages.sh`](../container/packages.sh). Add the tools your
projects need there; `./agybox` rebuilds the image the next time it runs. agy is not in the image, so `./agybox update`
needs no rebuild.
