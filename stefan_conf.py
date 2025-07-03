import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QLineEdit, QGroupBox, QFormLayout, QProgressBar, QTabWidget, QCheckBox, QFileDialog, QListWidget, QListWidgetItem
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtCore import pyqtSlot, QStringListModel
from PyQt5.QtGui import QIcon, QFontMetrics
from objects import TPoint

class SerialConfigurator(QWidget):
    def __init__(self, confprot, config_objects, serialPort, fw_uploader, img_uploader):
        self.confprot = confprot
        self.config = config_objects
        self.serialPort = serialPort
        self.fw_uploader = fw_uploader
        self.img_uploader = img_uploader
        self.fw_file = None
        self.connected = False
        super().__init__()
        self.initUI()
        self.init_layout_lists()

    def show(self):
        super().show()
        self.resize(500, self.size().height())
        self.setFixedSize(self.size())

    def init_layout_lists(self):
        self.aprsSymbolMap = {
            "BALLOON" : 6,
            "CAR" : 3,
            "ROCKET" : 5,
            "WX_STATION" : 1, 
            "DIGI" :  0,
        }
        self.aprsSymbolMapInverse = {v: k for k, v in self.aprsSymbolMap.items()}

        self.geoConfigModeMap = {
            'TX INSIDE' : 0,
            'TX OUTSIDE' : 1
        }
        self.geoConfigModeMapInverse = {v: k for k, v in self.geoConfigModeMap.items()}

        # common setters
        self.str_to_qlabel = lambda x, y: y.setText(str(x))
        self.str_to_qcombobox = lambda x, y: y.setCurrentText(str(x))
        cord_lines_to_objs = lambda x : [TPoint(int(float(x[i].text()) * 100), int(float(x[i+1].text()) * 100)) for i in range(0, len(x), 2)]
        def objs_to_cord_lines(x, y):
            for i in range(0, len(y), 2):
                y[i].setText(str(float(x[int(i/2)].x)/100))
                y[i+1].setText(str(float(x[int(i/2)].y)/100))
        #                           stefan obj(idx, attribute) | qtObj | setter | getter

        self.config_map = [
            [('aprs_config', "callsign"),                       self.aprsCallsign,          lambda x: x.text(),                                  self.str_to_qlabel                                                         ],
            [('aprs_config', "destination"),                    None,                       None,                                                None                                                                       ],
            [('aprs_config', "digi_path"),                      self.aprsDigiPath,          lambda x: x.text(),                                  self.str_to_qlabel                                                         ],
            [('aprs_config', "callsign_designator"),            self.aprsDesignator,        lambda x: int(x.currentText()),                      self.str_to_qcombobox                                                      ],
            [('aprs_config', "destination_designator"),         None,                       None,                                                None                                                                       ],
            [('aprs_config', "symbol"),                         self.aprsSymbol,            lambda x: int(self.aprsSymbolMap[x.currentText()]),  lambda x,y : self.str_to_qcombobox(self.aprsSymbolMapInverse[x], y)        ],
            
            [('freq_table_config', "frequency"),                self.frequencyLines,        lambda x: int(float(x.text())*1000),                 lambda x,y : self.str_to_qlabel(float(x)/1000, y)                          ],
            [('freq_table_config', "telemetry_psc"),            self.telemetryPrescalers,   lambda x: int(x.currentText()),                      self.str_to_qcombobox                                                      ],
            [('freq_table_config', "position_psc"),             self.positionPrescalers,    lambda x: int(x.currentText()),                      self.str_to_qcombobox                                                      ],
            [('freq_table_config', "radio_mode"),               self.modeBoxes,             lambda x: int(self.modes.index(x.currentText())),    lambda x, y : y.setCurrentText(self.modes[x])                              ],
            
            [('geofencing_config', "points"),                   self.geoConfigCordLines,    cord_lines_to_objs,                                  objs_to_cord_lines                                                         ],
            [('geofencing_config', "b_inside"),                 self.geoConfigModeBoxes,    lambda x: int(self.geoConfigModeMap[x.currentText()]), lambda x,y : self.str_to_qcombobox(self.geoConfigModeMapInverse[x], y)   ],
            
            [('sstv_config', "sstv_text_field"),                self.sstvTextHeader,        lambda x: x.text(),                                  self.str_to_qlabel                                                         ],
            [('sstv_config', "images_cnt"),                     self.sstvImageCnt,          lambda x: int(x.currentText()),                      self.str_to_qcombobox                                                      ],
            [('sstv_config', "images_per_freq"),                self.sstvImageCntPerFreq,   lambda x: int(x.currentText()),                      self.str_to_qcombobox                                                      ],
            [('sstv_config', "b_header_enabled"),               self.sstvBHeaderEnabled,    lambda x: int(x.isChecked()),                        lambda x,y : y.setChecked( x > 0 )                                         ],
        ]

    @pyqtSlot()
    def connect(self):
        portName = self.comboBox.currentText()
        # self.serialPort = QSerialPort()
        if self.connected:
            self.serialPort.close()
            self.connected = False

        self.serialPort.setPortName(portName)
        self.serialPort.setBaudRate(115200)


        if self.serialPort.open(QSerialPort.ReadWrite, ):
            self.connected = True
            self.connectionLabel.setText("Connecting ..." + portName)
            self.get_command_async()
        else:
            self.connected = False
            self.connectionLabel.setText("Failed to connect to " + portName)
            self.serialPort.close()

    def set_command(self):
        for key, obj_qt, setter, getter in self.config_map:
            if obj_qt == None:
                continue
            dict_idx, attr = key
            obj = self.config[dict_idx]
            if not hasattr(obj, 'table_size'):
                setattr(obj, attr, setter(obj_qt))
            else:
                for i in range(min(obj.table_size, len(obj_qt))):
                    setattr(obj.objects[i], attr, setter(obj_qt[i]))
        self.confprot.set_all_sync(self.update_progressbar)

    def set_command_async(self):
        print("set command requested")
        for key, obj_qt, setter, getter in self.config_map:
            if obj_qt == None:
                continue
            dict_idx, attr = key
            obj = self.config[dict_idx]
            if not hasattr(obj, 'table_size'):
                setattr(obj, attr, setter(obj_qt))
            else:
                for i in range(min(obj.table_size, len(obj_qt))):
                    setattr(obj.objects[i], attr, setter(obj_qt[i]))
        
        self.disable_buttons(True)
        self.confprot.set_all_async(self.progress_callback)

    def get_command_async(self):
        self.disable_buttons(True)
        self.confprot.get_all_async(self.progress_callback_get)

    def progress_callback_get(self, progress):
        self.progress_callback(progress)
        if progress != 100:
            return

        self.connectionLabel.setText("Connected")
        #update qt objects
        for key, obj_qt, setter, getter in self.config_map:
            if obj_qt == None:
                continue
            dict_idx, attr = key
            obj = self.config[dict_idx]
            if not hasattr(obj, 'table_size'):
                getter(getattr(obj, attr), obj_qt)
            else:
                for i in range(min(obj.table_size, len(obj_qt))):
                    getter(getattr(obj.objects[i], attr), obj_qt[i])
        
    def progress_callback(self, progress):
        if progress < 0 or progress == 100:
            self.disable_buttons(False)
        
        if progress >= 0:
            self.update_progressbar(progress)

    def disable_buttons(self, disabled):
        self.getCommandButton.setDisabled(disabled)
        self.setCommandButton.setDisabled(disabled)
        self.fwUpdateUploadButton.setDisabled(disabled)
        self.sstvImagesUploadButton.setDisabled(disabled)
    
    def get_command(self):
        self.confprot.get_all_sync(self.update_progressbar)
        for key, obj_qt, setter, getter in self.config_map:
            if obj_qt == None:
                continue
            dict_idx, attr = key
            obj = self.config[dict_idx]
            if not hasattr(obj, 'table_size'):
                getter(getattr(obj, attr), obj_qt)
            else:
                for i in range(min(obj.table_size, len(obj_qt))):
                    getter(getattr(obj.objects[i], attr), obj_qt[i])
            
    def update_progressbar(self, percent):
        print(percent)
        self.progressBar.setValue(int(percent))

    def initUI(self):
        self.setWindowTitle('SQ9P Tracker Configurator')

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.connectionSettings = QGroupBox('Connection Settings')
        self.connectionSettingsLayout = QVBoxLayout()
        self.connectionSettings.setLayout(self.connectionSettingsLayout)

        self.uartConfigRowLayout = QHBoxLayout()
        self.connectionSettingsLayout.addLayout(self.uartConfigRowLayout)

        self.comboBox = QComboBox(self)
        self.serialPorts = QSerialPortInfo.availablePorts()
        for port in self.serialPorts:
            self.comboBox.addItem(port.portName())

        self.connectionLabel = QLabel(self)
        self.connectionLabel.setText("Disconnected")

        self.connectButton = QPushButton('Connect', self)
        self.connectButton.clicked.connect(self.connect)

        self.uartConfigRowLayout.addWidget(self.comboBox)
        self.uartConfigRowLayout.addWidget(self.connectionLabel)
        self.uartConfigRowLayout.addWidget(self.connectButton)

        self.uartCommandRowLayout = QHBoxLayout()
        self.connectionSettingsLayout.addLayout(self.uartCommandRowLayout)

        self.getCommandButton = QPushButton('Get', self)
        self.getCommandButton.clicked.connect(self.get_command_async)
        self.setCommandButton = QPushButton('Set', self)
        self.setCommandButton.clicked.connect(self.set_command_async)

        self.uartCommandRowLayout.addWidget(self.getCommandButton)
        self.uartCommandRowLayout.addWidget(self.setCommandButton)

        self.progresBarLayout = QHBoxLayout()
        self.connectionSettingsLayout.addLayout(self.progresBarLayout)

        self.progressBar = QProgressBar(self)
        self.progresBarLayout.addWidget(self.progressBar)
        self.progressBar.setValue(0)
        self.layout.addWidget(self.connectionSettings)

        self.tabs = QTabWidget()
        self.init_frequency_layout()
        self.init_geoconig_layout()
        self.init_sstv_layout()
        self.init_update_layout()

        self.multiConfig = QGroupBox('Multi Configuration')
        self.multiConfigLayout = QVBoxLayout()
        self.multiConfig.setLayout(self.multiConfigLayout)

        self.multiConfigLayout.addWidget(self.tabs)
        self.layout.addWidget(self.multiConfig)
        #self.layout.addWidget(self.tabs)
        # self.layout.addWidget(self.aprsSettings)

    def init_frequency_layout(self):
        self.frequencyConfigTab = QWidget()
        self.frequencyConfigTabLayout = QHBoxLayout()
        self.frequencyConfigTab.setLayout(self.frequencyConfigTabLayout)

        self.frequencyConfigGroupBox = QGroupBox('Frequency Settings')
        self.frequencyConfigLayout = QVBoxLayout()
        self.frequencyConfigGroupBox.setLayout(self.frequencyConfigLayout)
        # self.frequencyConfigTab.setLayout(self.frequencyConfigLayout)
        self.frequencyConfigTabLayout.addWidget(self.frequencyConfigGroupBox)
        self.tabs.addTab(self.frequencyConfigTab, "Frequency")

        self.frequencyLayouts = []
        self.frequencyLines = []
        self.modeBoxes = []
        self.positionPrescalers = []
        self.telemetryPrescalers = []

        self.modes = ['APRS AFSK 1200', 'APRS AFSK 9600', 'APRS AFSK CUSTOM', 'APRS_LORA 300', 'APRS LORA 1200', 'APRS LORA CUSTOM', '4FSK HORUS V2', 'FM SSTV', 'FM AUDIO']
        prescalers = [str(i) for i in range(0, 16)]

        self.columnLabelsLayout = QHBoxLayout()
        self.frequencyConfigLayout.addLayout(self.columnLabelsLayout)

        for i in range(11):
            layout = QHBoxLayout()
            self.frequencyLayouts.append(layout)
            self.frequencyConfigLayout.addLayout(layout)

            layout.addWidget(QLabel(str(i)+(".  " if i < 10 else ".")))
            layout.addWidget(QLabel("Frequency"))

            frequencyLine = QLineEdit()
            frequencyLine.setMaxLength(8)
            metrics = QFontMetrics(frequencyLine.font())
            width = metrics.horizontalAdvance('0' * 8) + 10
            frequencyLine.setFixedWidth(width)
            self.frequencyLines.append(frequencyLine)
            layout.addWidget(frequencyLine)

            layout.addWidget(QLabel("Mode"))
            modeBox = QComboBox()
            self.modeBoxes.append(modeBox)
            modeBox.addItems(self.modes)
            layout.addWidget(modeBox)

            layout.addWidget(QLabel("Position psc"))
            positionPrescaler = QComboBox()
            self.positionPrescalers.append(positionPrescaler)
            positionPrescaler.addItems(prescalers)
            layout.addWidget(positionPrescaler)

            layout.addWidget(QLabel("Telemetry psc"))
            telemetryPrescaler = QComboBox()
            self.telemetryPrescalers.append(telemetryPrescaler)
            telemetryPrescaler.addItems(prescalers)
            layout.addWidget(telemetryPrescaler)

        self.aprsSettings = QGroupBox('APRS Settings')
        self.aprsSettingsLayout = QFormLayout()
        self.aprsSettings.setLayout(self.aprsSettingsLayout)

        self.aprsCallsign = QLineEdit()
        self.aprsDesignator = QComboBox()
        self.aprsDesignator.addItems([str(i) for i in range(0, 16)])
        self.aprsDigiPath = QLineEdit()
        self.aprsSymbol = QComboBox()
        self.aprsSymbol.addItems(["BALLOON", "CAR", "ROCKET", "WX_STATION", "DIGI"])

        self.aprsSettingsLayout.addRow('CALLSIGN', self.aprsCallsign)
        self.aprsSettingsLayout.addRow('Designator', self.aprsDesignator)
        self.aprsSettingsLayout.addRow('Digi path', self.aprsDigiPath)
        self.aprsSettingsLayout.addRow('Symbol', self.aprsSymbol)
        self.frequencyConfigTabLayout.addWidget(self.aprsSettings)


    def init_sstv_layout(self):
        self.sstvConfigTab = QWidget()
        self.sstvConfigTabLayout = QHBoxLayout()
        self.sstvConfigTab.setLayout(self.sstvConfigTabLayout)

        self.sstvParametersGroupBox = QGroupBox('SSTV parameters')
        self.sstvParametersGroupBoxLayout = QFormLayout()
        self.sstvParametersGroupBox.setLayout(self.sstvParametersGroupBoxLayout)
        self.sstvConfigTabLayout.addWidget(self.sstvParametersGroupBox)

        self.sstvTextHeader = QLineEdit()
        self.sstvBHeaderEnabled = QCheckBox()
        self.sstvImageCnt = QComboBox()
        self.sstvImageCnt.addItems([str(i) for i in range(0, 15)])
        self.sstvImageCntPerFreq = QComboBox()
        self.sstvImageCntPerFreq.addItems([str(i) for i in range(0, 15)])

        self.sstvParametersGroupBoxLayout.addRow('Text header', self.sstvTextHeader)
        self.sstvParametersGroupBoxLayout.addRow('Text header enabled', self.sstvBHeaderEnabled)
        self.sstvParametersGroupBoxLayout.addRow('Images count', self.sstvImageCnt)
        self.sstvParametersGroupBoxLayout.addRow('Images per freq', self.sstvImageCntPerFreq)

        self.sstvImagesGroupBox = QGroupBox('Images')
        self.sstvImagesGroupBoxLayout = QVBoxLayout()
        self.sstvImagesGroupBox.setLayout(self.sstvImagesGroupBoxLayout)
        self.sstvConfigTabLayout.addWidget(self.sstvImagesGroupBox)

        self.sstvImagesSelectButton = QPushButton('Open images')
        self.sstvImagesGroupBoxLayout.addWidget(self.sstvImagesSelectButton)
        self.sstvImagesSelectButton.clicked.connect(self.sstv_file_chose_dialog)

        self.sstvImagesGroupBoxLayout.addWidget(QLabel('Selected images:'))
        self.sstvImagesSelectedList = QListWidget()
        self.sstvImagesGroupBoxLayout.addWidget(self.sstvImagesSelectedList)
        
        self.sstvImagesUploadButton = QPushButton('Upload images to device')
        self.sstvImagesGroupBoxLayout.addWidget(self.sstvImagesUploadButton)
        self.sstvImagesUploadButton.pressed.connect(self.init_sstv_upload)

        self.tabs.addTab(self.sstvConfigTab, "SSTV config")

    def sstv_file_chose_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        self.sstv_files, _ = QFileDialog.getOpenFileNames(self,"Select file", "","PNG (*.png);JPEG (*.jpg);;All Files (*)", options=options)
        
        self.sstvImagesSelectedList.clear()
        for image in self.sstv_files:
            thumbnail = QListWidgetItem()
            thumbnail.setText(image)
            thumbnail.setIcon(QIcon(image))
            self.sstvImagesSelectedList.addItem(thumbnail)

    def init_geoconig_layout(self):
        self.geoConfigTab = QWidget()
        self.geoConfigTabLayout = QVBoxLayout()
        self.geoConfigTab.setLayout(self.geoConfigTabLayout)

        self.geoConfigRowLayouts = []
        self.geoConfigModeBoxes = []
        self.geoConfigCordLines = []

        self.positionModes = ['TX INSIDE', 'TX OUTSIDE']

        for i in range(11):
            RowLayout = QHBoxLayout()
            self.geoConfigRowLayouts.append(RowLayout)
            self.geoConfigTabLayout.addLayout(RowLayout)

            RowLayout.addWidget(QLabel(str(i)+(".  " if i < 10 else ".")))

            PositionModeBox = QComboBox()
            PositionModeBox.addItems(self.positionModes)
            self.geoConfigModeBoxes.append(PositionModeBox)
            RowLayout.addWidget(PositionModeBox)

            CoordinatesLinesInRow = []
            for i in range(5):
                CoordLineX = QLineEdit()
                CoordLineY = QLineEdit()
                CoordinatesLinesInRow.append(CoordLineX)
                CoordinatesLinesInRow.append(CoordLineY)

                RowLayout.addWidget(QLabel("X"+str(i)))
                RowLayout.addWidget(CoordLineX)
                RowLayout.addWidget(QLabel("Y"+str(i)))
                RowLayout.addWidget(CoordLineY)

            self.geoConfigCordLines.append(CoordinatesLinesInRow)

        self.tabs.addTab(self.geoConfigTab, "Geofencing")

    def init_update_layout(self):
        self.fwUpdateTab = QWidget()
        self.fwUpdateTabLayout = QVBoxLayout()
        self.fwUpdateTab.setLayout(self.fwUpdateTabLayout)

        self.fwUpdateRowLayout = QHBoxLayout()
        self.fwUpdateTabLayout.addLayout(self.fwUpdateRowLayout)

        self.fwUpdateSelectButton = QPushButton('Select file')
        self.fwUpdateRowLayout.addWidget(self.fwUpdateSelectButton)
        self.fwUpdateSelectButton.clicked.connect(self.load_file_update_dialog)

        self.fwUpdateFileLabel = QLabel("firmware file not selected")
        self.fwUpdateRowLayout.addWidget(self.fwUpdateFileLabel)

        self.fwUpdateUploadButton = QPushButton('upload')
        self.fwUpdateUploadButton.clicked.connect(self.init_firmware_upload)
        self.fwUpdateTabLayout.addWidget(self.fwUpdateUploadButton)
        self.fwUpdateTabLayout.addStretch(1)

        self.tabs.addTab(self.fwUpdateTab, "Software update")

    def load_file_update_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        self.fw_file, _ = QFileDialog.getOpenFileName(self,"Select file", "","BIN (*.bin);;All Files (*)", options=options)
        
        if self.fw_file:
            self.fwUpdateFileLabel.setText(f"Wybrane pliki: {self.fw_file}")

    def init_firmware_upload(self):
        if not self.fw_file:
            return
        
        self.disable_buttons(True)
        self.fw_uploader.upload_firmware(self.fw_file, self.progress_callback)

    def init_sstv_upload(self):
        if not self.sstv_files:
            return

        self.disable_buttons(True)
        self.img_uploader.upload_images(self.sstv_files, self.progress_callback)

# app = QApplication(sys.argv)

# widget = SerialConfigurator()
# widget.show()

# sys.exit(app.exec_())
   