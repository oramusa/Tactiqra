import unittest
from unittest.mock import patch
from app.historical_multi_match_api import (
    loss_to_shot, recovery_to_shot, set_piece_summary,
    flank_entries, fullback_loss_candidates, validate_event_identity, shot_summary, goal_origins,
)


def event(eid, kind, team=1, second=0, **extra):
    return dict(id=eid, type={'name': kind}, team={'id': team},
                timestamp=f'00:00:{second:06.3f}', period=1,
                possession=1, possession_team={'id': team}, **extra)


class TacticalIntelligenceTests(unittest.TestCase):
    def test_shot_xg_coverage_excludes_invalid_values(self):
        rows=[event(str(i),'Shot',1,1,shot={'statsbomb_xg':x}) for i,x in enumerate([0.25, None, float('nan'), -0.1, 1.1, True])]
        own, opponent=shot_summary(rows,1,2)
        self.assertEqual((own['shots'],own['xg_count'],own['xg_sum']),(6,1,0.25))
        self.assertIsNone(opponent['xg_sum'])

    def test_goal_origin_invalid_clock_is_uncovered(self):
        for clock in ['00:00:nan','00:00:inf','00:00:-1','00:61:00']:
            goal=event('g','Shot',1,1,shot={'outcome':{'name':'Goal'}})
            goal['timestamp']=clock
            with self.subTest(clock=clock):
                result=goal_origins([goal],1)
                self.assertEqual(len(result),1)
                self.assertEqual(result[0]['preceding_events'],[])

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            validate_event_identity([event('a','Pass'),event('a','Shot')])

    def test_invalid_identity_and_record_rejected(self):
        for row in [None, {}, event('','Pass'), event(' ','Pass')]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                validate_event_identity([row])

    def test_invalid_nested_fields_rejected(self):
        row=event('a','Shot',shot='invalid')
        with self.assertRaises(ValueError):
            validate_event_identity([row])

    def test_optional_fields_can_be_missing(self):
        validate_event_identity([event('a','Pass'),event('b','Shot',shot=None)])

    def test_loss_nearest_boundary_and_direction(self):
        rows = [event('a','Error',2,0), event('b','Miscontrol',2,5),
                event('s','Shot',1,20)]
        result = loss_to_shot(rows,1,2)
        self.assertEqual(result['own']['covered'],1)
        self.assertEqual(result['own']['candidates'][0]['loss_event_id'],'b')
        self.assertEqual(result['own']['candidates'][0]['seconds'],15)
        self.assertEqual(result['opponent']['shots'],0)

    def test_loss_outside_window_and_period(self):
        loss = event('a','Error',1,0)
        shot = event('s','Shot',2,16)
        self.assertEqual(loss_to_shot([loss,shot],1,2)['opponent']['candidates'],[])
        shot.update(period=2,timestamp='00:00:01.000')
        self.assertEqual(loss_to_shot([loss,shot],1,2)['opponent']['candidates'],[])

    def test_malformed_clock_is_uncovered(self):
        loss = event('a','Error',2,0)
        loss['timestamp']='invalid'
        shot = event('s','Shot',1,10)
        result=loss_to_shot([loss,shot],1,2)['own']
        self.assertEqual((result['shots'],result['covered']),(1,0))

    def test_recovery_same_possession_and_failure(self):
        recovery=event('r','Ball Recovery',2,0)
        shot=event('s','Shot',2,15)
        result=recovery_to_shot([recovery,shot],1,2)['opponent']
        self.assertEqual(result['candidates'][0]['recovery_event_id'],'r')
        recovery['ball_recovery']={'recovery_failure':True}
        self.assertEqual(recovery_to_shot([recovery,shot],1,2)['opponent']['candidates'],[])
        recovery.pop('ball_recovery')
        shot['possession']=2
        self.assertEqual(recovery_to_shot([recovery,shot],1,2)['opponent']['candidates'],[])

    def test_recovery_missing_possession(self):
        shot=event('s','Shot',1,10)
        shot.pop('possession')
        result=recovery_to_shot([shot],1,2)['own']
        self.assertEqual((result['shots'],result['covered']),(1,0))

    def test_set_piece_coverage_and_xg(self):
        rows=[event('s','Shot',1,1,play_pattern={'name':'From Corner'},
                    shot={'statsbomb_xg':0.2,'outcome':{'name':'Goal'}}),
              event('t','Shot',1,2),
              event('u','Shot',2,3,play_pattern={'name':'From Free Kick'},
                    shot={'statsbomb_xg':float('nan')})]
        result=set_piece_summary(rows,1,2)
        self.assertEqual((result['own']['shots'],result['own']['classified']),(2,1))
        self.assertTrue(result['own']['categories']['corner'][0]['goal'])
        self.assertIsNone(result['opponent']['categories']['free_kick'][0]['xg'])

    def test_flank_boundaries_and_missing_location(self):
        rows=[event('l','Pass',1,1,location=[79,0],pass_={'end_location':[80,0]}),
              event('c','Pass',1,2,location=[79,40],pass_={'end_location':[80,40]}),
              event('r','Pass',1,3,location=[79,80],pass_={'end_location':[80,80]}),
              event('inside','Pass',1,4,location=[80,40],pass_={'end_location':[90,40]}),
              event('missing','Pass',1,5,pass_={'end_location':[90,40]}),
              event('failed','Pass',1,6,location=[79,40],pass_={'end_location':[90,40],'outcome':{'name':'Incomplete'}})]
        for row in rows:
            row['pass']=row.pop('pass_')
        result=flank_entries(rows,1,2)['own']
        self.assertEqual((result['completed'],result['located']),(5,4))
        self.assertEqual([e['lane'] for e in result['entries']],['left','center','right'])

    def test_fullback_reuses_precomputed_loss_windows(self):
        rows=[event('l','Dispossessed',1,0,position={'name':'Right Back'},location=[60,10]),
              event('s','Shot',2,10)]
        expected=fullback_loss_candidates(rows,1,2)
        windows=loss_to_shot(rows,1,2)
        with patch('app.historical_multi_match_api.loss_to_shot',side_effect=AssertionError('Unexpected rescan')):
            self.assertEqual(fullback_loss_candidates(rows,1,2,loss_windows=windows),expected)

    def test_fullback_position_and_raw_location(self):
        loss=event('l','Dispossessed',1,0,position={'name':'Right Back'},location=[60,10])
        shot=event('s','Shot',2,10)
        result=fullback_loss_candidates([loss,shot],1,2)['opponent']
        self.assertEqual(result['position_known'],1)
        self.assertTrue(result['candidates'][0]['advanced_raw'])
        loss.pop('position')
        result=fullback_loss_candidates([loss,shot],1,2)['opponent']
        self.assertEqual(result['position_known'],0)
        self.assertEqual(result['candidates'],[])


if __name__ == '__main__':
    unittest.main()
