import unittest
from app.main import normalize_matches

class MatchSelectionTests(unittest.TestCase):
    def test_venue_sort_and_limit(self):
        def m(i, date, home):
            return {'id': i, 'utcDate': date, 'competition': {'code': 'PD'}, 'status': 'FINISHED', 'homeTeam': {'id': 1 if home else 2, 'name': 'A'}, 'awayTeam': {'id': 2 if home else 1, 'name': 'B'}, 'score': {'fullTime': {'home': 1, 'away': 0}}}
        raw = [m(1,'2026-01-01T00:00:00Z',True),m(2,'2026-03-01T00:00:00Z',False),m(3,'2026-02-01T00:00:00Z',True)]
        self.assertEqual([x['id'] for x in normalize_matches(raw,1,1,'home')],[3])
        self.assertEqual([x['id'] for x in normalize_matches(raw,1,2,'all')],[2,3])
        self.assertEqual([x['id'] for x in normalize_matches(raw,1,3,'away')],[2])

if __name__ == '__main__': unittest.main()
