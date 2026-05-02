"""Cabinet electronic lock control via GPIO."""
import logging
import threading
import time

from afracs import config

log = logging.getLogger(__name__)

try:
    import RPi.GPIO as _GPIO
    _GPIO.setwarnings(False)
    _GPIO.setmode(_GPIO.BCM)
    _HAS_GPIO = True
    log.info("RPi.GPIO backend active")
except ImportError:
    _GPIO = None
    _HAS_GPIO = False
    log.info("RPi.GPIO not available — lock pulses will be simulated")


class CabinetLock:
    def __init__(self, pin: int, pulse_seconds: float = config.LOCK_PULSE_SECONDS):
        self._pin = pin
        self._pulse_seconds = pulse_seconds
        if _HAS_GPIO:
            _GPIO.setup(pin, _GPIO.OUT, initial=_GPIO.LOW)
            log.info("CabinetLock ready on BCM pin %d (pulse=%.1fs)", pin, pulse_seconds)

    def unlock(self) -> None:
        log.info("Firing lock on BCM pin %d for %.1fs", self._pin, self._pulse_seconds)
        if _HAS_GPIO:
            _GPIO.output(self._pin, _GPIO.HIGH)
            time.sleep(self._pulse_seconds)
            _GPIO.output(self._pin, _GPIO.LOW)
        else:
            log.info("(simulated) pin %d HIGH → sleep %.1fs → LOW", self._pin, self._pulse_seconds)
            time.sleep(self._pulse_seconds)

    def close(self) -> None:
        if _HAS_GPIO:
            _GPIO.output(self._pin, _GPIO.LOW)


class CabinetLockBank:
    def __init__(self, pin_map: dict[str, int] | None = None) -> None:
        if pin_map is None:
            pin_map = config.CABINET_LOCK_PINS
        self._locks: dict[str, CabinetLock] = {
            cab_id: CabinetLock(pin) for cab_id, pin in pin_map.items()
        }
        log.info("CabinetLockBank: %s", {k: v._pin for k, v in self._locks.items()})

    def unlock(self, cabinet_id: str) -> None:
        lock = self._locks.get(cabinet_id)
        if lock is None:
            log.warning("No lock configured for cabinet %r", cabinet_id)
            return
        threading.Thread(target=lock.unlock, daemon=True).start()

    def cabinet_ids(self) -> list[str]:
        return list(self._locks.keys())

    def close(self) -> None:
        for lock in self._locks.values():
            lock.close()
        if _HAS_GPIO:
            _GPIO.cleanup()
