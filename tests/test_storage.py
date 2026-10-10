import concurrent.futures
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import storage as s


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        s.DATA_DIR=Path(self.tmp.name)
        s.DB_PATH=s.DATA_DIR/'backbenchers.sqlite3'
        s.init_db()
        self.assertTrue(s.create_room('Office Crew','office123','admin123'))
        self.alex=s.register('Alex','1234')
        self.taylor=s.register('Taylor','3344')

    def tearDown(self):
        self.tmp.cleanup()

    def test_room_first_setup_and_login(self):
        self.assertFalse(s.create_room('Another Room','another123','anotherpin'))
        self.assertTrue(s.validate_room_code('office123'))
        self.assertFalse(s.validate_room_code('incorrect'))
        self.assertTrue(s.validate_host_pin('admin123'))
        self.assertFalse(s.validate_host_pin('office123'))
        self.assertEqual(s.login('aLeX','1234')['id'],self.alex['id'])
        self.assertIsNone(s.login('Alex','bad pin'))
        with self.assertRaisesRegex(ValueError,'already taken'):
            s.register('ALEX','1234')

    def test_vote_and_final_result(self):
        bid=s.new_bill(self.alex['id'],'Chai at four','A friendly 4 PM break')
        s.vote(bid,self.alex['id'],'Aye')
        s.vote(bid,self.alex['id'],'No')
        s.vote(bid,self.taylor['id'],'Aye')
        rows=s.bills()
        self.assertEqual((rows[0]['aye'],rows[0]['no'],rows[0]['abstain']), (1,1,0))
        self.assertEqual(s.my_vote(bid,self.alex['id']),'No')
        s.close_bill(bid)
        with self.assertRaises(ValueError):
            s.vote(bid,self.alex['id'],'Aye')

    def test_concurrent_users_one_vote_each(self):
        users=[s.register('Player'+str(i),'4321') for i in range(7)]
        bid=s.new_bill(self.alex['id'],'Chai break vote','Test seven devices')
        def cast(u):
            for _ in range(4):
                s.vote(bid,u['id'],'Aye')
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
            list(pool.map(cast,users))
        self.assertEqual(s.bills()[0]['aye'],7)
        self.assertEqual(s.stats()['proposals'],1)

    def test_moderation_and_reactions(self):
        pid=s.add_post(self.alex['id'],'Appreciation','Well done to everyone today!')
        self.assertEqual(len(s.posts()),0)
        self.assertEqual(len(s.posts('pending')),1)
        s.moderate_post(pid,'approved')
        self.assertEqual(s.posts()[0]['nickname'],'Alex')
        s.react(pid,self.taylor['id'],'👏')
        s.react(pid,self.taylor['id'],'💡')
        self.assertEqual(s.reactions_for(pid),{'💡':1})
        with self.assertRaises(ValueError):
            s.add_post(self.alex['id'],'Unlisted','Test nonapproved category')

    def test_live_moments(self):
        mid=s.add_moment(self.alex['id'],'Applause','Nice work team!','A very good day',30)
        self.assertEqual(s.current_moment()['id'],mid)
        self.assertEqual(len(s.recent_moments()),1)
        with s.connect() as c:
            c.execute('UPDATE moments SET expires_at=? WHERE id=?',(s.now()-1,mid))
        self.assertIsNone(s.current_moment())

    def test_presence(self):
        s.heartbeat(self.alex['id'])
        self.assertGreaterEqual(s.stats()['online'],2)
        with s.connect() as c:
            c.execute('UPDATE members SET last_seen=? WHERE id=?',(s.now()-100,self.taylor['id']))
        self.assertEqual(s.stats()['online'],1)

if __name__=='__main__':
    unittest.main()
