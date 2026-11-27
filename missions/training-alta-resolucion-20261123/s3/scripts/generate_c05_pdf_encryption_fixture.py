"""Rebuild the deterministic, genuinely encrypted INF-0084 PDF fixture."""
from __future__ import annotations

import hashlib
from pathlib import Path

PADDING = bytes.fromhex(
    "28bf4e5e4e758a4164004e56fffa01082e2e00b6d0683e802f0ca9fe6453697a"
)


def rc4(key: bytes, data: bytes) -> bytes:
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) & 255
        state[i], state[j] = state[j], state[i]
    i = j = 0
    output = bytearray()
    for value in data:
        i = (i + 1) & 255
        j = (j + state[i]) & 255
        state[i], state[j] = state[j], state[i]
        output.append(value ^ state[(state[i] + state[j]) & 255])
    return bytes(output)


def pad(password: bytes) -> bytes:
    return (password + PADDING)[:32]


def make_pdf(plaintext: bytes = b"C05 protected fixture text", file_id: bytes = bytes.fromhex("c05f0084c05f0084c05f0084c05f0084")) -> bytes:
    user_password, owner_password = b"c05-user", b"c05-owner"
    permissions = -4
    owner_key = hashlib.md5(pad(owner_password)).digest()[:5]
    owner_entry = rc4(owner_key, pad(user_password))
    file_key = hashlib.md5(
        pad(user_password) + owner_entry + permissions.to_bytes(4, "little", signed=True) + file_id
    ).digest()[:5]
    user_entry = rc4(file_key, PADDING)
    object_key = hashlib.md5(file_key + (1).to_bytes(3, "little") + b"\0\0").digest()[:10]
    secret = rc4(object_key, plaintext)
    literal = b"(" + b"".join(f"\\{byte:03o}".encode() for byte in secret) + b")"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R /Subject " + literal + b" >>",
        b"<< /Type /Pages /Kids [] /Count 0 >>",
        b"<< /Filter /Standard /V 1 /R 2 /Length 40 /O <" + owner_entry.hex().encode() + b"> /U <" + user_entry.hex().encode() + b"> /P -4 >>",
    ]
    raw = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(raw))
        raw.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(raw)
    raw.extend(b"xref\n0 4\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        raw.extend(f"{offset:010d} 00000 n \n".encode())
    raw.extend(
        f"trailer\n<< /Size 4 /Root 1 0 R /Encrypt 3 0 R /ID [<{file_id.hex()}><{file_id.hex()}>] >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(raw)


if __name__ == "__main__":
    target = Path(__file__).parents[1] / "fixtures" / "FX-MGL5-INF-0084.pdf"
    target.write_bytes(make_pdf())
    print(hashlib.sha256(target.read_bytes()).hexdigest())
    boundary = target.with_name("FX-MGL5-INF-0084-boundary.pdf")
    boundary.write_bytes(make_pdf(b"", bytes.fromhex("b04e0084b04e0084b04e0084b04e0084")))
    print(hashlib.sha256(boundary.read_bytes()).hexdigest())
