import unittest
from patrol_metrics import match, overlap


class MatchingTests(unittest.TestCase):
    def gt(self, cls=0): return {"classId": cls, "box": [0,0,10,10]}
    def pred(self, confidence=.9, cls=0, box=None): return {"classId": cls, "box": box or [0,0,10,10], "confidence": confidence}
    def test_perfect(self):
        row=match([self.pred()], [self.gt()]); self.assertEqual((row['tp'],row['fp'],row['fn'],row['precision'],row['recall']), (1,0,0,1,1))
    def test_duplicate(self):
        row=match([self.pred(.4),self.pred(.9)], [self.gt()]); self.assertEqual((row['tp'],row['fp'],row['fn']), (1,1,0)); self.assertTrue(row['predictions'][0]['correct'])
    def test_wrong_class(self):
        row=match([self.pred(cls=1)],[self.gt()]); self.assertEqual((row['tp'],row['fp'],row['fn']), (0,1,1))
    def test_empty_predictions(self):
        row=match([],[self.gt()]); self.assertIsNone(row['precision']); self.assertEqual(row['recall'],0)
    def test_empty_truth(self):
        row=match([self.pred()],[]); self.assertIsNone(row['recall']); self.assertEqual(row['precision'],0)
    def test_empty_both(self):
        row=match([],[]); self.assertIsNone(row['precision']); self.assertIsNone(row['recall']); self.assertEqual(row['tp'],0)
    def test_iou_boundary(self):
        self.assertEqual(overlap([0,0,10,10],[0,0,5,10]),.5)
        self.assertEqual(match([self.pred(box=[0,0,5,10])],[self.gt()])['tp'],1)
    def test_missed(self): self.assertEqual(match([self.pred(box=[50,50,10,10])],[self.gt()])['fn'],1)
    def test_nonfinite(self):
        with self.assertRaises(ValueError): match([self.pred(float('nan'))],[self.gt()])


if __name__=='__main__': unittest.main(verbosity=2)
