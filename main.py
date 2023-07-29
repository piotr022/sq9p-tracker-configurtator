from comm import SerialWrapper
from confprot import ConfProt
import objects
from stefan_conf import SerialConfigurator
from fwupd import FirmwareUploader
from imgupload import ImgUpload

from PyQt5.QtWidgets import QApplication
from PyQt5.QtSerialPort import QSerialPort
import sys

import serial
   
v2_objects = {
   "aprs_config" : objects.ObjAprsConfig(0, 1), 
   "freq_table_config" : objects.ObjTable(objects.ObjFreq(1, 0), 11),
   "geofencing_config" : objects.ObjTable(objects.ObjGeoConf(1, 1), 11),
   "sstv_config" : objects.ObjSstvConfig(1, 2)
   }

if __name__ == "__main__":
   ser = QSerialPort()
   comm_interface = SerialWrapper(ser)
   config_protocol = ConfProt(list(v2_objects.values()), comm_interface)
   fw_uploader = FirmwareUploader(comm_interface)
   img_uploader = ImgUpload(comm_interface)

   v2_objects["aprs_config"].callsign = "SQ9P"
   v2_objects["aprs_config"].callsign_designator = 7
   v2_objects["aprs_config"].digi_path = "WIDE1-1"
   v2_objects["aprs_config"].destination = "TEST"
   v2_objects["aprs_config"].destination_designator = 1
   v2_objects["aprs_config"].symbol = 1
   # err = config_protocol.set_sync(v2_objects["aprs_config"])

   app = QApplication(sys.argv)
   widget = SerialConfigurator(config_protocol, v2_objects, ser, fw_uploader, img_uploader)
   widget.show()
   sys.exit(app.exec_())