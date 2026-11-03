"""Guard diagnostic identities and retain conservative blast protection."""
from pathlib import Path
import unittest

from test_ui_gating import function_body


SOURCE = Path(__file__).resolve().parents[1] / 'AutoplayXCom2/Src/AutoplayXCom2/Classes/APX_AreaAttackPlanner.uc'


class GrenadeBlockerDiagnosticsTests(unittest.TestCase):
    def test_identity_defaults_to_redacted_until_own_or_currently_visible(self):
        reject = function_body(SOURCE.read_text(), 'RejectBlast')
        own = reject.index('GetAssociatedPlayerID() == SourceUnit.GetAssociatedPlayerID()')
        visible = reject.index("ScanVisibleObjects.Find('ObjectID', BlockerID)")
        disclose = reject.index('if (bKnown)')
        self.assertLess(reject.index('ScanBlastBlockerID = 0;'), own)
        self.assertLess(reject.index('ScanBlastBlockerClass = "redacted";'), own)
        self.assertLess(own, disclose)
        self.assertLess(visible, disclose)
        self.assertGreater(reject.index('ScanBlastBlockerID = BlockerID;'), disclose)
        self.assertGreater(reject.index('string(BlockerObject.Class.Name)'), disclose)
        for attribute in ('ScanBlastBlockerRadial = Destructible.HasRadialDamage()',
                          'ScanBlastBlockerChildren = Destructible.AffectedChildren.Length',
                          'ScanBlastBlockerSurrounding = Destructible.bDestroysSurroundingArea'):
            self.assertGreater(reject.index(attribute), disclose)
        self.assertNotIn('TileLocation', reject)
        self.assertNotIn('.Location', reject)

    def test_scan_refreshes_visibility_and_does_not_reuse_previous_identity(self):
        source = SOURCE.read_text()
        choose = function_body(source, 'ChooseAction')
        self.assertIn('ScanVisibleObjects.Length = 0;', choose)
        self.assertIn('GetAllVisibleObjectsForPlayer(', choose)
        for reset in ('ScanBlastBlockerID = 0;', 'ScanBlastBlockerClass = "none";',
                      'ScanBlastBlockerGeometry = "none";', 'ScanBlastSafeRadius = -1.0;'):
            self.assertIn(reset, choose)
        self.assertIn('ScanBlastSafeRadius = LastBlastSafeRadius;', function_body(source, 'RejectBlast'))

    def test_missing_geometry_and_actual_proximity_are_distinguishable_without_relaxation(self):
        source = SOURCE.read_text()
        footprint = function_body(source, 'FootprintNearImpact')
        for label in ('no_interface', 'empty_footprint', 'near_footprint', 'clear_footprint'):
            self.assertIn('LastFootprintGeometry = "' + label + '";', footprint)
        self.assertIn('if (VisibleObject == none)\n        return true;', footprint)
        self.assertIn('if (Tiles.Length == 0)\n        return true;', footprint)
        blast = function_body(source, 'BlastIsSafe')
        self.assertIn('"objective", LastFootprintGeometry)', blast)
        self.assertIn('"protected_unit", LastFootprintGeometry)', blast)

    def test_distinguishes_radial_children_and_fracture_flags_but_keeps_all_guards(self):
        source = SOURCE.read_text()
        reject = function_body(source, 'RejectBlast')
        dangerous = function_body(source, 'HasDangerousScenery')
        for expression in ('Destructible.HasRadialDamage()', 'Destructible.AffectedChildren.Length',
                           'Destructible.bDestroysSurroundingArea'):
            self.assertIn(expression, reject)
            self.assertIn(expression, dangerous)
        summary = function_body(source, 'GetDiagnosticSummary')
        for field in ('pair_offset_centers=', 'blast_blocker_kind=', 'blast_blocker_id=',
                      'blast_blocker_class=', 'blast_blocker_geometry=', 'blast_blocker_radial=',
                      'blast_blocker_children=', 'blast_blocker_surrounding=', 'blast_safe_radius_units='):
            self.assertIn(field, summary)


if __name__ == '__main__':
    unittest.main()
