# agy in a sandbox on WSL

Run Google's Antigravity CLI (`agy`) in WSL Ubuntu, confined to one project folder, with an allow-list proxy as its
only way out to the network. Choose how it is confined: bubblewrap, Docker or Apptainer.

```sh
./agybox                   # set up if needed, then open agy in the sandbox
./agybox doctor            # check that the sandbox allows and refuses what it should
```

This is an independent project, not affiliated with or endorsed by Google. It downloads agy from Google's own release
server, checks it against the SHA-512 that Google publishes, and does not redistribute it.

## Why

- **A coding agent runs the commands a model writes.** Its instructions can come from anything it reads: a README, an
  issue, a dependency. With `always-proceed` it runs them without asking. In the sandbox, it can work on one folder,
  but not read your home, your SSH keys or your shell's secrets.
- **WSL adds ways out that Linux does not have.** Every Windows drive is mounted at `/mnt/c`, and WSL's interop starts
  any Windows `.exe` outside Linux entirely, from `cmd.exe` to PowerShell. The sandbox hides the drives, cannot reach
  interop, and `./agybox doctor` checks both.
- **Mirrored networking shares Windows' localhost.** With `networkingMode=mirrored`, anything listening on Windows'
  127.0.0.1 is reachable from WSL too. The sandbox has a network namespace of its own, so it cannot reach either
  machine's local services, or your LAN, or look up names, and leaves only through the proxy.
- **agy needs Google, and little else.** The proxy lets it reach the few hosts it needs for sign-in and its models, and
  refuses the rest. Add more hosts for one project when you need them.

## Backends

| `AGYBOX_BACKEND` | Uses | Tools inside | Needs |
|---|---|---|---|
| `bwrap` (default) | [bubblewrap](https://github.com/containers/bubblewrap): namespaces, no image | Your WSL Ubuntu's, read-only | Nothing: `setup` fetches bwrap without root if it is missing |
| `apptainer` | A rootless [Apptainer](https://apptainer.org) container | The image from [`container/agybox.def`](container/agybox.def) | `apptainer`. The image builds without root |
| `docker` | A Docker container, unprivileged, with a read-only root | The image from [`container/Dockerfile`](container/Dockerfile) | Docker Desktop with WSL integration, or docker-ce in WSL |

All three give agy the same view: the workspace at its own path, a home of its own at `/home/agent`, agy's binary
read-only, and the proxy. See [Backends](docs/backends.md) for how they differ.

## Status

> [!NOTE]
> Tested on WSL 2 (3.0.5, kernel 6.18, Ubuntu 24.04, mirrored networking): `./agybox doctor` passes all its checks
> with `bwrap`, `apptainer` and `docker` (Docker Desktop 29.6 with WSL integration), in the `proxy` and `none`
> networks, and agy 1.5.9 starts and reaches its sign-in on each. A signed-in session has been run with `bwrap` on a
> fresh Windows 11 and Ubuntu 24.04.
>
> With `docker`, agy's own sandbox for commands may not work: Docker's default seccomp profile usually refuses new
> user namespaces, which agy needs to run commands. `./agybox doctor` checks this ("agy can make its own sandbox for
> commands"), but it has not been run on docker yet.
>
> The allow list may still miss a host that another agy build or account type needs. If agy fails after sign-in, run
> `./agybox hosts` to see what the proxy refused. Run `./agybox doctor` before you rely on any backend.

## Requirements

- WSL 2 with Ubuntu (22.04 or newer), or Linux on x86-64 or arm64
- `curl`, `python3` and `tar`, which Ubuntu has
- For `apptainer` or `docker`: that tool, as above

Clone this repository into WSL's own filesystem, such as `~/agy-wsl-sandbox`, not onto a Windows drive under `/mnt`:
the sandbox's home needs Linux permissions.

## Quick start

```sh
git clone https://github.com/kyledent/agy-wsl-sandbox.git ~/agy-wsl-sandbox
cd ~/agy-wsl-sandbox
./agybox setup       # download agy and check it; fetch bubblewrap or build the image
./agybox doctor      # check the sandbox
./agybox             # open agy, and sign in
```

**Signing in.** agy prints a Google sign-in link. Open it in your Windows browser (Ctrl+click in Windows Terminal), sign
in, and paste the code the page gives you back into agy. The callback goes to `antigravity.google`, not to localhost, so
this works from inside the sandbox's network. The token is kept in `.state/home`, which only the sandbox can see. It
is not shared with an agy you run outside.

Put your project in `./workspace`, or set `WORKSPACE_DIR` in `.env`. agy can only work there.

## Network

| `AGYBOX_NETWORK` | agy can reach |
|---|---|
| `proxy` (default) | The hosts in [`allow/hosts.txt`](allow/hosts.txt) and your `allow/local.txt`, through the proxy |
| `learn` | Any public host, through the proxy, which logs them. Then `./agybox hosts all` |
| `none` | Nothing. agy cannot reach its models, but the shell and tools work offline |
| `open` | WSL's own network: the internet, your LAN, any VPN, and in mirrored mode Windows' localhost |

Even in `learn` mode, the proxy refuses private, loopback and link-local addresses. See [Network](docs/network.md).

## Commands

| Command | What it does |
|---|---|
| `./agybox` | Set up if needed, then open agy. Arguments go to agy: `./agybox --continue` |
| `./agybox setup` | Download agy and check its SHA-512; fetch bubblewrap or build the docker or apptainer image |
| `./agybox update` | Download the latest agy. agy cannot update itself in the sandbox, as its binary is read-only |
| `./agybox shell` | A shell in the sandbox, in the workspace |
| `./agybox run CMD` | Run a command in the sandbox: `./agybox run git status` |
| `./agybox doctor` | Check that the sandbox allows and refuses what it should |
| `./agybox hosts` | The hosts the proxy refused, to add to `allow/local.txt`. `hosts all` adds the allowed ones |
| `./agybox status` | The backend, network, agy version and folders in use |

## Documentation

- [Backends](docs/backends.md): bubblewrap, Apptainer and Docker, and how to choose
- [Network](docs/network.md): the proxy, the allow list and the network modes
- [Sandbox](docs/sandbox.md): what the sandbox allows, what `doctor` checks, and its limits
- [Configuration](docs/configuration.md): every setting in `.env`
- [Hardening](docs/hardening.md): known gaps, and how to tighten the setup further
- [Troubleshooting](docs/troubleshooting.md)

## Tests

`tests/run.sh` checks the scripts and the proxy, with no sandbox. `./agybox doctor` tests the sandbox itself, on the
backend in use:

```sh
tests/run.sh
AGYBOX_BACKEND=apptainer ./agybox doctor
```

## Acknowledgements

The design follows [bonsai-metal-sandbox](https://github.com/kyledent/bonsai-metal-sandbox), which does the same for a
local model and the pi agent under macOS's `sandbox-exec`.

## License

[Apache License 2.0](LICENSE). This covers the code in this repository. agy is downloaded from Google, under its own
terms.
