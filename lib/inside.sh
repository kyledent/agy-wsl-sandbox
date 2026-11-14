#!/bin/sh
# The first thing that runs in the sandbox, in every backend: sets PATH, starts the relay to the proxy when there is
# one, then runs the command it was given.
export PATH="/opt/agy:$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export TMPDIR=/tmp

if [ -S /run/agybox/proxy.sock ]; then
    python3 /opt/agybox/relay.py 3128 /run/agybox/proxy.sock &
    # Wait until it listens: starting python from an image can take a moment
    n=0
    until python3 -c 'import socket; socket.create_connection(("127.0.0.1", 3128), 0.2).close()' 2>/dev/null; do
        n=$((n + 1))
        if [ "$n" -ge 50 ]; then
            echo "agybox: the relay to the proxy did not start" >&2
            break
        fi
        sleep 0.1
    done
fi

exec "$@"
