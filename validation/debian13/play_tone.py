#!/usr/bin/env python3
"""Write a one-second audible tone. Presence of a player is not success."""
from __future__ import annotations

import math
import struct
import sys
import wave


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/louksna-tone.wav"
    rate = 22050
    with wave.open(path, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = bytearray()
        for i in range(rate):
            sample = int(12000 * math.sin(2 * math.pi * 440 * i / rate))
            frames += struct.pack("<h", sample)
        handle.writeframes(frames)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
