import unittest
from unittest.mock import Mock, patch
from patrol_io import replace_with_retry


class AtomicProgressTests(unittest.TestCase):
    def test_brief_windows_reader_lock(self):
        source = Mock()
        source.replace.side_effect = [PermissionError(),PermissionError(),None]
        with patch('patrol_io.time.sleep') as sleep:
            replace_with_retry(source,'progress.json')
        self.assertEqual(source.replace.call_count,3)
        self.assertEqual(sleep.call_count,2)

    def test_permanent_lock_is_not_silently_ignored(self):
        source = Mock()
        source.replace.side_effect = PermissionError()
        with patch('patrol_io.time.sleep'), self.assertRaises(PermissionError):
            replace_with_retry(source,'progress.json')
        self.assertEqual(source.replace.call_count,40)

    def test_other_io_errors_are_not_retried(self):
        source = Mock()
        source.replace.side_effect = FileNotFoundError()
        with self.assertRaises(FileNotFoundError):
            replace_with_retry(source,'progress.json')
        self.assertEqual(source.replace.call_count,1)


if __name__ == '__main__':
    unittest.main()
