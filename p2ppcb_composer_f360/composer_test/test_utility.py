import typing as ty
import unittest

import adsk.core as ac

from composer_test.test_base import new_document

from f360_common import ATTR_GROUP, BadCodeException, F3AttributeDict, F3OccurrenceDict, SurrogateComponent, VirtualF3Occurrence, reset_context


TEST_M3D = ac.Matrix3D.create()
TEST_M3D.setCell(2, 3, 1.)
TEST_P3D = ac.Point3D.create(0., 0., 0.)
TEST_P3D.transformBy(TEST_M3D)


def raise_exception(*args, **kwargs):
    raise BadCodeException('Should not call this.')


class ShouldBeCalled:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, *args: ty.Any, **kwds: ty.Any):
        self.called = True


class MappingCheck:
    def __init__(self, d: ty.MutableMapping, tc: unittest.TestCase) -> None:
        self.d = d
        self.tc = tc

    def empty_check(self):
        self.tc.assertEqual(len(self.d), 0, 'Should be empty.')

    def contains_check(self, en: str, en_error: str):
        self.tc.assertTrue(en in self.d, '__contains__() test failed.')
        self.tc.assertFalse(en_error in self.d, '__contains__() test failed.')
        with self.tc.assertRaises(KeyError, msg='Should be not found.'):
            _ = self.d[en_error]
        with self.tc.assertRaises(KeyError, msg='Should be not found.'):
            del self.d[en_error]

    def iter_check(self, oracle_keys: ty.List[str]):
        keys: ty.List[str] = []
        for n in self.d:
            keys.append(n)
        self.tc.assertEqual(keys, oracle_keys, '__iter__() test failed.')


class TestF360Common(unittest.TestCase):
    def check_transform(self, t: ac.Matrix3D, msg: str):
        p = ac.Point3D.create(0., 0., 0.)
        p.transformBy(t)
        self.assertTrue(TEST_P3D.isEqualToByTolerance(p, 0.001), msg)

    def test_f3_attribute_dict(self):
        doc = new_document()
        con = reset_context()
        o = con.child.new_real('test_occ')
        attr_dict = F3AttributeDict(o.raw_occ.attributes)
        mc = MappingCheck(attr_dict, self)
        mc.empty_check()
        attr_dict['a1'] = 'a1'
        mc.contains_check('a1', 'a2')
        self.assertEqual(attr_dict['a1'], 'a1', '__getitem__() test failed.')
        mc.iter_check(['a1'])
        attr_dict['a1'] = 'A1'
        self.assertEqual(attr_dict['a1'], 'A1', '__setitem__() overwrite failed.')
        del attr_dict['a1']
        self.assertIsNone(attr_dict.raw_attrs.itemByName(ATTR_GROUP, 'a1'), '__delitem__ test failed.')
        doc.close(False)

    def test_f3_occurrence_dict(self):
        doc = new_document()
        con = reset_context()
        # root component
        occ_dict = F3OccurrenceDict(con.comp)
        mc = MappingCheck(occ_dict, self)
        mc.empty_check()
        o1 = occ_dict.new_real('o1')
        mc.contains_check('o1', 'o2')
        self.assertEqual(occ_dict['o1'].comp, o1.comp, '__getitem__() test failed.')
        mc.iter_check(['o1'])

        with self.assertRaises(BadCodeException, msg='Overwrite not detected.'):
            _ = occ_dict.new_real('o1')
        o1_2 = occ_dict.new_real('o1', overwrite=True, transform=TEST_M3D)
        self.check_transform(o1_2.transform, 'transform arg is not working.')
        o2 = occ_dict.new_real('o2')
        o3 = o2.child.new_real('o3')
        with self.assertRaises(KeyError, msg='name collision not detected.'):
            _ = o1_2.child.new_real('o3')
        o1 = occ_dict.new_real('o1', overwrite=True, transform=TEST_M3D)  # old o1 has been invalidated.

        with self.assertRaises(BadCodeException, msg='Impossible case not detected'):
            _ = occ_dict.new_surrogate('s1')
        s1 = o1.child.new_surrogate('s1')
        self.assertEqual(s1, o1.child['s1'])
        mc2 = MappingCheck(o1.child, self)
        mc2.contains_check('s1', 's2')
        mc2.iter_check(['s1'])

        o3_2 = o1.child.add(o3, transform=TEST_M3D, on_surrogate=raise_exception)
        self.check_transform(o3_2.transform, 'transform arg is not working.')
        self.assertEqual(o3_2.comp, o3.comp, 'Should have the same af.Component.')

        with self.assertRaises(BadCodeException, msg='Should not available to root component.'):
            _ = occ_dict.add(s1)
        sbc = ShouldBeCalled()
        s2 = o2.child.add(s1, transform=TEST_M3D, on_surrogate=sbc)
        self.assertTrue(sbc.called)
        self.check_transform(s2.transform, 'transform arg is not working.')

        with self.assertRaises(BadCodeException, msg='Should detect s1 is surrogate.'):
            _ = s1.child.get_real('foo')
        with self.assertRaises(BadCodeException, msg='Should detect s1 is surrogate.'):
            _ = o1.child.get_real('s1')
        self.assertEqual(o1.child.get_real('o3', on_create=raise_exception).comp, o3.comp, 'get_real() test failed.')
        sbc.called = False
        o4 = o1.child.get_real('o4', on_create=sbc)
        self.assertTrue(sbc.called, 'The on_create should be called.')

        self.assertEqual(o1.child.get('o4', on_surrogate=raise_exception).comp, o4.comp, 'get() failed.')
        self.assertEqual(o1.child.get('s1', on_surrogate=raise_exception).comp, s1.comp, 'get() failed.')
        sbc.called = False
        _ = o1.child.get('s3', on_surrogate=sbc)
        self.assertTrue(sbc.called, 'The on_surrogate should be called.')

        del o1.child['s1']
        self.assertFalse('s1' in o1.child)

        o1.child.clear()
        mc2.empty_check()

        doc.close(False)

    def test_surrogate_component(self):
        doc = new_document()
        con = reset_context()

        sc = SurrogateComponent.get('s1')
        with self.assertRaises(BadCodeException, msg='SurrogateComponent.bRepBodies is prohibited.'):
            _ = sc.bRepBodies
        self.assertTrue('s1' in con._surrogate_comps)
        self.assertEqual(SurrogateComponent.get('s1'), sc, 'Should return existing instance.')
        sc.delete_me()
        self.assertFalse('s1' in con._surrogate_comps)

        doc.close(False)

    def test_surrogate_f3_occurrence(self):
        doc = new_document()
        con = reset_context()

        o1 = con.child.new_real('o1')
        o2 = o1.child.new_real('o2')

        def get_surrogate(occ: VirtualF3Occurrence, name: str):
            s = occ.child.new_surrogate(name)
            s.transform = TEST_M3D
            s.comp_attr['ca'] = 'ca'
            s.occ_attr['oa'] = 'oa'
            return s

        def check_surrogate(occ: VirtualF3Occurrence):
            self.assertEqual(occ.comp_attr['ca'], 'ca', 'comp_attr should be migrated.')
            self.assertEqual(occ.occ_attr['oa'], 'oa', 'occ_attr should be migrated.')
            self.check_transform(occ.transform, 'transform property should be migrated.')
            self.assertEqual(occ.parent.child[occ.name].comp, occ.comp, 'parent-child relationship is corrupted.')

        s1 = get_surrogate(o1, 's1')
        with self.assertRaises(BadCodeException, msg='Reading raw_occ should raise.'):
            _ = s1.raw_occ
        check_surrogate(s1)

        s2 = s1.child.new_surrogate('s2')
        with self.assertRaises(BadCodeException, msg='replace() order violation should raise.'):
            s2.replace()

        # move_to() case
        del o1.child['s1']
        s1 = get_surrogate(o1, 's1')
        os1 = o2.child.new_real('s1')
        sbc = ShouldBeCalled()
        ros1 = s1.replace(on_create=sbc, real_occ=os1)
        self.assertTrue(sbc.called, 'The on_create should be called.')
        check_surrogate(ros1)

        # comp from con.des.allComponents
        s3 = get_surrogate(o1, 's3')
        os3 = o2.child.new_real('s3')
        os3.comp_attr['oa_from_real'] = 'oa_from_real'
        ros3 = s3.replace()
        check_surrogate(ros3)
        self.assertEqual(ros3.comp_attr['oa_from_real'], 'oa_from_real', 'comp_attr should be kept.')

        # comp is real
        s3_2 = o1.child.new_surrogate('s3', overwrite=True, comp=os3.comp)
        ros3_2 = s3_2.replace()
        self.assertEqual(ros3_2.comp_attr['oa_from_real'], 'oa_from_real', 'comp_attr should be kept.')

        doc.close(False)

    def test_attr_singleton(self):
        doc = new_document()
        con = reset_context()

        o1 = con.child.new_real('o1')
        con.attr_singleton['a1'] = ('a1', o1.raw_occ)
        con.attr_singleton['a2'] = ('a2', o1.comp)
        self.assertEqual(con.attr_singleton['a1'], ('a1', o1.raw_occ))
        self.assertEqual(con.attr_singleton['a2'], ('a2', o1.comp))
        del con.attr_singleton['a2']
        self.assertFalse('a2' in con.attr_singleton, 'should be deleted.')

        o1.comp_attr['a1'] = 'a1'
        with self.assertRaises(KeyError, msg='should find two attributes.'):
            _ = con.attr_singleton['a1']

        doc.close(False)
