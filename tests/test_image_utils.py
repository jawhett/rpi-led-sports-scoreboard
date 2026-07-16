import unittest
from unittest.mock import MagicMock
from PIL import Image, ImageDraw
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.image_utils import clear_image

class TestImageUtils(unittest.TestCase):
    def test_clear_image_single(self):
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (100, 100)
        mock_draw = MagicMock(spec=ImageDraw.ImageDraw)

        clear_image(mock_image, mock_draw)

        mock_draw.rectangle.assert_called_once_with([(0, 0), (100, 100)], fill=(0, 0, 0))

    def test_clear_image_list(self):
        mock_images = [MagicMock(spec=Image.Image), MagicMock(spec=Image.Image)]
        mock_images[0].size = (50, 50)
        mock_images[1].size = (200, 150)
        mock_draws = [MagicMock(spec=ImageDraw.ImageDraw), MagicMock(spec=ImageDraw.ImageDraw)]

        clear_image(mock_images, mock_draws)

        mock_draws[0].rectangle.assert_called_once_with([(0, 0), (50, 50)], fill=(0, 0, 0))
        mock_draws[1].rectangle.assert_called_once_with([(0, 0), (200, 150)], fill=(0, 0, 0))

if __name__ == '__main__':
    unittest.main()
