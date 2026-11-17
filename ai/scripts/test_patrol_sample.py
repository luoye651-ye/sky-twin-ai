import unittest
from patrol_sample import select_records


class PatrolSamplingTests(unittest.TestCase):
    def setUp(self):
        self.pool = [{'id': f'data15_{i}'} for i in range(132)]

    def test_all_counts_and_no_duplicates(self):
        for count in range(1,133):
            sample = select_records(self.pool,count,'run-one')
            self.assertEqual(len(sample),count)
            self.assertEqual(len({r['id'] for r in sample}),count)
            self.assertTrue(all(r in self.pool for r in sample))

    def test_replay_and_input_order(self):
        self.assertEqual(select_records(self.pool,25,'run-one'),select_records(list(reversed(self.pool)),25,'run-one'))

    def test_new_run_samples_differ(self):
        self.assertNotEqual(select_records(self.pool,25,'run-one'),select_records(self.pool,25,'run-two'))

    def test_invalid_counts(self):
        for count in (0,133,-1,1.5):
            with self.assertRaises(ValueError): select_records(self.pool,count,'seed')

    def test_duplicate_pool_rejected(self):
        with self.assertRaises(ValueError): select_records([{'id':'a'},{'id':'a'}],1,'seed')
