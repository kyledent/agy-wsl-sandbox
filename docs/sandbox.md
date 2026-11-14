# Sandbox

## What it can do

| | Inside the sandbox |
|---|---|
| **Reads** | The workspace, its home, the system's programs and `/etc` (bwrap) or the image (docker, apptainer), agy |
| **Writes** | The workspace, its home, `/tmp` |
| **Starts programs** | Yes, and they stay in the sandbox |
| **Sees processes** | Its own only |
| **Network** | Set by `AGYBOX_NETWORK`: the proxy by default. See [Network](network.md) |
| **Environment** | Only what `./agybox` sets, and the variables in `AGYBOX_PASS_ENV` |
| **Limits** | Memory, CPUs and processes, if set in `.env` |

It cannot read or change your home, this folder's `.env`, `.state` (other than its home) or `.runtime`, agy's binary,
the sandbox's own scripts, or the Windows drives.

## WSL's ways out, and how each is closed

| Way out | What it would allow | Closed by |
|---|---|---|
| `/mnt/c` and the other drive mounts | Every file of your Windows user | They are not mounted in the sandbox |
| Interop: running a Windows `.exe` | A program that runs in Windows, outside the sandbox and outside Linux | WSL registers `.exe` files with the kernel, and the kernel keeps that registration in every namespace. So copying `cmd.exe` into the workspace would work as an `.exe` anywhere. What stops it is that WSL's `/init` then needs `/run/WSL`'s interop socket and the real process tree, which the sandbox does not have |
| `WSL_INTEROP`, `/run/WSL` | The same, more directly | Not in the environment, not mounted |
| Your D-Bus session | Starting programs through systemd or a desktop service, outside the sandbox; the keyring | Not mounted. agy then keeps its token in a file in the sandbox's home |
| Windows' localhost (mirrored mode) | Any service listening on Windows' or WSL's 127.0.0.1 | The sandbox's own network namespace |
| Typing into your terminal (`TIOCSTI`) | Commands that your shell runs after agy exits | The kernel, when `dev.tty.legacy_tiocsti` is 0. The setting came in Linux 6.2, and its default depends on how the kernel was built. WSL's 6.18 kernel has it at 0 |

`./agybox doctor` checks each of these.

## What `doctor` checks

Run it after every change to `.env`, to WSL, or to this repository:

```
Sandbox (backend: bwrap, network: proxy)
  ok    it can run a program at all
  ok    agy runs (1.5.9)
  ok    git, python3 and curl are there
  ok    it can write the workspace
  ok    it can write its home
Files
  ok    it cannot read your home (/home/you/.agybox-doctor-canary)
  ok    it cannot write your home
  ok    it cannot read this folder's .state and .env
  ok    it cannot change agy's binary
  ok    it cannot change its entry script
  ok    it cannot see the Windows drives
Processes and services
  ok    it cannot see the host's processes
  ok    it cannot make user namespaces of its own
  ok    it cannot reach WSL's interop socket
  ok    it cannot reach your D-Bus session
  ok    it cannot start a Windows program (cmd.exe in the workspace)
  ok    it cannot type into your terminal (the kernel refuses TIOCSTI)
Network (proxy)
  ok    it can reach agy's sign-in service through the proxy
  ok    the proxy refuses a host not on the allow list
  ok    it cannot connect around the proxy
  ok    it cannot look up names (no DNS)
  ok    it cannot reach a service on this machine's loopback
  ok    the proxy refuses this machine's loopback
```

The Windows program check copies `cmd.exe` into the workspace and tries to run it from inside the sandbox. It passes if
the program does not print what it was asked to.

## Limits

- **Anything the agent writes in the workspace is untrusted once you use it outside.** It can change `.git/hooks`,
  `.git/config`, `package.json` scripts, `.vscode/tasks.json` and `Makefile`s, and those run with your full rights when you
  use git, npm or VS Code outside the sandbox. Read the diff first. See
  [Hardening](hardening.md#separate-your-projects).
- **agy's sign-in token is in the sandbox's home, and the agent can read it.** With it, someone could use your Antigravity
  account. They would still need a way to send it out, which the proxy limits to the hosts on the list.
- **Variables in `AGYBOX_PASS_ENV` are readable by the agent.** `GH_TOKEN` is passed if you set it.
- **The agent does not ask before it runs a command** with `always-proceed`. The sandbox limits what a bad command can
  reach, but within the workspace it can still delete your work. Use version control.
- **It is one layer.** All three backends share WSL's Linux kernel. They do not protect against a kernel bug.
- **`/etc` is readable with bwrap.** It holds no secrets on a standard Ubuntu: `/etc/shadow` and SSH host keys are not
  readable by your user anyway. Check for others you have added.
