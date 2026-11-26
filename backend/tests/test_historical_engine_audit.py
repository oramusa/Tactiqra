import unittest
from app.historical_multi_match_api import (
    validate_event_identity, playing_style, attacking_patterns, loss_to_shot,
    recovery_to_shot, transition_intelligence, fullback_loss_candidates,
    set_piece_summary, defensive_weakness, set_piece_intelligence,
    player_intelligence, spatial_network,
)

def event(i, kind, team=1, **fields):
    return dict(id=str(i), index=i, type={'name':kind}, team={'id':team},
                player={'id':team*10,'name':str(team)}, period=1, possession=1,
                possession_team={'id':1}, timestamp=f'00:00:{i:02d}.000',
                location=[50,40], **fields)

class HistoricalEngineAudit(unittest.TestCase):
    def test_identity(self):
        validate_event_identity([event(1,'Pass'),event(2,'Shot')])
        for rows in ([event(1,'Pass'),event(1,'Shot')],[event(2,'Pass'),event(1,'Shot')]):
            with self.assertRaises(ValueError):
                validate_event_identity(rows)

    def test_engine_contract(self):
        rows=[event(1,'Ball Recovery'),event(2,'Pass',pass_ignored=True),
              event(3,'Dispossessed',team=2),event(4,'Shot',shot={'outcome':{'name':'Goal'}})]
        rows[1]['pass']={'recipient':{'id':11},'end_location':[110,40],'length':60,'type':{'name':'Corner'}}
        rows[3]['play_pattern']={'name':'From Corner'}
        rows[2]['position']={'name':'Right Back'}
        validate_event_identity(rows)
        style=playing_style(rows,1,2)
        attack=attacking_patterns(rows,1,2)
        loss=loss_to_shot(rows,1,2)
        recovery=recovery_to_shot(rows,1,2)
        fb=fullback_loss_candidates(rows,1,2,loss_windows=loss)
        sp=set_piece_summary(rows,1,2)
        defense=defensive_weakness(rows,1,2,attack,loss,fb,sp)
        tr=transition_intelligence(rows,recovery,loss)
        restart=set_piece_intelligence(rows,1,2)
        player=player_intelligence(rows,1,2)
        net=spatial_network(rows,1,2)
        self.assertEqual(style['own']['completed'],1)
        self.assertEqual(len(attack['own']['box_entries']),1)
        self.assertEqual(defense['opponent']['shots'],1)
        self.assertEqual(len(defense['opponent']['loss_candidates']),1)
        self.assertEqual(tr['own']['recovery']['thresholds']['5']['goals'],1)
        self.assertEqual(restart['own']['corner']['matched_shots'],1)
        self.assertEqual(player['own'][0]['goals'],1)
        self.assertEqual(net['own']['links'][0]['count'],1)
        self.assertEqual(sum(c['count'] for c in net['own']['cells']),3)

if __name__=='__main__':
    unittest.main()
