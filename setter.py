import sys
import time
import struct
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
import serial
import serial.tools.list_ports

class SerialApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.serial_port = serial.Serial()

        # Wybór portu szeregowego
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel('Port szeregowy:'))
        self.port_select = QComboBox()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_select.addItem(port.device)
        port_layout.addWidget(self.port_select)
        layout.addLayout(port_layout)

        # Ustawienia numeru banku
        bank_layout = QHBoxLayout()
        bank_layout.addWidget(QLabel('Numer banku konfiguracyjnego:'))
        self.bank_input = QLineEdit()
        bank_layout.addWidget(self.bank_input)
        layout.addLayout(bank_layout)

        # Ustawienia numeru obiektu
        object_layout = QHBoxLayout()
        object_layout.addWidget(QLabel('Numer obiektu konfiguracyjnego:'))
        self.object_input = QLineEdit()
        object_layout.addWidget(self.object_input)
        layout.addLayout(object_layout)

        # Wybór akcji
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel('Akcja:'))
        self.action_select = QComboBox()
        self.action_select.addItem('GET', 0)
        self.action_select.addItem('SET', 1)
        action_layout.addWidget(self.action_select)
        layout.addLayout(action_layout)

        # Pole danych
        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel('Dane:'))
        self.data_input = QLineEdit()
        data_layout.addWidget(self.data_input)
        layout.addLayout(data_layout)

        # Przyciski
        button_layout = QHBoxLayout()
        self.send_button = QPushButton('Wyślij')
        self.send_button.clicked.connect(self.send_data)
        button_layout.addWidget(self.send_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def send_data(self):
        bank = int(self.bank_input.text())
        obj = int(self.object_input.text())
        action = self.action_select.currentData()

        if action == 0:  # GET
            self.send_get(bank, obj)
        elif action == 1:  # SET
            data = self.data_input.text()
            self.send_set(bank, obj, data)

    def open_serial_port(self):
        if not self.serial_port.is_open:
            self.serial_port.port = self.port_select.currentText()
            self.serial_port.baudrate = 9600
            self.serial_port.timeout = 1  # Ustal timeout na 1 sekundę
            self.serial_port.open()

    def send_get(self, bank, obj):
        self.open_serial_port()

        header = 0xABCD
        action = 0
        frame = struct.pack('>HBB', header, action, bank) + struct.pack('B', obj)
        self.serial_port.write(frame)
        response = self.wait_for_get_response()

        if response is not None:
            self.data_input.setText(response)

    def send_set(self, bank, obj, data):
        self.open_serial_port()

        header = 0xABCD
        action = 1
        data_length = len(data)
        frame = struct.pack('>HBBB', header, action, bank, obj) + struct.pack('B', data_length) + data.encode()
        self.serial_port.write(frame)
        ack_received = self.wait_for_ack()

        if ack_received:
            self.set_data_input_color("green")
            print("ACK received")
        else:
            self.set_data_input_color("red")
            print("ACK not received")

    def set_data_input_color(self, color):
        palette = self.data_input.palette()
        palette.setColor(QPalette.Text, QColor(color))
        self.data_input.setPalette(palette)

    def wait_for_ack(self):
        start_time = time.time()
        timeout = 5  # Oczekuj na odpowiedź przez 5 sekund

        while time.time() - start_time < timeout:
            if self.serial_port.in_waiting > 0:
                response = self.serial_port.read(5)
                header, action, _, _ = struct.unpack('>HBBB', response)

                if header == 0xABCD and action == 3:
                    return True

        return False

    def wait_for_get_response(self):
        start_time = time.time()
        timeout = 5  # Oczekuj na odpowiedź przez 5 sekund

        while time.time() - start_time < timeout:
            if self.serial_port.in_waiting > 0:
                response = self.serial_port.read(6)
                header, action, _, _, data_length = struct.unpack('>HBBBB', response)

                if header == 0xABCD and action == 4:
                    data = self.serial_port.read(data_length)
                    return data.decode()

        return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SerialApp()
    ex.show()
    sys.exit(app.exec_())