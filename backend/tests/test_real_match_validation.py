"""Opt-in integration checks against the historical StatsBomb pilot."""
import os
import unittest
from app.historical_multi_match_api import (
    read_source, validate_event_identity, shot_summary, loss_to_shot,
    recovery_to_shot, set_piece_summary, flank_entries, fullback_loss_candidates,
)


@unittest.skipUnless(os.getenv('TACTIQRA_REAL_MATCH_TEST') == '1', 'Opt-in network test')
class RealMatchValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = read_source('events/3773386.json')
        validate_event_identity(cls.events)
        cls.by_id = {e['id']: e for e in cls.events}
        cls.own = 217
        cls.opp = next(e['team']['id'] for e in cls.events
                       if e.get('type', {}).get('name') == 'Shot'
                       and e['team']['id'] != cls.own)

    def test_reference_shot_counts(self):
        own, opp = shot_summary(self.events,self.own,self.opp)
        self.assertEqual((own['shots'],opp['shots']),(25,4))
        self.assertEqual((own['goals_from_shots'],opp['goals_from_shots']),(1,1))
        self.assertEqual((own['xg_count'],opp['xg_count']),(25,4))
        self.assertAlmostEqual(self.by_id['75bdc651-c041-4021-b201-cb9eb8b97837']['shot']['statsbomb_xg'],0.9761923,places=6)

    def test_transition_evidence(self):
        for fn, key in [(loss_to_shot,'loss_event_id'),(recovery_to_shot,'recovery_event_id')]:
            result=fn(self.events,self.own,self.opp)
            for side,tid in [('own',self.own),('opponent',self.opp)]:
                row=result[side]
                self.assertLessEqual(len(row['candidates']),row['covered'])
                self.assertLessEqual(row['covered'],row['shots'])
                for c in row['candidates']:
                    shot=self.by_id[c['shot_event_id']]
                    prior=self.by_id[c[key]]
                    self.assertEqual(shot['team']['id'],tid)
                    self.assertEqual(shot['period'],prior['period'])
                    self.assertTrue(0<=c['seconds']<=15)
                    if key=='recovery_event_id':
                        self.assertEqual(prior['team']['id'],tid)
                        self.assertEqual(prior['possession'],shot['possession'])
                    else:
                        self.assertNotEqual(prior['team']['id'],tid)

    def test_set_piece_and_flank_evidence(self):
        for side,tid in [('own',self.own),('opponent',self.opp)]:
            row=set_piece_summary(self.events,self.own,self.opp)[side]
            for kind,pattern in [('corner','From Corner'),('free_kick','From Free Kick'),('throw_in','From Throw In')]:
                expected={e['id'] for e in self.events if e.get('type',{}).get('name')=='Shot' and e.get('team',{}).get('id')==tid and e.get('play_pattern',{}).get('name')==pattern}
                self.assertEqual({e['event_id'] for e in row['categories'][kind]},expected)
            flank=flank_entries(self.events,self.own,self.opp)[side]
            for entry in flank['entries']:
                source=self.by_id[entry['event_id']]
                self.assertEqual(source['team']['id'],tid)
                self.assertEqual(source['location'][:2],entry['start'])
                self.assertEqual(source['pass']['end_location'][:2],entry['end'])
                self.assertTrue(entry['start'][0]<80<=entry['end'][0])
                self.assertNotIn('outcome',source['pass'])

    def test_fullback_evidence(self):
        for row in fullback_loss_candidates(self.events,self.own,self.opp).values():
            self.assertLessEqual(len(row['candidates']),row['position_known'])
            for c in row['candidates']:
                self.assertEqual(self.by_id[c['loss_event_id']]['position']['name'],c['position'])


if __name__ == '__main__':
    unittest.main()
