# Troubleshooting

## agy fails after sign-in, or a tool cannot download

The proxy probably refused a host. See which:

```sh
./agybox hosts
```

Add the ones you trust to `allow/local.txt`. The change applies at once.

Known refusals:

| Host | Meaning |
|---|---|
| `lh3.googleusercontent.com` | agy's fetch of your account's picture. Harmless, and refused on purpose |
| `aicode.googleapis.com`, `jetski-webchannel.googleapis.com`, `www.gstatic.com` | Your account's settings, Remote Control's relay and the plugin marketplace. Allowed since 15 November 2026: update this repository |
| A host your project uses, such as an API | Your project's need, not agy's: add it to `allow/local.txt` |
| `daily-cloudcode-pa.googleapis.com` | agy's models on its daily channel. Allowed since this was found; with an older copy of `allow/hosts.txt`, agy fails with "Eligibility check failed ... loadCodeAssist". Update this repository, or add the host to `allow/local.txt` | To see everything a session uses, run it once
with `AGYBOX_NETWORK=learn`, then `./agybox hosts all`. See [Network](network.md).

If agy needs a host that is not in `allow/hosts.txt`, please report it, so that the list can be fixed for everyone.

## Signing in

agy prints a link to `accounts.google.com`. Open it in your Windows browser, sign in, and paste the code the page shows
into agy. agy waits about a minute; if it gives up, run `./agybox` again.

If the page tries to return to agy but nothing happens, paste the code instead. The sandbox has no route for a browser
to reach agy directly.

## agy's commands fail with "no space left on device"

```
Command failed to run: fork/exec /opt/agy/agy: no space left on device
```

This is not about disk space. agy runs each command by starting itself again in new namespaces, and the kernel answers
`ENOSPC` when a namespace cannot be made because of a limit. The usual cause was this repository: until 15 November
2026, bwrap ran with `--disable-userns`, which sets that limit inside the sandbox. Update this
repository (`git pull`), or check that `.env` does not set `AGYBOX_DISABLE_USERNS=1`. Then `./agybox doctor` should pass
"agy can make its own sandbox for commands".

A full `/tmp` can also report it, as `/tmp` in the sandbox is in memory: `./agybox run df -h /tmp`.

## `doctor` fails

| Check | Likely cause |
|---|---|
| "it can run a program at all" | bwrap: user namespaces are turned off (`/proc/sys/user/max_user_namespaces` is 0). apptainer: see its error with `./agybox run true` |
| "agy runs" | agy's download is broken: `rm -rf .runtime/agy`, then `./agybox setup` |
| "git, python3 and curl are there" | bwrap: install them in WSL. docker, apptainer: add them to `container/packages.sh` |
| "it cannot see the Windows drives" | A mount you added, or a changed backend |
| "it cannot start a Windows program" | **Stop and report it.** The sandbox can reach WSL's interop |
| "it cannot type into your terminal" | The kernel allows `TIOCSTI`. On Linux 6.2 or newer: `sudo sysctl dev.tty.legacy_tiocsti=0`. On WSL, `wsl --update` brings a newer kernel |
| "it can reach agy's sign-in service through the proxy" | No internet outside either, or (docker) the proxy's socket does not work in the container |
| "agy can make its own sandbox for commands" | docker: its default seccomp profile refuses new user namespaces, so agy's commands will fail; use bwrap or apptainer. bwrap: `AGYBOX_DISABLE_USERNS=1` is set |
| Any "cannot" check that fails | **Do not use that backend** until it is understood. Please report it |

## apptainer: "failed to mount binfmt_misc filesystem"

`apptainer build --fakeroot` cannot mount `binfmt_misc` in WSL. `./agybox setup` retries with `--ignore-subuid`, which
works there. If both fail, check that your user has a range in `/etc/subuid`, or build the image elsewhere and copy it to
`.runtime/agybox.sif`. Then `echo` the recipe hash (see `recipe_hash` in `agybox`) into `.runtime/agybox.sif.recipe`.

## docker: "could not be found in this WSL 2 distro"

Turn on Docker Desktop's integration for your distro: **Settings → Resources → WSL integration**. Then open a new WSL
terminal.

## A tool works outside but not inside

- **bwrap:** tools in your home (`~/.local`, `~/.nvm`, `~/.cargo`) are not in the sandbox. Install them system-wide, or
  inside, with `./agybox shell`, into the sandbox's home.
- **docker, apptainer:** add them to `container/packages.sh`.
- **Anything that uses SSH** cannot reach the network: use HTTPS.

## The memory limit

When `AGYBOX_MEMORY` is reached, the kernel kills the process that asked for more, such as a build. agy carries on.
`dmesg` (outside) shows which process it was.

## Starting again

```sh
rm -rf .state/home      # agy's settings, sign-in and conversations
rm -rf .runtime         # agy, bwrap and the image; ./agybox setup brings them back
```
