import struct

class ObjBase:
    def __init__(self, db_id, obj_id):
        self.databank_id = db_id
        self.obj_id = obj_id
        self.len = 63

class ObjAprsConfig(ObjBase):
    def __init__(self, db_id, obj_id):
        ObjBase.__init__(self, db_id, obj_id)
        self.len = 63

        self.callsign = None
        self.destination = None
        self.digi_path = None
        self.callsign_designator = None
        self.destination_designator = None
        self.symbol = None

    def serialize(self):
        return struct.pack('15s15s30sbbB',
                           self.callsign.encode('utf-8'),
                           self.destination.encode('utf-8'),
                           self.digi_path.encode('utf-8'),
                           self.callsign_designator,
                           self.destination_designator,
                           self.symbol)
    
    def deserialize(self, raw_data) -> bool:
        if len(raw_data) != self.len:
            print(f"deserialize err rx size {len(raw_data)} but required {self.len}")
            return False
        
        (
            self.callsign,
            self.destination,
            self.digi_path,
            self.callsign_designator,
            self.destination_designator,
            self.symbol
        ) = struct.unpack('15s15s30sbbB', raw_data)
        self.callsign = self.callsign.decode().replace('\x00', '')
        self.destination = self.destination.decode().replace('\x00', '')
        self.digi_path = self.digi_path.decode().replace('\x00', '')
        print("deserialize res:")
        print(self.callsign)
        print(self.symbol)
        print(self.destination_designator)
        return True
    
class ObjFreq(ObjBase):
    def __init__(self, db_id, obj_id):
        ObjBase.__init__(self, db_id, obj_id)
        self.len = 7

        self.frequency = 3
        self.radio_mode = 0
        self.tx_power = 0
        self.telemetry_psc = 0
        self.position_psc = 0

    def serialize(self):
        return struct.pack('<IBBB',
                           self.frequency,
                           self.radio_mode & 0xFF,
                           self.tx_power & 0xFF,
                           ((int(self.telemetry_psc) << 4) | int(self.position_psc)) & 0xFF)
    
    def deserialize(self, raw_data) -> bool:
        if len(raw_data) != self.len:
            print(f"deserialize err rx size {len(raw_data)} but required {self.len}")
            return False
        (
            self.frequency,
            self.radio_mode,
            self.tx_power,  
            psc_bath
        ) = struct.unpack('<IBBB', raw_data)
        self.telemetry_psc = (int(psc_bath) >> 4) & 0xFF
        self.position_psc = int(psc_bath) & 0xF

        print(f'!!!! freq: {self.frequency}')
        return True
    
class ObjTable(ObjBase):
    def __init__(self, init_instance, table_size):
        ObjBase.__init__(self, init_instance.databank_id, init_instance.obj_id)
        self.len = init_instance.len
        self.table_size = table_size
        init_instance_type = type(init_instance)
        self.objects = [init_instance_type(init_instance.databank_id, init_instance.obj_id) for _ in range(table_size)]

    def serialize(self, idx):
        return self.objects[idx].serialize()
    
    def deserialize(self, data, idx = 0):
        return self.objects[idx].deserialize(data)
    
class TPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
class ObjGeoConf(ObjBase):
    def __init__(self, db_id, obj_id):
        ObjBase.__init__(self, db_id, obj_id)
        self.len = 22
        self.points = [TPoint(0, 0)] * 5
        
        self.b_inside = False

    def serialize(self):
        points_data = []
        for i in range(len(self.points)):
            points_data.append(self.points[i].x)
            points_data.append(self.points[i].y)

        return struct.pack('<10hH',
                           *points_data,
                           self.b_inside)
    
    def deserialize(self, raw_data) -> bool:
        if len(raw_data) != self.len:
            print(f"deserialize err rx size {len(raw_data)} but required {self.len}")
            return False
        
        raw_data = struct.unpack('<10hH', raw_data)
        points_data = raw_data[:-1]
        self.b_inside = raw_data[-1]
        print(f"len of points_data {len(points_data)}")
        for i in range(0, len(points_data), 2):
            self.points[int(i/2)] = TPoint(points_data[i], points_data[i+1])

        return True
    

class ObjSstvConfig(ObjBase):
    def __init__(self, db_id, obj_id):
        ObjBase.__init__(self, db_id, obj_id)
        self.len = 53
        self.sstv_text_field = '\0' * 50
        self.images_cnt = 0
        self.images_per_freq = 0
        self.b_header_enabled = True

    def serialize(self):
        return struct.pack(
            '<50sBBB',
            self.sstv_text_field.encode('ascii')[:50].ljust(50, b'\0'),
            self.images_cnt,
            self.images_per_freq,
            int(self.b_header_enabled)
        )

    def deserialize(self, raw_data):
        if len(raw_data) != self.len:
            return False

        sstv_text_bytes, self.images_cnt, self.images_per_freq, b_header_flag = struct.unpack('<50sBBB', raw_data)
        self.sstv_text_field = sstv_text_bytes.decode('ascii').rstrip('\0')
        self.b_header_enabled = bool(b_header_flag)
        return True
