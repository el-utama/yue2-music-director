import unittest
from yue2_music_director.score_guard import UnsupportedScore, validate_score


class ScoreTests(unittest.TestCase):
    def test_valid_simple_score(self):
        abc = 'X:1\nT:Demo\nM:2/4\nL:1/16\nK:Bb\n% chorus\nV: Vocal\n"Bb"C2D2E2F2|\nV: Ins\nZ|\n'
        result = validate_score(abc)
        self.assertEqual(result['bars'], {'Vocal':1, 'Ins':1})
        self.assertEqual(result['errors'], [])

    def test_bar_duration_mismatch(self):
        abc = 'M:2/4\nL:1/16\nV: Vocal\nC7|\nV: Ins\nZ|\n'
        self.assertTrue(validate_score(abc)['errors'])

    def test_unsupported_construct_fails(self):
        abc = 'M:2/4\nL:1/16\nV: Vocal\n{ornament}C8|\nV: Ins\nZ|\n'
        with self.assertRaises(UnsupportedScore):
            validate_score(abc)


if __name__ == '__main__':
    unittest.main()
