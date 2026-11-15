# Hardening

The default [sandbox](sandbox.md) keeps agy away from your home, your Windows drives, Windows' interop and every host but
the few it needs. This page covers what it does not do, and how to go further.

## What this defends against

The main risk is the agent running a harmful command without anyone intending it. Its instructions can come from anything
it reads: a README, an issue, a dependency, or a web page. So assume that a hostile command will run at some point, and
consider what it could reach.

| An attacker would want to | What stands in the way |
|---|---|
| Read your SSH keys, tokens and documents, in WSL or Windows | The mounts: only the workspace and the sandbox's home |
| Run something in Windows, outside WSL | No interop socket, no drives, its own process tree |
| Send out what it can read | The proxy's allow list |
| Reach your LAN, VPN, or services on localhost | The sandbox's own network namespace, and the proxy's refusal of private addresses |
| Stay around for later sessions | Little: see [Separate your projects](#separate-your-projects) |
| Damage the workspace | Little: version control and backups |
| Use up the machine | The limits, if you set them |

## Start here

In `.env`:

```sh
AGYBOX_NETWORK=proxy
AGYBOX_PASS_ENV=
AGYBOX_MEMORY=8G
AGYBOX_PIDS=2048
```

- **Keep the network on `proxy`.** Use `learn` or `open` for one session at a time, not in `.env`.
- **Pass no tokens.** If you need `GH_TOKEN`, use a fine-grained token for one repository, with a short expiry, and
  assume the agent can read it.
- **Set limits.** Without them, a runaway build can use all of WSL's memory, which Windows shares.
- **Keep the allow list short.** Look at `./agybox hosts all` now and then, and remove what you no longer need from
  `allow/local.txt`.

## Separate your projects

**Give the agent a copy, not your repository.** The agent can write `.git/config` and `.git/hooks` in the workspace, and
ordinary commands outside the sandbox act on them. Even `git diff` can run a program named in `.git/config`. Keep your
real repository outside the workspace, and move work across with `git clone --no-local` and `git fetch`, which git's
documentation treats as safe with a repository you do not trust:

```sh
git clone --no-local ~/code/project workspace/project   # the agent's copy

# after the agent has committed its work, from your real repository:
cd ~/code/project
git fetch ~/agy-wsl-sandbox/workspace/project HEAD
git diff HEAD...FETCH_HEAD
```

This protects your git setup only. Build scripts, `package.json`, `.envrc`, `Makefile`s and `.vscode/` files in the diff
still run with your full rights once you use them, so read them first. VS Code's Restricted Mode helps when you open the
workspace there.

**Use one workspace per project,** and keep secrets out of it. The agent can read a `.env` in the workspace.

**Reset the sandbox's home between projects you do not trust.** `.state/home` survives between sessions, including
agy's plugins, MCP servers, hooks and settings, and agy loads them the next time it starts. Something hostile can stay
there and follow you to the next project, still inside the sandbox. With agy closed:

```sh
rm -rf .state/home    # you will need to sign in again
```

Or keep one checkout of this repository per project, each with its own `.state`.

## Inside the sandbox

**agy's own permissions still apply.** `AGY_TOOL_EXECUTION_POLICY=request-review` asks before each tool. Within the
sandbox, `always-proceed` is a reasonable choice, as the sandbox is the boundary, but it means a hostile instruction is
carried out at once.

**agy runs each command in a sandbox of its own.** It starts itself again (`/opt/agy/agy`) in new namespaces for every
shell command, so it needs user namespaces inside this sandbox, and `./agybox doctor` checks that it can make them. Its
binary also has Landlock and seccomp code; `./agybox --sandbox` turns on its stricter terminal restrictions.

### User namespaces inside

User namespaces are a common way into kernel bugs, and bwrap 0.8 and newer can turn them off inside the sandbox. That
also stops agy's own command sandbox: every command agy runs then fails with
`fork/exec /opt/agy/agy: no space left on device` (the kernel's answer at a namespace limit). So it is off by default.
To turn user namespaces off anyway, for `./agybox shell` and `./agybox run` work without agy:

```sh
AGYBOX_DISABLE_USERNS=1 ./agybox shell
```

## Tighter rules

### bwrap reads all of `/etc`

Narrow it to what your tools need, in `sandbox_cmd_bwrap` in [`agybox`](../agybox):

```sh
--ro-bind /etc/passwd /etc/passwd --ro-bind /etc/group /etc/group --ro-bind /etc/ssl /etc/ssl
--ro-bind /etc/ca-certificates /etc/ca-certificates --ro-bind /etc/alternatives /etc/alternatives
--ro-bind /etc/ld.so.cache /etc/ld.so.cache --ro-bind /etc/gitconfig /etc/gitconfig
```

and run `./agybox doctor` after each change. Or use the apptainer or docker backend, whose `/etc` is the image's.

### Pin the image

The images start `FROM ubuntu:24.04`, which moves. Pin it to a digest, in both
[`Dockerfile`](../container/Dockerfile) and [`agybox.def`](../container/agybox.def):

```
FROM ubuntu:24.04@sha256:...
```

### seccomp

Docker applies its default seccomp profile. bwrap and apptainer apply none here. bwrap takes one with `--seccomp FD`,
for example one generated from Docker's default profile. That narrows the system calls the kernel exposes.

## Protect the supply chain

- **agy** comes from Google's release server, checked against the SHA-512 in Google's manifest, over HTTPS. That is the
  same check agy's own installer makes. It is not pinned: `./agybox update` takes the latest. To stay on a version, do
  not run `update`. The previous version is kept, and `ln -sfn VERSION .runtime/agy/current` goes back to it.
- **bubblewrap**, when fetched by `setup`, comes from Ubuntu's archive through `apt-get download`, which checks it against
  apt's signed index.
- **The images** are built from Ubuntu's packages. See [Pin the image](#pin-the-image).

## Stronger boundaries

All three backends share WSL's Linux kernel, which runs in the same VM as your other WSL distros and Docker Desktop. A
kernel bug, or a flaw in WSL's `/init`, could break out of any of them.

| Layer | What it adds | Cost |
|---|---|---|
| A separate WSL distro for agy | Its own filesystem and users. Interop and `/mnt` can be turned off for the whole distro in its `/etc/wsl.conf` (`[interop] enabled=false`, `[automount] enabled=false`) | Another distro to keep up. It still shares the kernel |
| A Hyper-V VM | A separate kernel, with its own limits | Most setup and memory |
| A separate machine | Physical separation | A second machine |

A separate distro is a good second layer to put under this one: install it, set its `/etc/wsl.conf` as above, run
`wsl --terminate` on it, and clone this repository there. Then even an escape from the sandbox finds no Windows drives
and no interop.

The rules for [the workspace](#separate-your-projects) still apply: a stronger boundary does not help if you then run
what the agent wrote, outside, without reading it.
