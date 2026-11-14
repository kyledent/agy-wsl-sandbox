# Backends

Each backend gives agy the same view, and `./agybox doctor` runs the same checks on each:

| Inside | From | Access |
|---|---|---|
| The workspace, at its own path | `WORKSPACE_DIR` | Read-write |
| `/home/agent` (`HOME`) | `.state/home` | Read-write: agy's settings, sign-in, conversations, and tools you install there |
| `/opt/agy/agy` | `.runtime/agy/current` | Read-only |
| `/opt/agybox` | [`lib/`](../lib): the entry script and the relay | Read-only |
| `/run/agybox/proxy.sock` | This run's proxy | Read-only, with the `proxy` and `learn` networks only |
| `/tmp` | A fresh, empty folder for each run | Read-write |

Everything else of yours is out of sight: your home, `/mnt/c` and the other Windows drives, `/run/WSL`, your D-Bus
session, and other processes. The environment starts empty, with only what `./agybox` passes (see
[Configuration](configuration.md)).

Switch for one run, or for good in `.env`:

```sh
AGYBOX_BACKEND=apptainer ./agybox
```

Each backend keeps the same `.state/home`, so your sign-in and conversations follow you between them.

## bwrap

[bubblewrap](https://github.com/containers/bubblewrap) is the tool Flatpak uses to build its sandboxes. `./agybox` gives
it a new user, PID, IPC, UTS, cgroup and network namespace, an empty root on a tmpfs, and mounts into it:

- `/usr`, `/etc` and the `/bin`, `/lib`, `/sbin` links, read-only: the programs and libraries of your WSL Ubuntu
- `/proc` for the sandbox's own processes, and a minimal `/dev`

It also drops every capability, and turns off user namespaces inside (`--disable-userns`).

**Choose it when** you want agy to use the tools you already have in WSL, with nothing to build. A tool you install with
`apt` outside appears inside at once. Tools in your home, such as `nvm` or `pipx` installs, do not, as your home is not
there. Install those in the sandbox's home instead, with `./agybox shell`.

**Setup.** If `bwrap` is not installed, `./agybox setup` fetches Ubuntu's package with `apt-get download` and unpacks
it into `.runtime/bwrap`. That needs no root: apt checks the package against its signed index, and bwrap runs
unprivileged. To use the system's instead: `sudo apt install bubblewrap`, then `rm -rf .runtime/bwrap`.

## apptainer

A rootless [Apptainer](https://apptainer.org) container from [`container/agybox.def`](../container/agybox.def): Ubuntu
24.04 with the tools in [`container/packages.sh`](../container/packages.sh). `./agybox` runs it with `--containall`
(its own PID and IPC namespaces, an empty environment, no home or `/tmp` of yours), `--no-mount hostfs,cwd`,
`--no-privs`, a writable tmpfs over the image, and `--net --network none` for every network but `open`.

**Choose it when** you want agy's tools to be fixed and separate from your WSL Ubuntu, or you already use Apptainer, as
on a cluster.

**Setup.** `./agybox setup` builds `.runtime/agybox.sif` with `apptainer build --fakeroot`. On WSL, fakeroot cannot
mount `binfmt_misc`, so it falls back to `--fakeroot --ignore-subuid`, which works there. It rebuilds the image when
`agybox.def` or `packages.sh` changes. Apptainer itself:

```sh
sudo add-apt-repository -y ppa:apptainer/ppa && sudo apt install -y apptainer
```

## docker

A container from [`container/Dockerfile`](../container/Dockerfile), the same Ubuntu 24.04 and packages as the Apptainer
image. `./agybox` runs it as your own user ID, so files it writes in the workspace are yours, with:

- `--cap-drop ALL` and `--security-opt no-new-privileges`
- `--read-only`: the image cannot change, and `/tmp` is a tmpfs
- `--network none` for every network but `open`, with the proxy's socket mounted in
- `--pids-limit 4096` by default, and `--memory` and `--cpus` from `.env`
- The environment from a file, not the command line, where `ps` would show `GH_TOKEN`

**Choose it when** you already run Docker, or want to share the image with others.

**Setup.** Either Docker Desktop with **Settings → Resources → WSL integration** turned on for your distro, or docker-ce
installed in WSL itself. Your user needs to be in the `docker` group. `./agybox setup` builds `agybox:latest`, and
rebuilds it when the `Dockerfile` or `packages.sh` changes.

> [!WARNING]
> The docker backend has not been run yet. In particular, `--network none` relies on the proxy's unix socket working
> when mounted into the container. With docker-ce in WSL, that is the same kernel and it should. With Docker Desktop,
> whose engine runs in its own WSL distro, `./agybox doctor` will tell. If "it can reach agy's sign-in service through
> the proxy" fails there, please report it.

Anyone who can run `docker` can start a privileged container, so membership of the `docker` group is equivalent to root
in WSL. That is about who runs `./agybox`, not about the agent: it cannot reach the Docker socket from inside.

## Choosing

| | bwrap | apptainer | docker |
|---|---|---|---|
| Tools inside | Your WSL Ubuntu's | The image's | The image's |
| Setup | None | Build an image (a few minutes) | Docker, and build an image |
| Start-up | Fastest | Fast | Slower: a container per run |
| Memory, CPU and process limits | Through systemd | Through systemd | Docker's own |
| Root filesystem | Your `/usr` and `/etc`, read-only | The image, with a writable tmpfs | The image, read-only |
| Tested | Yes | Yes | Not yet |

All three share one Linux kernel with WSL and Windows' WSL VM. None of them is a virtual machine: a kernel bug could
break any of them. See [Hardening](hardening.md#stronger-boundaries) for a stronger boundary.
