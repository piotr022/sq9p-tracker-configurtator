import struct, os

class OtaFrameType:
    init = 0
    data = 1
    reflash = 2
    ack = 3
    reflash_other_device = 4

class FirmwareUploader:
    ack_frame_len = 7
    packet_fw_chunk_size = 128
    def __init__(self, comm_interface):
        self.comm_interface = comm_interface

    def upload_firmware(self, filename, status_callback):
        self.status_callback = status_callback
        self.file = open(filename)
        self.file.seek(0, os.SEEK_END)
        fw_size = self.file.tell()
        self.file.seek(0)
        init_frame = self.get_header(OtaFrameType.init)
        secret_code = struct.unpack('<Q', self.file.read(8))
        init_frame += struct.pack('<QHH', secret_code,
                                  0, fw_size)
        self.comm_interface.send(init_frame)
        self.comm_interface.receive(7, self.receive_cb)

    def receive_cb(self, rx_data):
        if len(rx_data) != self.ack_frame_len:
            return self.status_callback(-1)
        
        _, _, _, _, ack = struct.unpack('<BHHBB')
        if not ack:
            return self.status_callback(-1)
        
        fw_offset = self.file.tell() - 8
        fw_part = self.file.read(self.packet_data_size)
        if not len(fw_part):
            return self.status_callback(100)
        if len(fw_part) < self.packet_fw_chunk_size:
            fw_part += [0xFF] * self.packet_fw_chunk_size - len(fw_part)
        
        packet = self.get_header(OtaFrameType.data)
        packet += struct.pack('<H', fw_offset)
        packet += fw_part
        self.comm_interface.send(packet)
        self.comm_interface.receive(7, self.receive_cb)
        
    def get_header(self, frame_type):
        return struct.pack('<BHHB',
                             0xA3,
                             0x00,
                             0xABCE,
                             frame_type)