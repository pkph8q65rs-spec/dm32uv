#!/usr/bin/env python3
"""Serial proxy between the Baofeng DM-32UV CPS and the radio's USB cable.

The CPS talks to one end of a com0com virtual pair; this script opens the other
end plus the real cable and relays bytes, holding RTS=HIGH / DTR=LOW on the real
port, which is what the radio's PSEARCH handshake needs.
"""
import argparse
import threading
import time

import serial
import serial.tools.list_ports

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--virtual", default="COM5", help="virtual port this script opens (the CPS uses its partner)")
ap.add_argument("--real", default=None, help="real serial port; default: auto-detect by description")
ap.add_argument("--match", default="CH340", help="description substring used for auto-detect")
ap.add_argument("--baud", type=int, default=115200)
ap.add_argument("--unsolicited", type=float, default=2.0,
                help="drop radio bytes arriving this many seconds after the CPS last transmitted")
ap.add_argument("--quiet", action="store_true", help="do not log every transfer")
args = ap.parse_args()


def log(msg, always=False):
    if always or not args.quiet:
        print(msg, flush=True)


def find_real():
    if args.real:
        return args.real
    for p in serial.tools.list_ports.comports():
        if args.match in (p.description or ""):
            return p.device
    return None


def read_chunk(src):
    # read(1) returns as soon as a byte arrives; then take whatever else is queued.
    b = src.read(1)
    if not b:
        return b
    n = src.in_waiting
    return b + src.read(n) if n else b


virt = serial.Serial(args.virtual, args.baud, timeout=0.02)
last_cps_tx = [0.0]
log(f"Bridge starting (virtual={args.virtual}, real={args.real or 'auto:' + args.match})", True)

while True:
    port = find_real()
    if not port:
        log("Radio cable not found, waiting...", True)
        time.sleep(2)
        continue
    try:
        real = serial.Serial(port, args.baud, timeout=0.02)
        real.rts = True
        real.dtr = False
    except Exception as e:
        log(f"Failed to open {port}: {e}, retrying...", True)
        time.sleep(2)
        continue

    real.reset_input_buffer()
    virt.reset_input_buffer()
    log(f"Bridge up: {args.virtual} <-> {port} (RTS=HIGH, DTR=LOW)", True)
    stop = threading.Event()

    def cps_to_radio():
        while not stop.is_set():
            try:
                data = read_chunk(virt)
                if data:
                    last_cps_tx[0] = time.time()
                    real.write(data)
                    log(f"[CPS->radio] {len(data)}")
            except Exception as e:
                log(f"[CPS->radio] error: {e}", True)
                stop.set()

    def radio_to_cps():
        while not stop.is_set():
            try:
                data = read_chunk(real)
                if data:
                    if time.time() - last_cps_tx[0] > args.unsolicited:
                        log(f"[radio->CPS] dropped {len(data)} unsolicited")
                        continue
                    virt.write(data)
                    log(f"[radio->CPS] {len(data)}")
            except Exception as e:
                log(f"[radio->CPS] error: {e}", True)
                stop.set()

    t1 = threading.Thread(target=cps_to_radio, daemon=True)
    t2 = threading.Thread(target=radio_to_cps, daemon=True)
    t1.start()
    t2.start()
    while t1.is_alive() and t2.is_alive() and not stop.is_set():
        time.sleep(0.5)
    try:
        real.close()
    except Exception:
        pass
    log("Radio port dropped, re-detecting...", True)
    time.sleep(1)
