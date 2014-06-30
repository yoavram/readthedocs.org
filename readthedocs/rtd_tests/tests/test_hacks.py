import sys

from django.test import TestCase

from core import hacks


class TestHacks(TestCase):
    fixtures = ['eric.json', 'test_data.json']

    def setUp(self):
        hacks.patch_meta_path()

    def tearDown(self):
        hacks.unpatch_meta_path()

    def test_hack_importer_order(self):
        self.assertTrue(len(sys.meta_path) > 1)
        self.assertTrue(isinstance(sys.meta_path[-1], hacks.ErrorlessImport))

    def test_hack_failed_import(self):
        import boogy
        self.assertEqual(str(boogy), "<Silly Human, I'm not real>")

    def test_hack_failed_local_import(self):
        def _import():
            import readthedocs.core.__non_existant__
        self.assertRaises(ImportError, _import)

    def test_hack_correct_import(self):
        import itertools
        self.assertNotEqual(str(itertools), "<Silly Human, I'm not real>")

    def test_hack_correct_local_import(self):
        import readthedocs.core.utils
        self.assertNotEqual(str(readthedocs.core.utils),
                            "<Silly Human, I'm not real>")

    def test_hack_correct_relative_import(self):
        import core.utils
        self.assertNotEqual(str(core.utils), "<Silly Human, I'm not real>")

    def test_hack_correct_relative_import_submodule(self):
        from core import utils
        self.assertNotEqual(str(utils), "<Silly Human, I'm not real>")
