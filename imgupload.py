from PIL import Image
from flashaccess import FlashAccess

class ImgUpload:
    width = 320
    img_base_address = 0x40000
    img_offset = 3 * 0x10000
    def __init__(self, comm_interface):
        self.flash_access = FlashAccess(comm_interface)

    def upload_images(self, filenames, status_callback):
        if self.image_idx or not len(filenames):
            return False
        self.filenames = filenames
        self.status_callback = status_callback
        self.write_address = ImgUpload.img_base_address
        self.write_done_cb()

    def write_done_cb(self, progress):
        img_serialized = self.prepare_next_image()
        if not len(img_serialized) or progress == -1:
            return self.status_callback(100)
        
        self.flash_access.write_to_flash(self.write_address,
                                         img_serialized,
                                         self.write_done_cb)
        self.write_address += ImgUpload.img_offset
    
    def prepare_next_image(self):
        if not len(self.filenames):
            return bytearray()
        
        img = Image.open(self.filenames.pop(0))
        img = img.convert('RGB')
        if img.size[0] != self.width:
            print("image not cropped to 320px in width")

        pixels = img.load()
        tx_buff = bytearray()
        pixel_cnt = img.size[0] * img.size[1]
        for i in range(pixel_cnt):
            x = i % img.size[0]
            y = i / img.size[0]
            for color in range(3):
                tx_buff.append(pixels[x, y][color])
        return tx_buff