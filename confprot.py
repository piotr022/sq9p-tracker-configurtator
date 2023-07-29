import struct
from typing import Dict, Any

class ECommand:
    GET = 0
    SET = 1
    GET_RESP = 2
    SET_ACK = 3
    SET_NACK = 4
    GET_ACK = 5

class ConfProtHeader:
    SIZE = 3
    ACCESS_SUB_SIZE = 4
    def __init__(self) -> None:
        self.fixed_id = 0xAF43
        self.command = ECommand.GET
        pass

    def serialize(self):
        return struct.pack("<HB",
                            self.fixed_id,
                            self.command)
    
    def deserialize(self, raw_data) -> bool:
        if not raw_data or len(raw_data) < 3:
            return False
        self.fixed_id, self.command = struct.unpack("<HB", raw_data[:3])
        return True

class ConfProt:
    def __init__(self, conf_objects, comm_interface) -> None:
        self.conf_objects = conf_objects
        self.comm_interface = comm_interface
        self.idx = 0
        self.sub_idx = 0
        self.irq_lock = True
        pass    

    def serialize_set(self, conf_obj, idx = 0) -> bytearray:
        data = self.generate_header(ECommand.SET)
        data += bytearray([conf_obj.databank_id,
                           conf_obj.obj_id,
                           idx,
                           conf_obj.len])
        if hasattr(conf_obj, 'table_size'):
            data.extend(conf_obj.serialize(idx))
        else:
            data.extend(conf_obj.serialize())
        return data
    
    def serialize_get(self, conf_obj, idx = 0) -> bytearray:
        data = self.generate_header(ECommand.GET)
        data += bytearray([conf_obj.databank_id,
                           conf_obj.obj_id,
                           idx,
                           conf_obj.len])
        return data
    
    def set_sync(self, conf_obj, idx = 0) -> bool:
        tx_frame = self.serialize_set(conf_obj, idx)
        self.comm_interface.send(tx_frame)
        rx_frame = self.comm_interface.receive(ConfProtHeader.SIZE)
        Header = ConfProtHeader()
        error = Header.deserialize(rx_frame)
        if error or Header.command != ECommand.SET_ACK:
            return False
        return True

    def get_sync(self, conf_obj, idx = 0) -> bool:
        tx_frame = self.serialize_get(conf_obj, idx)
        self.comm_interface.send(tx_frame)
        rx_frame = self.comm_interface.receive(conf_obj.len + ConfProtHeader.SIZE + ConfProtHeader.ACCESS_SUB_SIZE)
        print(rx_frame)
        Header = ConfProtHeader()
        status = Header.deserialize(rx_frame)
        print(f"hader data {Header.command} {Header.fixed_id} {status} {status == False} {Header.command != ECommand.GET_RESP}")
        if status == False or Header.command != ECommand.GET_RESP:
            print("response header not valid")
            return False
        if idx != 0:
            return conf_obj.deserialize(rx_frame[ConfProtHeader.SIZE + ConfProtHeader.ACCESS_SUB_SIZE:], idx)
        return conf_obj.deserialize(rx_frame[ConfProtHeader.SIZE + ConfProtHeader.ACCESS_SUB_SIZE:])
    
    def set_all_sync(self, status_callback = None):
        processing_idx = 0
        for obj in self.conf_objects:
            if hasattr(obj, 'table_size'):
                for i in range(obj.table_size):
                    processing_idx += self.set_sync(obj, i)
            else:
                processing_idx += self.set_sync(obj)
            if status_callback != None:
                status_callback(100*processing_idx/len(self.conf_objects))
            
    def get_all_sync(self, status_callback = None):
        processing_idx = 0
        for obj in self.conf_objects:
            if hasattr(obj, 'table_size'):
                for i in range(obj.table_size):
                    processing_idx += self.get_sync(obj, i)
            else:
                processing_idx += self.get_sync(obj)
            if status_callback != None:
                status_callback(100*processing_idx/len(self.conf_objects))

    def set_all_async(self, status_callback):
        if self.idx > 0:
            return False
        self.status_callback = status_callback
        self.idx = 0
        self.sub_idx = 0
        self.send_next_set_async()

    def send_next_set_async(self):
        if self.idx >= len(self.conf_objects):
            print("send cmd finished")
            self.idx = 0
            return False
        obj = self.conf_objects[self.idx]
        if hasattr(obj, 'table_size'):
            if self.sub_idx < obj.table_size:
                tx_frame = self.serialize_set(self.conf_objects[self.idx], self.sub_idx)
                print(f"send cmd {self.idx} {self.sub_idx}")
                self.sub_idx += 1
            else: # sub idx finished
                self.sub_idx = 0
                self.idx += 1
                return self.send_next_set_async()
        else:
            tx_frame = self.serialize_set(self.conf_objects[self.idx])
            print(f"send cmd {self.idx} {self.sub_idx}")
            self.idx += 1

        self.comm_interface.flush()
        self.comm_interface.send_async(tx_frame)
        self.comm_interface.receive_async(ConfProtHeader.SIZE, self.rx_done_cb_set)
        return True

    def rx_done_cb_set(self, rx_frame):
        if rx_frame == None:
            self.status_callback(-1)

        Header = ConfProtHeader()
        error = Header.deserialize(rx_frame)
        if error == False or Header.command != ECommand.SET_ACK:
            return self.status_callback(-1)
        if self.send_next_set_async():
            self.status_callback(100 * self.idx/len(self.conf_objects))
        else:
            self.status_callback(100)

    def get_all_async(self, status_callback):
        if self.idx > 0:
            return False
        self.status_callback = status_callback
        self.idx = 0
        self.sub_idx = 0
        self.send_next_get()

    def rx_done_cb_get(self, rx_frame):
        if len(rx_frame) != self.current_obj.len + ConfProtHeader.SIZE + ConfProtHeader.ACCESS_SUB_SIZE:
            print("rx wrong len")
            self.status_callback(-1)
            self.idx = 0
            self.sub_idx = 0
            return
        
        Header = ConfProtHeader()
        HeaderDesResult = Header.deserialize(rx_frame)
        if not HeaderDesResult or Header.command != ECommand.GET_RESP:
            print("rx wrong header")
            self.status_callback(-1)
            return

        if self.sub_idx > 0:
            res = self.current_obj.deserialize(rx_frame[ConfProtHeader.SIZE + ConfProtHeader.ACCESS_SUB_SIZE:], self.sub_idx - 1)
        else:
            res = self.current_obj.deserialize(rx_frame[ConfProtHeader.SIZE + ConfProtHeader.ACCESS_SUB_SIZE:])

        if not res:
            print(f"deserialize err {self.idx - 1}, {self.sub_idx - 1}")

        if not self.send_next_get():
            self.status_callback(100)
        else:
            self.status_callback(100 * self.idx / len(self.conf_objects))

    def send_next_get(self):
        if(self.idx >= len(self.conf_objects)):
            self.idx = 0
            return False
        
        self.current_obj = self.conf_objects[self.idx]
        if hasattr(self.current_obj, 'table_size'):
            if self.sub_idx < self.current_obj.table_size:
                tx_frame = self.serialize_get(self.conf_objects[self.idx], self.sub_idx)
                print(f"get cmd {self.idx} {self.sub_idx}")
                self.sub_idx += 1
            else: # sub idx finished
                self.sub_idx = 0
                self.idx += 1
                return self.send_next_get()
        else:
            tx_frame = self.serialize_get(self.conf_objects[self.idx])
            print(f"send cmd {self.idx} {self.sub_idx}")
            self.idx += 1

        self.comm_interface.flush()
        self.comm_interface.send_async(tx_frame)
        self.comm_interface.receive_async(self.current_obj.len + ConfProtHeader.SIZE + ConfProtHeader.ACCESS_SUB_SIZE, self.rx_done_cb_get)
        return True
        
    def generate_header(self, cmd):
        return bytearray([0x43, 0xAF, cmd])
    

if __name__ == "__main__":
    import objects
    import serial
    ser = serial.Serial('COM24', 115200, timeout=1) 
    aprs_conf = []
    aprs_conf.append(objects.ObjAprsConfig(0, 1))
    prot = ConfProt(aprs_conf, None)
    tx_frame = prot.serialize_get(aprs_conf[0])
    ser.write(tx_frame)
    rx_frame = ser.read(100)
    print(rx_frame)