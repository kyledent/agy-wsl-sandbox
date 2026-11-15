# Network

## How the proxy works

With `AGYBOX_NETWORK=proxy` (the default) or `learn`, the sandbox has a network namespace of its own, with only a
loopback interface. It has no route anywhere, and no DNS. The only way out is a unix socket:

```
agy ──HTTPS_PROXY──▶ relay on 127.0.0.1:3128 ──▶ /run/agybox/proxy.sock ──▶ proxy ──▶ allowed host
     (inside the sandbox)                          (the boundary)            (outside, in WSL)
```

1. `./agybox` starts [`lib/proxy.py`](../lib/proxy.py) outside the sandbox, on a unix socket of its own for this run.
2. Inside, [`lib/inside.sh`](../lib/inside.sh) starts [`lib/relay.py`](../lib/relay.py), which listens on
   `127.0.0.1:3128` and passes each connection to the socket.
3. `HTTPS_PROXY` and `HTTP_PROXY` point at the relay. agy, git, curl, pip and npm honor them.
4. The proxy accepts `CONNECT host:port`, and plain HTTP requests. It lets one through only if:
   - the host is on the allow list, and the port is 443, or one listed with the host, and
   - every address the host resolves to is public. So an allowed name that points at your LAN, a VPN, Windows' loopback
     or a cloud metadata address is refused all the same.
5. It connects to the address it checked, and logs each decision to `.state/proxy.log`.

The proxy stops with `./agybox`, even if `./agybox` is killed.

## The allow list

[`allow/hosts.txt`](../allow/hosts.txt) has what agy needs, as far as is known:

| Host | For |
|---|---|
| `oauth2.googleapis.com`, `accounts.google.com`, `www.googleapis.com`, `antigravity.google` | Sign-in, tokens, the account's details |
| `cloudcode-pa.googleapis.com`, `daily-cloudcode-pa.googleapis.com` | The models. Which one depends on agy's release channel |
| `play.googleapis.com` | agy's usage logging and feature flags |

It was made from runs of agy before and after sign-in, and the hostnames in agy's binary. One host is refused on
purpose: `lh3.googleusercontent.com`, from which agy fetches your account's picture once after sign-in. Nothing needs it. Google Cloud and business accounts may
need the commented hosts in that file as well. **If agy fails after sign-in, run `./agybox hosts`.** It lists what the
proxy refused, most often first.

Your own hosts go in `allow/local.txt`, which git ignores. `./agybox setup` creates it from
[`allow/local.txt.example`](../allow/local.txt.example), with examples for GitHub, PyPI and npm. The proxy rereads both
files when they change, so an edit applies at once, to running sessions too.

```
pypi.org                 # this host only
*.example.com            # any subdomain, not example.com itself
registry.example.com:8443  # port 8443 as well as 443
```

### Learn mode

To find what a project needs, run one session with `learn`. The proxy allows any public host and logs each one:

```sh
AGYBOX_NETWORK=learn ./agybox
./agybox hosts all
```

Then add what you trust to `allow/local.txt`, and go back to `proxy`.

## Choosing hosts

Every host on the list is somewhere the agent can send whatever it can read: the workspace, its home, and any token you
passed in. Some hosts make that easy:

- **Wildcards over big platforms.** `*.googleapis.com` would include `storage.googleapis.com`, where anyone can upload to
  a bucket of their own. That is why the list names each Google host. Avoid `*.amazonaws.com`, `*.cloudfront.net`,
  `*.githubusercontent.com` and the like.
- **Hosts that take uploads from anyone.** Paste sites, `gist.github.com`, `api.github.com` with a token, issue trackers,
  file sharing.
- **The model's own API.** agy sends your prompts and the files it reads to Google; that is how it works. The proxy
  cannot tell an ordinary request from one that carries out more than it should.

## The other modes

| Mode | bwrap | apptainer | docker |
|---|---|---|---|
| `proxy`, `learn` | Its own network namespace | `--net --network none` | `--network none` |
| `none` | The same, without the proxy | The same | The same |
| `open` | WSL's network, shared | WSL's network, shared | Docker's default bridge |

**`none`** is for work that needs no network: agy itself cannot work, as it cannot reach its models, but `./agybox run`
and `./agybox shell` can.

**`open`** shares WSL's network. In mirrored mode (`networkingMode=mirrored` in `.wslconfig`), that includes every
service on Windows' localhost, such as a database, a development server or a desktop app's API. With docker's bridge,
`host.docker.internal` reaches them too. Use it for one session when you need it:

```sh
AGYBOX_NETWORK=open ./agybox
```

## What does not go through the proxy

- **SSH.** `git@github.com:` remotes, `ssh`, `scp` and database clients do not use `HTTPS_PROXY`, and fail. Use HTTPS
  remotes.
- **Programs that ignore the proxy variables.** They fail to connect: the sandbox has no other route.
- **DNS.** There is no resolver in the sandbox. Clients that use a proxy send the name to it, and it resolves the name
  outside.
