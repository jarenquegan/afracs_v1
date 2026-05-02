"""Cabinet electronic lock control via GPIO."""
import threading
import time

from gpiozero import PWMOutputDevice, OutputDevice

from afracs import config


class Buzzer:
    def __init__(self, pin: int = config.GPIO_BUZZER_PIN):
        # We use PWM to "drive" the buzzer at a specific frequency
        self._device = PWMOutputDevice(pin, initial_value=0, frequency=config.BUZZER_FREQUENCY)

    def _beep(self, n: int, duration: float = 0.1, duty: float = 0.5) -> None:
        def run():
            for _ in range(n):
                self._device.value = duty
                time.sleep(duration)
                self._device.value = 0
                time.sleep(duration)
        threading.Thread(target=run, daemon=True).start()

    def _siren(self, loops: int = 1) -> None:
        """Sweeps frequency to create a louder, more piercing sound."""
        def run():
            orig_freq = self._device.frequency
            for _ in range(loops):
                # Sweep from 2000Hz to 4000Hz
                for f in range(2000, 4001, 200):
                    self._device.frequency = f
                    self._device.value = 0.6
                    time.sleep(0.02)
            self._device.value = 0
            self._device.frequency = orig_freq
        threading.Thread(target=run, daemon=True).start()

    def success(self) -> None:
        """One sharp, high-pitched beep."""
        self._beep(n=1, duration=0.2, duty=0.7)

    def failure(self) -> None:
        """A quick low-high 'thump' sound."""
        def run():
            self._device.frequency = 1500
            self._device.value = 0.8
            time.sleep(0.1)
            self._device.frequency = 3500
            self._device.value = 0.8
            time.sleep(0.1)
            self._device.value = 0
        threading.Thread(target=run, daemon=True).start()

    def alert(self) -> None:
        """The loudest siren effect."""
        self._siren(loops=5)

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
