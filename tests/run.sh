#!/usr/bin/env bash
# Tests that need no sandbox: the scripts parse, and the proxy allows and refuses what it should. The sandbox
# itself is tested by ./agybox doctor, on each backend.
#
#   tests/run.sh
set -uo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
TMP=$(mktemp -d)
FAILS=0
trap 'kill $(jobs -p) 2>/dev/null; rm -rf "$TMP"' EXIT

ok()   { echo "  ok    $1"; }
fail() { echo "  FAIL  $1"; FAILS=$(( FAILS + 1 )); }
check() { local label=$1; shift; if "$@" >/dev/null 2>&1; then ok "$label"; else fail "$label"; fi; }

echo "Scripts"
check "agybox parses" bash -n "$ROOT/agybox"
check "inside.sh parses" sh -n "$ROOT/lib/inside.sh"
check "proxy.py and relay.py compile" python3 -m py_compile "$ROOT/lib/proxy.py" "$ROOT/lib/relay.py"
if command -v shellcheck >/dev/null; then
    check "shellcheck is clean" shellcheck -x "$ROOT/agybox" "$ROOT/lib/inside.sh" "$ROOT/tests/run.sh" "$ROOT/container/packages.sh"
fi

echo "Allow list matching"
cat > "$TMP/allow.txt" <<'EOF'
# a comment
exact.example.com
*.wild.example.com
ports.example.com:8443
localhost
127.0.0.1
EOF
check "matching rules" python3 - "$ROOT/lib" "$TMP/allow.txt" <<'EOF'
import sys
sys.path.insert(0, sys.argv[1])
from proxy import AllowList
a = AllowList([sys.argv[2]])
assert a.ports_for("exact.example.com") == {443}
assert a.ports_for("EXACT.example.com.") == {443}
assert a.ports_for("sub.exact.example.com") == set()
assert a.ports_for("a.wild.example.com") == {443}
assert a.ports_for("a.b.wild.example.com") == {443}
assert a.ports_for("wild.example.com") == set()
assert a.ports_for("evilwild.example.com") == set()
assert a.ports_for("ports.example.com") == {443, 8443}
assert a.ports_for("other.com") == set()
assert AllowList([sys.argv[2]], any_public=True).ports_for("other.com") == {80, 443}
EOF

echo "Proxy"
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
python3 "$ROOT/lib/proxy.py" --listen "tcp:127.0.0.1:$PORT" --allow "$TMP/allow.txt" --log "$TMP/proxy.log" &
sleep 0.5
# The status of the request, or of the proxy's answer to CONNECT when the tunnel was refused
code() {
    local c
    c=$(curl -s -m 10 -o /dev/null -w '%{http_code} %{http_connect}' -x "http://127.0.0.1:$PORT" "$@" 2>/dev/null)
    case "$c" in "000 "*) echo "${c#* }" ;; *) echo "${c%% *}" ;; esac
}
refused() { [ "$(code "$1")" = 403 ]; }
check "refuses a host not on the list" refused https://not-listed.example.org/
check "refuses an allowed name at a loopback address" refused https://localhost/
check "refuses an allowed loopback address" refused https://127.0.0.1/
check "refuses a port not allowed" refused https://exact.example.com:8443/
check "refuses plain HTTP on a port not allowed" refused http://localhost/
check "logs refusals" grep -q 'DENY  CONNECT not-listed.example.org:443' "$TMP/proxy.log"

# With the internet: an allowed host goes through
echo 'oauth2.googleapis.com' >> "$TMP/allow.txt"
c=$(code https://oauth2.googleapis.com/)
if [ "$c" = 000 ] && ! curl -s -m 5 -o /dev/null https://oauth2.googleapis.com/; then
    echo "  skip  allowed host: no internet"
elif [ "$c" != 000 ] && [ "$c" != 403 ] && [ "$c" != 502 ]; then
    ok "lets an allowed host through, and rereads the list when it changes (HTTP $c)"
else
    fail "lets an allowed host through (HTTP $c)"
fi

echo
if [ "$FAILS" -gt 0 ]; then echo "$FAILS failed."; exit 1; fi
echo "All tests passed."
