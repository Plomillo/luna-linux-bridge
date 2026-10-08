#!/bin/sh
# Explicitly provision local-only TLS identities. Never starts/enables systemd.
set -eu
umask 077

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: execute with sudo; this provisions root-controlled TLS policy." >&2
  exit 2
fi
if [ -z "${SUDO_UID:-}" ] || [ "$SUDO_UID" -eq 0 ]; then
  echo "ERROR: invoke with sudo from the intended owner account (not a root login)." >&2
  exit 2
fi

OWNER_UID="$SUDO_UID"
OWNER_HOME="$(getent passwd "$OWNER_UID" | cut -d: -f6)"
[ -n "$OWNER_HOME" ] && [ -d "$OWNER_HOME" ] || { echo "ERROR: owner home not found" >&2; exit 2; }

BASE=/etc/louksna/remote-bridge
TLS="$BASE/tls"
CLIENT="$OWNER_HOME/.config/louksna/mtls"
CONFIG="$BASE/mtls.json"

# Fail closed: never overwrite a prior trust configuration or identity.
for p in "$CONFIG" "$TLS" "$CLIENT"; do
  if [ -e "$p" ] || [ -L "$p" ]; then
    echo "ERROR: existing trust material found at $p; refusing overwrite." >&2
    exit 3
  fi
done

install -d -o root -g root -m 0755 "$BASE"
install -d -o root -g root -m 0700 "$TLS"
install -d -o "$OWNER_UID" -g "$(id -gn "$OWNER_UID")" -m 0700 "$OWNER_HOME/.config"
install -d -o "$OWNER_UID" -g "$(id -gn "$OWNER_UID")" -m 0700 "$OWNER_HOME/.config/louksna"
install -d -o "$OWNER_UID" -g "$(id -gn "$OWNER_UID")" -m 0700 "$CLIENT"

cleanup() {
  # Partial provisioning must never be mistaken for a complete config.
  if [ ! -f "$CONFIG" ]; then
    rm -f "$TLS/ca.key" "$TLS/ca.pem" "$TLS/server.key" "$TLS/server.pem" "$TLS/server.csr" "$TLS/server.ext" "$TLS/client.csr" "$TLS/client.ext" "$TLS/client.pem" "$TLS/client.key" "$TLS/ca.srl"
    rm -rf "$CLIENT"
  fi
}
trap cleanup EXIT HUP INT TERM

openssl req -x509 -newkey rsa:3072 -nodes -sha256 \
  -keyout "$TLS/ca.key" -out "$TLS/ca.pem" -days 365 \
  -subj "/CN=LOUKSNA Local mTLS CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
chmod 0600 "$TLS/ca.key"
chmod 0644 "$TLS/ca.pem"

openssl req -new -newkey rsa:3072 -nodes -sha256 \
  -keyout "$TLS/server.key" -out "$TLS/server.csr" \
  -subj "/CN=localhost"
chmod 0600 "$TLS/server.key"
cat > "$TLS/server.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost,IP:127.0.0.1
EOF
openssl x509 -req -sha256 -in "$TLS/server.csr" \
  -CA "$TLS/ca.pem" -CAkey "$TLS/ca.key" -CAcreateserial \
  -out "$TLS/server.pem" -days 180 -extfile "$TLS/server.ext"
chmod 0644 "$TLS/server.pem"

openssl req -new -newkey rsa:3072 -nodes -sha256 \
  -keyout "$CLIENT/client.key" -out "$TLS/client.csr" \
  -subj "/CN=LOUKSNA Local Owner Client"
chmod 0600 "$CLIENT/client.key"
cat > "$TLS/client.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature
extendedKeyUsage=clientAuth
EOF
openssl x509 -req -sha256 -in "$TLS/client.csr" \
  -CA "$TLS/ca.pem" -CAkey "$TLS/ca.key" -CAcreateserial \
  -out "$CLIENT/client.pem" -days 180 -extfile "$TLS/client.ext"
chmod 0644 "$CLIENT/client.pem"
cp "$TLS/ca.pem" "$CLIENT/ca.pem"
chown "$OWNER_UID:$(id -gn "$OWNER_UID")" "$CLIENT/client.key" "$CLIENT/client.pem" "$CLIENT/ca.pem"
chmod 0600 "$CLIENT/client.key"
chmod 0644 "$CLIENT/client.pem" "$CLIENT/ca.pem"

CLIENT_PIN="$(openssl x509 -in "$CLIENT/client.pem" -outform DER | sha256sum | cut -d' ' -f1)"
SERVER_PIN="$(sha256sum "$TLS/server.pem" | cut -d' ' -f1)"
CA_PIN="$(sha256sum "$TLS/ca.pem" | cut -d' ' -f1)"
python3 - "$CONFIG" "$TLS/server.pem" "$TLS/server.key" "$TLS/ca.pem" "$CLIENT_PIN" "$SERVER_PIN" "$CA_PIN" <<'PY'
import json, os, sys, tempfile
config, server_cert, server_key, ca, client_pin, server_pin, ca_pin = sys.argv[1:]
data = {
    "schema": "LRB_MTLS_READONLY_GATEWAY/0.3",
    "server_cert": server_cert,
    "server_key": server_key,
    "client_ca": ca,
    "client_cert_sha256": client_pin,
    "server_cert_sha256": server_pin,
    "client_ca_sha256": ca_pin,
}
directory = os.path.dirname(config)
fd, tmp = tempfile.mkstemp(prefix=".mtls.json.", dir=directory, text=True)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=True, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.chown(tmp, 0, 0)
    os.replace(tmp, config)
except BaseException:
    try: os.unlink(tmp)
    except FileNotFoundError: pass
    raise
PY
chmod 0600 "$CONFIG"
chown root:root "$CONFIG"

# Validate against the installed gateway's real fail-closed checks before success.
PYTHONPATH=/usr/lib/louksna/bridge python3 - "$CONFIG" <<'PY'
import sys
import mtls_gateway
cfg = mtls_gateway.read_config(sys.argv[1], enforce_root=True)
print("CONFIG_VALIDATED schema=" + cfg["schema"])
PY

# Remove signing key and transient CSRs/extensions; retain CA certificate for server trust.
rm -f "$TLS/ca.key" "$TLS/server.csr" "$TLS/server.ext" "$TLS/client.csr" "$TLS/client.ext" "$TLS/ca.srl"
trap - EXIT HUP INT TERM
echo "PROVISIONED: $CONFIG"
echo "CLIENT_IDENTITY: $CLIENT"
echo "SERVICE_STATE: left disabled and stopped; activation is a separate reviewed step."
