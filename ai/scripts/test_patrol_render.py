import tempfile
from pathlib import Path
import unittest
from PIL import Image
from patrol_eval import render


class PatrolPreviewTests(unittest.TestCase):
    def test_no_banner_and_keep_image_size(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'preview.jpg'
            render(Image.new('RGB',(640,360),(100,180,210)),[],target,True)
            with Image.open(target) as image:
                self.assertEqual(image.size,(640,360))
                for x in (10,100,320,630):
                    self.assertTrue(all(abs(a-b)<=3 for a,b in zip(image.getpixel((x,5)),(100,180,210))))

    def test_prediction_box_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'preview.jpg'
            render(Image.new('RGB',(640,360),'white'),[{'classId':0,'confidence':.8,'box':[100,100,80,80]}],target,True)
            with Image.open(target) as image:
                r,g,b = image.getpixel((100,140))
                self.assertGreater(r,180)
                self.assertGreater(g,150)
                self.assertLess(b,140)
