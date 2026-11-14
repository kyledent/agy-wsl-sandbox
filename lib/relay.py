#!/usr/bin/env python3
"""Inside the sandbox: listen on 127.0.0.1:PORT and pass each connection to the proxy's unix socket.

The sandbox has its own network namespace with only a loopback interface, so this relay is its only way out, and
the proxy at the other end decides where traffic may go.

    relay.py 3128 /run/agy-proxy.sock
"""

import asyncio
import sys


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


async def main(port, sock):
    async def handle(reader, writer):
        try:
            up_reader, up_writer = await asyncio.open_unix_connection(sock)
        except OSError:
            writer.close()
            return
        await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer))

    server = await asyncio.start_server(handle, "127.0.0.1", port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), sys.argv[2]))
