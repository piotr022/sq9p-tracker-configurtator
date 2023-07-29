import struct

class FlashAccess:
    frame_id = 0xFFAABBCC
    erase_sequence = 0xAABBCCDD
    ack_byte = 0xAA
    ack_len = 1
    mtu = 128
    img_block_size = 3 * 0x10000

    def __init__(self, comm_interface):
        self.comm_interface = comm_interface

    def write_to_flash(self, address, data, progress_callback):
        self.start_address = address
        self.data = data
        self.progress_callback = progress_callback
        self.idx = 0
        self.erase_idx = 0

        if not len(data):
            return self.progress_callback(-1)
        
        tx_frame = self.encode_next_erase_frame()
        if not len(tx_frame):
            return self.progress_callback(-1)
        
        self.comm_interface.send_async(tx_frame)
        self.comm_interface.receive_async(FlashAccess.ack_len, self.receive_handler)

    def encode_next_erase_frame(self):
        erase_offset = self.erase_idx * FlashAccess.img_block_size
        if erase_offset >= len(self.data):
            return bytearray()
        erase_frame = struct.pack('<IIHB',
                                FlashAccess.erase_sequence,
                                self.start_address + erase_offset,
                                1,1)
        self.erase_idx += 1
        return erase_frame

    def encode_next_frame(self):
        if self.idx >= len(self.data):
            return bytearray()
        
        data_size = min(FlashAccess.mtu, len(self.data) - self.idx)
        tx_frame = self.encode_header(self.start_address + self.idx, 
                        data_size)
        tx_frame += self.data[self.idx:self.idx + data_size]
        self.idx += data_size
        return tx_frame

    def receive_handler(self, rx_data):
        if len(rx_data) != 1 or rx_data[0] != FlashAccess.ack_byte:
            return self.progress_callback(-1)
        
        erase_frame = self.encode_next_erase_frame()
        if len(erase_frame):
            next_frame = erase_frame
        else:
            next_frame = self.encode_next_frame()
            if(not len(next_frame)):
                return self.progress_callback(100)
            
        self.comm_interface.send_async(next_frame)
        self.comm_interface.receive_async(1, self.receive_handler)        

    def encode_header(self, address, len):
        return struct.pack('<IIHB',
                           FlashAccess.frame_id,
                           address,
                           len,
                           1)