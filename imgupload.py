from PIL import Image
from flashaccess import FlashAccess

class ImgUpload:
    width = 320
    height = 240
    img_base_address = 0x40000
    img_offset = 3 * 0x10000

    def __init__(self, comm_interface):
        self.flash_access = FlashAccess(comm_interface)
        self.image_idx = 0
        self.filenames = []
        self.status_callback = None
        self.write_address = ImgUpload.img_base_address

    def upload_images(self, filenames, status_callback):
        if self.image_idx or not len(filenames):
            return False
        self.filenames = filenames
        self.status_callback = status_callback
        self.write_address = ImgUpload.img_base_address
        self.image_idx = 0
        self.write_done_cb(0)
        return True

    def write_done_cb(self, progress):
        if progress == -1 or self.image_idx >= len(self.filenames):
            self.image_idx = 0
            return self.status_callback(100)

        img_serialized = self.prepare_next_image()
        if not len(img_serialized):
            self.image_idx = 0
            return self.status_callback(100)

        print(f'img upl sending {len(img_serialized)}B')

        self.flash_access.write_to_flash(
            self.write_address,
            img_serialized,
            self.write_done_cb
        )
        self.write_address += ImgUpload.img_offset
        self.image_idx += 1
        self.status_callback(int((self.image_idx / len(self.filenames)) * 100))

    def prepare_next_image(self):
        if self.image_idx >= len(self.filenames):
            return bytearray()

        img = Image.open(self.filenames[self.image_idx])
        img = img.convert('RGB')

        if img.size != (self.width, self.height):
            print(f"Warning: image resized from {img.size} to {(self.width, self.height)}")
            img = img.resize((self.width, self.height), Image.LANCZOS)

        pixels = img.load()
        tx_buff = bytearray()
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = pixels[x, y]
                tx_buff.extend([r, g, b])

        return tx_buff
