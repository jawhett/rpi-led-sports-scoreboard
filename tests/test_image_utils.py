import unittest
from PIL import Image, ImageDraw
from utils.image_utils import crop_image

class TestImageUtils(unittest.TestCase):
    def test_crop_image_rgba(self):
        # Create an RGBA image with transparent borders
        img = Image.new('RGBA', (20, 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([5, 5, 14, 14], fill=(255, 0, 0, 255))

        cropped = crop_image(img)

        self.assertEqual(cropped.size, (10, 10))
        self.assertEqual(cropped.mode, 'RGB')
        self.assertEqual(cropped.getpixel((0,0)), (255, 0, 0))

    def test_crop_image_all_transparent(self):
        # Create a completely transparent RGBA image
        img = Image.new('RGBA', (20, 20), (0, 0, 0, 0))

        cropped = crop_image(img)

        self.assertEqual(cropped.size, (20, 20))
        self.assertEqual(cropped.mode, 'RGB')
        self.assertEqual(cropped.getpixel((0,0)), (0, 0, 0))

    def test_crop_image_rgb(self):
        # Create an RGB image (no transparency)
        img = Image.new('RGB', (20, 20), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([5, 5, 14, 14], fill=(255, 0, 0))

        cropped = crop_image(img)

        # Bounding box of RGB should just be the non-zero pixels
        self.assertEqual(cropped.size, (10, 10))
        self.assertEqual(cropped.mode, 'RGB')
        self.assertEqual(cropped.getpixel((0,0)), (255, 0, 0))

    def test_crop_image_la(self):
        # Create an LA image with transparency
        img = Image.new('LA', (20, 20), (0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([5, 5, 14, 14], fill=(255, 255))

        cropped = crop_image(img)

        self.assertEqual(cropped.size, (10, 10))
        self.assertEqual(cropped.mode, 'RGB')
        self.assertEqual(cropped.getpixel((0,0)), (255, 255, 255))

    def test_crop_image_p(self):
        # Create a P image with transparency
        img = Image.new('P', (20, 20), 0)
        img.putpalette([0, 0, 0, 255, 0, 0])
        img.info['transparency'] = 0
        draw = ImageDraw.Draw(img)
        draw.rectangle([5, 5, 14, 14], fill=1)

        cropped = crop_image(img)

        self.assertEqual(cropped.size, (10, 10))
        self.assertEqual(cropped.mode, 'RGB')
        self.assertEqual(cropped.getpixel((0,0)), (255, 0, 0))

if __name__ == '__main__':
    unittest.main()
