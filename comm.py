from PyQt5.QtCore import QTimer

class SerialWrapper:
    def __init__(self, serial_ref, timeout=1000, timeout_idle_line=100) -> None:
        self.serial_ref = serial_ref
        self.timeout = timeout
        self.timeout_idle_line = timeout_idle_line
        self.user_rx_callback = None
        self.callback_slot_inited = False
        self.timeout_timer = QTimer(self.serial_ref)  # zapewnia przeżycie timera
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.onTimeout)

    def send(self, data):
        self.serial_ref.flush()
        self.serial_ref.write(data)
        self.serial_ref.waitForBytesWritten(-1)

    def receive(self, size=0):
        self.flush_rx()
        rx_data = bytearray()
        while self.serial_ref.waitForReadyRead(self.timeout):
            rx_data += self.serial_ref.readAll()
            if len(rx_data) >= size:
                break
        return rx_data

    def receive_detect_idle(self):
        rx_data = bytearray()
        self.flush_rx()
        timeout = self.timeout

        while True:
            if not self.serial_ref.waitForReadyRead(timeout):
                break
            rx_data += self.serial_ref.readAll()
            timeout = self.timeout_idle_line  # zmiana na idle timeout po 1. bajcie

        return rx_data

    def send_async(self, data):
        self.serial_ref.write(data)

    def receive_async(self, size, callback, timeout=0):
        self.serial_ref.readAll()
        self.user_requested_read_size = size
        self.user_data = bytearray()
        self.user_rx_callback = callback

        if not self.callback_slot_inited:
            self.callback_slot_inited = True
            self.serial_ref.readyRead.connect(self.onRxDone)

        if timeout > 0:
            if self.timeout_timer.isActive():
                self.timeout_timer.stop()
            self.timeout_timer.start(timeout)

    def onSendDone(self):
        pass

    def onRxDone(self):
        self.user_data += self.serial_ref.readAll()
        if len(self.user_data) >= self.user_requested_read_size:
            if self.timeout_timer.isActive():
                self.timeout_timer.stop()
            print(f"rx data: {self.user_data}")
            if self.user_rx_callback:
                self.user_rx_callback(self.user_data)

    def onTimeout(self):
        print("rx timeout")
        if self.user_rx_callback:
            self.user_rx_callback(None)

    def flush_rx(self):
        self.serial_ref.readAll()

    def flush(self):
        self.flush_rx()
