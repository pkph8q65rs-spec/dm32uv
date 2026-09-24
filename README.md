# dm32uv-cps-bridge

A small serial proxy that lets the **official Baofeng DM-32UV CPS** (customer programming software) connect to radios that ignore it.

## The problem

On some DM-32UV firmware, the radio only answers the `PSEARCH` programming handshake when the serial adapter holds **RTS = HIGH and DTR = LOW**. The official CPS drives the opposite levels, so it reports "no connection" no matter which COM port you pick. This finding comes from [fivelidz/dm32uv-linux](https://github.com/fivelidz/dm32uv-linux), which works around it with a standalone Python programmer.

This project takes a different route: keep using the real CPS, and put a proxy between it and the cable.

```
CPS --COM6==(com0com pair)==COM5-- cps_bridge.py --COM4--> USB cable --> radio
                                        (forces RTS=HIGH, DTR=LOW)
```

## Status

- Tested on Windows 11, CPS v1.60, a CH340-based programming cable, radio firmware strings `DM32.01.01.046` and `DM32.01.01.047`.
- **Reading from the radio through the CPS works.**
- Writing to the radio through the bridge is **untested**. Back up first and use at your own risk; a bad write can leave a radio unusable.

## Requirements

- Windows, Python 3, `pip install pyserial`
- [com0com](https://com0com.sourceforge.net/) (virtual null-modem driver). Windows 10/11 only loads kernel drivers signed through Microsoft's dev portal, so you may need a signed community build and possibly test-signing mode (`bcdedit /set testsigning on`, then reboot). Understand what that changes before doing it.
- The DM-32UV CPS from the [Baofeng download page](https://www.baofengradio.com/pages/download)

## Setup

1. Install com0com and create a pair, e.g. `CNCA0` = COM6 and `CNCB0` = COM5 (check Device Manager for the numbers).
2. Close the CPS, then edit its `cps.ini` (in the CPS install folder):
   ```ini
   [function]
   lang=en

   [com]
   port=6
   ```
   `port=` is the CPS end of the pair. This CPS build has no port picker in its UI, so the ini is the only place to set it. `lang=en` switches the interface from Chinese to English.
3. Start the bridge: `python cps_bridge.py --virtual COM5`
4. Open the CPS, **power-cycle the radio** (normal power-on, no buttons held), then Read.

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--virtual` | `COM5` | Virtual port the bridge opens (partner of the CPS's port) |
| `--real` | auto | Real port; by default the first port whose description contains `--match` |
| `--match` | `CH340` | Description substring for auto-detect (e.g. `FT232` for FTDI cables) |
| `--baud` | `115200` | Baud rate on both ports |
| `--unsolicited` | `2.0` | Drop radio bytes arriving this many seconds after the CPS last transmitted |
| `--quiet` | off | Do not log each transfer |

The bridge re-detects the cable if it drops off USB, which cheap CH340 adapters do.

## Why it is written this way

- The CPS retries `PSEARCH` after a short timeout. Extra latency in the relay produces a duplicate reply and desyncs the handshake, so the relay avoids `flush()` (pyserial's Windows implementation polls in 50 ms steps) and uses `read(1)` plus `in_waiting` instead of a fixed-size read that waits out its timeout.
- Bytes the radio sends long after the CPS last spoke are stale and are dropped.

## Troubleshooting

- **No connection:** power-cycle the radio before every attempt; the handshake is finicky.
- **Access denied:** only one program can hold a port. Close anything else using the cable.
- **Cable vanishes mid-transfer:** try another cable or a direct USB port, and disable USB power saving for the hub.
- **Do not** hold PTT+SK1 at power-on; that is firmware-upgrade mode, not programming mode.

## Credits and disclaimer

The RTS/DTR discovery is from [fivelidz/dm32uv-linux](https://github.com/fivelidz/dm32uv-linux). This project is not affiliated with Baofeng. Provided as-is, with no warranty.

## License

MIT, see `LICENSE`.
