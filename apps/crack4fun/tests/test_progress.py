import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace'))
from progress import Store
from programs import catalog


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.store=Store(self.temp.name)
    def test_flags_are_distinct_and_private_and_persist(self):
        flags=[self.store.flag(c['id']) for p in catalog() for c in p['challenges']]
        self.assertEqual(len(flags),17);self.assertEqual(len(set(flags)),17)
        for flag in flags:self.assertRegex(flag,r'^\{[a-z0-9_]+\}$')
        public=json.dumps(self.store.public())+json.dumps(catalog())
        self.assertNotIn(self.store.read()['secret'],public)
        self.assertTrue(all(flag not in public for flag in flags))
        self.assertEqual(Store(self.temp.name).flag('fs-01'),flags[0])
    def test_format_wrong_challenge_and_duplicate(self):
        with self.assertRaises(ValueError):self.store.submit('fs-01','FLAG{bad}')
        self.assertFalse(self.store.submit('fs-01',self.store.flag('fo-01'))['correct'])
        flag=self.store.flag('fs-01')
        self.assertFalse(self.store.submit('fs-01','{wrong}')['correct'])
        self.assertTrue(self.store.submit('fs-01',' \n'+flag+'\n ')['correct'])
        self.assertTrue(self.store.submit('fs-01',flag)['already'])
        self.assertEqual(len(self.store.public()['completed']),1)
    def test_clear_and_switch_are_scoped(self):
        for c in ['fs-01','fo-01']:self.store.submit(c,self.store.flag(c))
        self.store.activate('forensics');self.store.clear('fs')
        self.assertEqual(self.store.public()['active'],'forensics')
        self.assertEqual(set(self.store.public()['completed']),{'fo-01'})

    def test_tutorial_completion_persists_independently(self):
        self.assertFalse(self.store.public()['tutorial_seen'])
        self.store.finish_tutorial()
        self.assertTrue(Store(self.temp.name).public()['tutorial_seen'])
        self.store.clear('fs')
        self.assertTrue(self.store.public()['tutorial_seen'])
        self.assertEqual(self.store.public()['completed'], {})
