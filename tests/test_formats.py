from pathlib import Path
import tempfile
import unittest
from PIL import Image
from pillow_heif import register_heif_opener
from scorestudio.recognition import load_image

class FormatTests(unittest.TestCase):
    def test_supported_image_decoders(self):
        register_heif_opener()
        with tempfile.TemporaryDirectory(dir='tmp') as temp:
            image=Image.new('RGB',(64,48),'white')
            for extension in ['png','jpg','webp','bmp','tiff','heic']:
                with self.subTest(extension=extension):
                    path=Path(temp)/('sample.'+extension)
                    image.save(path)
                    restored=load_image(path)
                    self.assertEqual(restored.size,(64,48))
                    self.assertEqual(restored.mode,'RGB')

if __name__=='__main__':unittest.main()
