import serial

class SerialWrapper:
    def __init__(self, serial_ref, timeout = 1000, timeout_idle_line = 100) -> None:
        self.serial_ref = serial_ref
        self.timeout = timeout
        self.timeout_idle_line = timeout_idle_line
        self.user_rx_callback = None
        self.callback_slot_inited = False

    def send(self, data):
        self.serial_ref.flush()
        self.serial_ref.write(data)
        self.serial_ref.waitForBytesWritten(-1)

    def receive(self, size = 0):
        self.flush()
        rx_data = bytearray()
        while self.serial_ref.waitForReadyRead(self.timeout):
            rx_data += self.serial_ref.readAll()
            if(len(rx_data) >= size):
                break
        return rx_data
    
    def receive_detect_idle(self):
        rx_data = bytearray()
        rx_to = self.timeout
        self.serial_ref.flush()
        while self.serial_ref.waitForReadyRead(500):
            rx_data += self.serial_ref.readAll()
            rx_to = self.timeout_idle_line
        
        return rx_data
        # while 1:
        #     rx_byte = self.serial_ref.readData(1)
        #     self.serial_ref.waitForReadyRead(rx_to)
        #     rx_byte = self.serial_ref.readData(1)

        #     if rx_byte:
        #         rx_data += rx_byte
        #         rx_to = self.timeout_idle_line
        #     else:
        #         print("no rx data")
        #         return rx_data
    def send_async(self, data):
        self.serial_ref.write(data)

    def receive_async(self, size, callback):
        self.serial_ref.readAll()
        self.user_requested_read_size = size
        self.user_data = bytearray()
        self.user_rx_callback = callback

        if not self.callback_slot_inited:
            self.callback_slot_inited = True
            self.serial_ref.readyRead.connect(self.onRxDone)

    def onSendDone(self):
        pass

    def onRxDone(self):
        self.user_data += self.serial_ref.readAll()
        if(len(self.user_data) >= self.user_requested_read_size):
            print(f"rx data: {self.user_data}")
            self.user_rx_callback(self.user_data)
        pass

    def flush(self):
        self.serial_ref.readAll()
