"""Cabinet electronic lock control via GPIO."""
import threading
import time

from gpiozero import Buzzer as GpioBuzzer, OutputDevice

from afracs import config


class Buzzer:
    def __init__(self, pin: int = config.GPIO_BUZZER_PIN):
        self._device = GpioBuzzer(pin)

    def success(self) -> None:
        """One short beep for success."""
        self._device.beep(on_time=0.1, off_time=0.1, n=1, background=True)

    def failure(self) -> None:
        """Two quick beeps for failure."""
        self._device.beep(on_time=0.1, off_time=0.1, n=2, background=True)

    def alert(self) -> None:
        """Rapid beeps for alert state."""
        self._device.beep(on_time=0.05, off_time=0.05, n=10, background=True)

    def close(self) -> None:
        self._device.close()


class CabinetLock:
    def __init__(
        self,
        pin: int = config.GPIO_LOCK_PIN,
        pulse_seconds: float = config.LOCK_PULSE_SECONDS,
    ):
        self._device = OutputDevice(pin, active_high=True, initial_value=False)
        self._pulse_seconds = pulse_seconds
        self._secured = True

    def unlock(self) -> None:
        self._device.on()
        self._secured = False
        time.sleep(self._pulse_seconds)
        self._device.off()
        self._secured = True

    def is_secured(self) -> bool:
        return self._secured

    def close(self) -> None:
        self._device.close()


class CabinetLockBank:
    def __init__(self, pin_map: dict[str, int] | None = None) -> None:
        if pin_map is None:
            pin_map = config.CABINET_LOCK_PINS
        self._locks: dict[str, CabinetLock] = {
            cab_id: CabinetLock(pin) for cab_id, pin in pin_map.items()
        }

    def unlock(self, cabinet_id: str) -> None:
        lock = self._locks.get(cabinet_id)
        if lock is None:
            return
        threading.Thread(target=lock.unlock, daemon=True).start()

    def cabinet_ids(self) -> list[str]:
        return list(self._locks.keys())

    def close(self) -> None:
        for lock in self._locks.values():
            lock.close()
