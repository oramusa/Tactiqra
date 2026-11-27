"""Opt-in real StatsBomb fixture validation; network failures fail the run."""
import unittest
from app import historical_multi_match_api as api

class RealMatchAudit(unittest.TestCase):
    def test_barcelona_fixture(self):
        mid=3773386
        meta=next(m for m in api.read_source('matches/11/90.json') if m['match_id']==mid)
        home=meta['home_team']['home_team_id']
        away=meta['away_team']['away_team_id']
        events=api.read_source(f'events/{mid}.json')
        api.validate_event_identity(events)
        self.assertEqual({e['team']['id'] for e in events if e.get('team')},{home,away})
        attack=api.attacking_patterns(events,home,away)
        loss=api.loss_to_shot(events,home,away)
        recovery=api.recovery_to_shot(events,home,away)
        fb=api.fullback_loss_candidates(events,home,away,loss_windows=loss)
        sp=api.set_piece_summary(events,home,away)
        defense=api.defensive_weakness(events,home,away,attack,loss,fb,sp)
        tr=api.transition_intelligence(events,recovery,loss)
        style=api.playing_style(events,home,away)
        players=api.player_intelligence(events,home,away)
        net=api.spatial_network(events,home,away)
        restarts=api.set_piece_intelligence(events,home,away)
        ids={e['id'] for e in events}
        for side,tid,other in [('own',home,'opponent'),('opponent',away,'own')]:
            own=[e for e in events if (e.get('team') or {}).get('id')==tid]
            shots=[e for e in own if e['type']['name']=='Shot']
            passes=[e for e in own if e['type']['name']=='Pass']
            complete=[e for e in passes if (e.get('pass') or {}).get('outcome') is None]
            self.assertEqual(style[side]['passes'],len(passes))
            self.assertEqual(style[side]['completed'],len(complete))
            self.assertEqual(attack[side]['shots'],len(shots))
            self.assertEqual(defense[other]['shots'],len(shots))
            self.assertEqual(sum(p['shots'] for p in players[side]),sum(isinstance((e.get('player') or {}).get('id'),int) for e in shots))
            for kind in ('loss','recovery'):
                w=tr[side][kind]
                self.assertLessEqual(len(w['candidates']),w['covered'])
                self.assertLessEqual(w['covered'],len(shots))
                self.assertEqual(w['thresholds']['15']['shots'],len(w['candidates']))
            for edge in net[side]['links']:
                self.assertEqual(edge['count'],len(edge['ids']))
                self.assertTrue(set(edge['ids'])<=ids)
            for cat in restarts[side].values():
                self.assertLessEqual(cat['matched_shots'],len(cat['shots']))
            print(side, 'shots',len(shots),'passes',len(passes),'completed',len(complete))
        print('Fixture:',mid,meta['home_team']['home_team_name'],meta['away_team']['away_team_name'])

if __name__=='__main__':
    unittest.main()
