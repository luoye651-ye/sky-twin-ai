import unittest
from vision_upload import normalized_box


class UploadBoxTests(unittest.TestCase):
    def test_normalizes_and_clamps(self):
        self.assertEqual(normalized_box([-10, 20, 100, 60], 200, 100), dict(x=0, y=.2, width=.5, height=.4))

    def test_empty_or_nonfinite_predictions_rejected(self):
        for box in ([20, 20, 10, 10], [0, 0, float('nan'), 10], [201, 0, 220, 10]):
            with self.assertRaises(ValueError): normalized_box(box, 200, 100)
