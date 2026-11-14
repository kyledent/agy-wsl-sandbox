#!/usr/bin/env python3
"""The allow-list proxy: the only way out of the sandbox's network.

It runs outside the sandbox and accepts HTTP CONNECT (and plain HTTP) requests. A request goes through only if
its host is on the allow list, its port is allowed, and every address the host resolves to is a public one, so
that an allowed name pointing at your LAN, your VPN or Windows' loopback is still refused. It connects to the
address it checked, not to a second lookup.

    proxy.py --listen unix:/path/to/sock --allow hosts.txt --log proxy.log
    proxy.py --listen tcp:127.0.0.1:3128 --allow hosts.txt --any-public

hosts.txt holds one pattern per line: "example.com" matches that host only, "*.example.com" matches its
subdomains (not example.com itself). "host:port" allows that port as well as 443. Lines starting with # are
comments. The file is read again when it changes, so edits apply without a restart.
"""

import argparse
import asyncio
import ipaddress
import os
import socket
import sys
import time

DEFAULT_PORTS = {443}
MAX_HEADER = 64 * 1024


class AllowList:
    def __init__(self, paths, any_public=False):
        self.paths = paths
        self.any_public = any_public
        self.stamp = None
        self.exact = {}
        self.suffix = {}

    def _load(self):
        stamp = tuple(os.stat(p).st_mtime_ns if os.path.exists(p) else 0 for p in self.paths)
        if stamp == self.stamp:
            return
        exact, suffix = {}, {}
        for path in self.paths:
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                for raw in f:
                    line = raw.split("#", 1)[0].strip().lower()
                    if not line:
                        continue
                    host, ports = line, set(DEFAULT_PORTS)
                    if line.count(":") == 1:
                        host, port = line.split(":")
                        if port.isdigit():
                            ports.add(int(port))
                    table = exact
                    if host.startswith("*."):
                        table, host = suffix, host[1:]   # ".example.com"
                    table.setdefault(host, set()).update(ports)
        self.exact, self.suffix, self.stamp = exact, suffix, stamp

    def ports_for(self, host):
        self._load()
        host = host.lower().rstrip(".")
        if host in self.exact:
            return self.exact[host]
        for suffix, ports in self.suffix.items():
            if host.endswith(suffix):
                return ports
        return {80, 443} if self.any_public else set()


class Log:
    def __init__(self, path):
        self.f = open(path, "a", buffering=1, encoding="utf-8") if path else sys.stderr

    def __call__(self, verdict, target, why=""):
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.f.write(f"{stamp} {verdict:<5} {target}{'  ' + why if why else ''}\n")


async def resolve_public(host, port):
    """The first address of HOST, if all of its addresses are public. Raises ValueError otherwise."""
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
        addrs = [ip]
    except ValueError:
        infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addrs = [ipaddress.ip_address(i[4][0].split("%")[0]) for i in infos]
    if not addrs:
        raise ValueError("no address")
    for a in addrs:
        if not a.is_global:
            raise ValueError(f"resolves to a non-public address {a}")
    return str(addrs[0])


async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def refuse(writer, code, text):
    body = (text + "\n").encode()
    writer.write(f"HTTP/1.1 {code} {text}\r\nContent-Type: text/plain\r\nContent-Length: {len(body)}\r\n"
                 f"Connection: close\r\n\r\n".encode() + body)
    try:
        await writer.drain()
    finally:
        writer.close()


def split_host_port(hostport, default_port):
    if hostport.startswith("["):
        host, _, rest = hostport[1:].partition("]")
        port = rest.lstrip(":") or default_port
    elif hostport.count(":") == 1:
        host, port = hostport.split(":")
    else:
        host, port = hostport, default_port
    return host, int(port)


async def handle(reader, writer, allow, log):
    try:
        head = await reader.readuntil(b"\r\n\r\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
        writer.close()
        return
    lines = head.decode("latin-1").split("\r\n")
    try:
        method, target, version = lines[0].split(" ")
    except ValueError:
        await refuse(writer, 400, "Bad Request")
        return

    if method.upper() == "CONNECT":
        host, port = split_host_port(target, 443)
        rest = b""
    else:
        # Plain HTTP through a proxy: an absolute URI
        if not target.lower().startswith("http://"):
            await refuse(writer, 400, "Bad Request")
            return
        hostport, _, path = target[7:].partition("/")
        host, port = split_host_port(hostport, 80)
        headers = [h for h in lines[1:] if h and not h.lower().startswith(("proxy-", "connection:"))]
        rest = (f"{method} /{path} {version}\r\n" + "\r\n".join(headers) +
                "\r\nConnection: close\r\n\r\n").encode("latin-1")

    label = f"{method.upper()} {host}:{port}"
    if port not in allow.ports_for(host):
        log("DENY", label, "not on the allow list")
        await refuse(writer, 403, "Forbidden by the sandbox's allow list")
        return
    try:
        addr = await resolve_public(host, port)
        up_reader, up_writer = await asyncio.wait_for(asyncio.open_connection(addr, port), 15)
    except ValueError as e:
        log("DENY", label, str(e))
        await refuse(writer, 403, "Forbidden: not a public address")
        return
    except (OSError, asyncio.TimeoutError) as e:
        log("FAIL", label, str(e) or type(e).__name__)
        await refuse(writer, 502, "Bad Gateway")
        return

    log("ALLOW", label, addr)
    if method.upper() == "CONNECT":
        writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        await writer.drain()
    else:
        up_writer.write(rest)
        await up_writer.drain()
    await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", required=True, help="unix:PATH or tcp:HOST:PORT")
    ap.add_argument("--allow", action="append", required=True, help="allow-list file; repeatable")
    ap.add_argument("--log", help="log file (default: stderr)")
    ap.add_argument("--any-public", action="store_true",
                    help="learn mode: allow any host on ports 80 and 443, still only at public addresses")
    args = ap.parse_args()

    allow, log = AllowList(args.allow, args.any_public), Log(args.log)
    handler = lambda r, w: handle(r, w, allow, log)  # noqa: E731
    kind, _, where = args.listen.partition(":")
    if kind == "unix":
        if os.path.exists(where):
            os.unlink(where)
        old = os.umask(0o077)
        server = await asyncio.start_unix_server(handler, path=where, limit=MAX_HEADER)
        os.umask(old)
    elif kind == "tcp":
        host, port = where.rsplit(":", 1)
        server = await asyncio.start_server(handler, host, int(port), limit=MAX_HEADER)
    else:
        sys.exit("--listen must be unix:PATH or tcp:HOST:PORT")
    log("START", args.listen)

    # Stop with ./agybox, even when it is killed and cannot stop us
    parent = os.getppid()

    async def watch_parent():
        while os.getppid() == parent:
            await asyncio.sleep(1)
        server.close()

    async with server:
        await asyncio.wait([asyncio.create_task(server.serve_forever()), asyncio.create_task(watch_parent())],
                           return_when=asyncio.FIRST_COMPLETED)
    if kind == "unix" and os.path.exists(where):
        os.unlink(where)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
