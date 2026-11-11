"""Recorder integration contracts; these do not execute the WOTC engine.

The simple sanitizing helper is executed from its actual UC body. Historical
visibility, read-only behavior and dispatch ordering are checked at their source
boundaries because the native history/cache are unavailable on Linux.
"""
import os
from pathlib import Path
import re
import unittest

from test_ui_gating import CHECKS, function_body


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ROOT / 'AutoplayXCom2/Src/AutoplayXCom2/Classes'
SOURCE = (CLASSES / 'APX_MissionRecorder.uc').read_text(encoding='utf-8-sig')


class MissionRecorderContracts(unittest.TestCase):
    def test_field_sanitizer_preserves_one_record_per_line(self):
        body = function_body(SOURCE, 'Safe')
        namespace = {'Repl': lambda value, old, new: value.replace(old, new), 'Chr': chr}
        lines = ['def sanitize(Value):'] + ['    ' + line.strip().rstrip(';')
                 for line in body.splitlines() if line.strip()]
        exec('\n'.join(lines), namespace)
        self.assertEqual(namespace['sanitize']('reason|spoof=true\r\nnext'),
                         'reason/spoof=true  next')
        self.assertEqual(namespace['sanitize']('ordinary_label'), 'ordinary_label')

    def test_recorder_does_not_mutate_game_state_or_roll_rng(self):
        code = CHECKS.without_comments(SOURCE)
        forbidden = r'\b(?:ModifyStateObject|CreateNewGameState|SubmitGameState|ActivateAbility_ReturnContext|Rand|FRand)\s*\('
        self.assertIsNone(re.search(forbidden, code))
        self.assertIn("GetAllVisibleEnemiesForPlayer(", code)

    def test_output_and_history_work_are_bounded(self):
        emit = function_body(SOURCE, 'Emit')
        self.assertIn('Sequence >= Clamp(MaxRecords, 100, 100000)', emit)
        self.assertIn('event=limit', emit)
        results = function_body(SOURCE, 'RecordResults')
        self.assertIn('HistoryCursor + Clamp(MaxHistoryFramesPerObserve, 16, 2048)', results)
        self.assertIn('HistoryCursor < EndIndex && !bLimitReported', results)
        self.assertIn('history_pending=', function_body(SOURCE, 'Finish'))

    def test_actual_result_requires_own_source_or_target_and_skips_interrupt(self):
        results = function_body(SOURCE, 'RecordResults')
        self.assertIn('if (!bOwnAction && !bOwnTarget)', results)
        interrupt = results.index('Context.InterruptionStatus == eInterruptionStatus_Interrupt')
        result = results.index('Emit("result",')
        self.assertLess(interrupt, result)
        self.assertIn('continue;', results[interrupt:result])
        self.assertIn('MultiTargetHitResults.Length', results)

    def test_previous_visibility_is_reset_for_every_action(self):
        results = function_body(SOURCE, 'RecordResults')
        reset = results.index('BeforeActionEnemies.Length = 0;')
        prior = results.index('OwnerPlayerID, BeforeActionEnemies, HistoryCursor - 1')
        redaction = results.index('// Preserve friendly targets') if '// Preserve friendly targets' in results else results.index('if (!IsOwnUnitAt(TargetID, HistoryCursor)')
        self.assertLess(reset, prior)
        self.assertLess(prior, redaction)
        self.assertIn('SourceID = 0;', results)

    def test_available_actions_include_handler_even_when_not_selected(self):
        available = function_body(SOURCE, 'RecordAvailability')
        self.assertIn('foreach Cache.AvailableActions(Action)', available)
        self.assertIn('|code=', available)
        self.assertIn('|input=', available)
        self.assertIn('|handler=', available)
        self.assertIn('AbilityHandler(UnitState, Ability.GetMyTemplateName())', available)
        handler = function_body(SOURCE, 'AbilityHandler')
        self.assertIn('IsObjectiveAbility(', handler)
        self.assertIn('return "unhandled";', handler)

    def test_chosen_preview_is_cached_before_activation(self):
        controller = (CLASSES / 'APX_Controller.uc').read_text(encoding='utf-8-sig')
        decision = function_body(controller, 'MakeDecision')
        self.assertLess(decision.index('MissionRecorder.PrepareChosenAction('),
                        decision.index('ActivateAbility_ReturnContext('))
        self.assertLess(decision.index('MissionRecorder.PrepareChosenMove('),
                        decision.index('PC.GameStateMoveUnitSingle('))
        self.assertLess(decision.index('MissionRecorder.PrepareChosenArea('),
                        decision.index('ActivateAbility_ReturnContext('))
        for name in ('ChosenAction', 'ChosenMove'):
            body = function_body(SOURCE, name)
            self.assertIn('PreparedChoiceFields', body)
            self.assertNotIn('ActionFields(', body)
            self.assertNotIn('MoveFields(', body)
        self.assertIn('PreparedChoiceFields = "";', function_body(SOURCE, 'BeginDecision'))

    def test_selected_grenade_uses_affected_units_and_native_secondary_damage_preview(self):
        area = function_body(SOURCE, 'RecordAreaTargetPreviews')
        self.assertIn('SelectedTarget = Action.AvailableTargets[TargetIndex];', area)
        self.assertIn('foreach SelectedTarget.AdditionalTargets(TargetRef)', area)
        self.assertIn('Grenade.LaunchedGrenadeEffects', area)
        self.assertIn('Grenade.ThrownGrenadeEffects', area)
        self.assertIn('Effect.GetDamagePreview(TargetRef, Ability, false,', area)
        self.assertNotIn('Ability.GetDamagePreview(', area)
        self.assertIn('PreviewDamageAfterArmor(', area)
        self.assertIn('if (bFalloff)\n            MinTotal = 0.0;', area)
        for field in ('preview_raw_min_damage', 'preview_raw_max_damage',
                      'preview_min_damage', 'preview_max_damage', 'explosive_falloff'):
            self.assertIn('|'+field+'=', area)

    def test_move_trace_explains_loss_of_attack_eligibility_after_blue_move(self):
        move = function_body(SOURCE, 'MoveFields')
        self.assertIn('GetMoveAttackOptions(UnitState, VisibleEnemies,', move)
        for field in ('best_attack_now', 'best_attack_after_move_ap', 'potential_attack_loss'):
            self.assertIn('|' + field + '=', move)
        self.assertIn('FMax(0.0, BestAttackNow - BestAttackAfterMove)', move)

    def test_source_links_and_recognized_melee_envelope_are_visible_in_diagnostics(self):
        action = function_body(SOURCE, 'ActionFields')
        preview = function_body(SOURCE, 'RecordMoveThreatPreviews')
        self.assertIn('GetKnownSourceBenefits(UnitState, TargetUnit,', action)
        for field in ('known_released_allies', 'known_linked_enemies'):
            self.assertIn('|' + field + '=', action)
        self.assertIn('GetMeleeThreatReach(Enemy)', preview)
        self.assertIn('|melee_threat_reach=', preview)
        self.assertLess(preview.index('IsVisibleHostile('), preview.index('GetMeleeThreatReach('))

    def test_grenade_preview_redacts_unknown_targets_before_reading_health(self):
        area = function_body(SOURCE, 'RecordAreaTargetPreviews')
        own = area.index('bOwnTarget = IsOwnUnitAt(TargetRef.ObjectID, CurrentHistory);')
        visible = area.index("VisibleUnits.Find('ObjectID', TargetRef.ObjectID) == INDEX_NONE")
        target = area.index('TargetUnit = XComGameState_Unit(')
        damage = area.index('Effect.GetDamagePreview(')
        self.assertLess(own, visible)
        self.assertLess(visible, target)
        self.assertLess(target, damage)
        self.assertIn('GetAllVisibleObjectsForPlayer(OwnerPlayerID, VisibleUnits)', area)
        self.assertIn('Count >= 64', area)
        self.assertNotIn('IterateByClassType', area)

    def test_area_choice_preserves_actual_selected_center_separately_from_scan_summary(self):
        prepare = function_body(SOURCE, 'PrepareChosenArea')
        self.assertIn('ActionFields(UnitState, "area",', prepare)
        self.assertIn('|aim_x=', prepare)
        self.assertIn('Impact = Locations[0];', prepare)
        self.assertIn('|impact_x=', prepare)
        self.assertIn('RecordAreaTargetPreviews(UnitState, Action, TargetIndex)', prepare)
        self.assertIn('|preview_targets=', prepare)
        reason = function_body(SOURCE, 'ActionFields')
        self.assertIn("Ability.GetMyTemplateName() == 'ThrowGrenade'", reason)
        self.assertIn("Ability.GetMyTemplateName() == 'LaunchGrenade'", reason)
        self.assertIn('Reason = "explosive_area_attack";', reason)

    def test_move_threat_traces_are_selected_only_visible_and_bounded(self):
        prepare = function_body(SOURCE, 'PrepareChosenMove')
        candidates = function_body(SOURCE, 'CandidateMove')
        preview = function_body(SOURCE, 'RecordMoveThreatPreviews')
        self.assertIn('RecordMoveThreatPreviews(UnitState, Path)', prepare)
        self.assertNotIn('RecordMoveThreatPreviews(', candidates)
        self.assertIn('GetVisibleThreats(UnitState, VisibleEnemies)', preview)
        self.assertIn('IsVisibleHostile(UnitState, Enemy, VisibleEnemies)', preview)
        self.assertIn('Count >= 64', preview)
        self.assertNotIn('IterateByClassType', preview)
        self.assertIn('GetCoverTypeForTarget(EnemyLocation, CurrentLocation, Angle)', preview)
        self.assertIn('GetCoverTypeForTarget(EnemyLocation, DestinationLocation, Angle)', preview)
        self.assertIn('CanSeeTileToTile(EnemyTile, DestinationTile, DestinationVisibility)', preview)
        self.assertNotIn('.TargetCover', preview)
        self.assertNotIn('_native_cover=', preview)
        self.assertIn('bDestinationLOS && DestinationVisibility.bVisibleFromDefault', preview)
        # Per-contact values must come from the planner, so a future report
        # can distinguish ranged cover changes from melee distance changes.
        self.assertIn('ThreatRiskAtTile(UnitState, Enemy, CurrentTile, MeleeReach, Weight)', preview)
        self.assertIn('ThreatRiskAtTile(UnitState, Enemy, DestinationTile, MeleeReach, Weight)', preview)
        for field in ('enemy_template', 'melee_only', 'current_distance',
                      'destination_distance', 'current_threat_risk', 'destination_threat_risk'):
            self.assertIn('|' + field + '=', preview)

    def test_unknown_outcome_is_not_a_loss_and_observation_survives_user_stop(self):
        finish = function_body(SOURCE, 'Finish')
        self.assertIn('Outcome = "unknown";', finish)
        self.assertIn('BattleData.VictoriousPlayer.ObjectID != 0', finish)
        controller = (CLASSES / 'APX_Controller.uc').read_text(encoding='utf-8-sig')
        tick = function_body(controller, 'Tick')
        self.assertLess(tick.index('MissionRecorder.Observe('), tick.index('if (!bEnabled)'))
        self.assertIn('MissionRecorder.Finish(', function_body(controller, 'Destroyed'))

    def test_native_end_waits_for_committed_winner_before_finalizing(self):
        finish = function_body(SOURCE, 'Finish')
        # A stale observer now closes without an end record. This contract is
        # about finalizing the live mission after its winner is committed.
        finish = finish[finish.index('if (`XCOMHISTORY != none)'):]
        pending = finish.index('Reason == "tactical_game_ended"')
        observe_finish = finish.index('Observe("finish")')
        self.assertIn('BattleData.VictoriousPlayer.ObjectID == 0', finish[pending:observe_finish])
        self.assertIn('Observe("ending")', finish[pending:observe_finish])
        self.assertIn('return;', finish[pending:observe_finish])
        self.assertGreater(finish.index('bFinished = true'), observe_finish)
        self.assertIn('LastEndHistory', finish[pending:observe_finish])

    def test_result_scope_preserves_friendly_vs_incoming_without_unredacting_sources(self):
        results = function_body(SOURCE, 'RecordResults')
        self.assertIn('SourceScope = "friendly"', results)
        self.assertIn('SourceScope = "visible_enemy"', results)
        self.assertIn('SourceScope = "unseen_other"', results)
        self.assertIn('|source_scope=', results)
        self.assertIn('SourceID = 0;', results)


@unittest.skipUnless(os.environ.get('APX_SDK_SOURCE_ROOT'), 'Set APX_SDK_SOURCE_ROOT to check native recorder declarations')
class RecorderSDKContracts(unittest.TestCase):
    def test_tile_visibility_contract_does_not_supply_native_target_cover(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))
        bind = (sdk / 'XComGame/Classes/X2Effect_GetOverHere.uc').read_text(encoding='utf-8-sig')
        self.assertIn('CanSeeTileToTile does not update TargetCover', bind)
        self.assertIn('OutVisibilityInfo.bVisibleFromDefault', bind)
        preview = function_body(SOURCE, 'RecordMoveThreatPreviews')
        self.assertNotIn('.TargetCover', preview)
        self.assertIn('GetCoverTypeForTarget(EnemyLocation, DestinationLocation, Angle)', preview)
        planner = (CLASSES / 'APX_MissionPlanner.uc').read_text(encoding='utf-8-sig')
        exposure = function_body(CHECKS.without_comments(planner), 'ExposureRisk')
        self.assertNotIn('Visibility.TargetCover', exposure)

    def test_recorder_history_visibility_time_and_outcome_declarations_exist(self):
        sdk = CHECKS.find_sdk_root(Path(os.environ['APX_SDK_SOURCE_ROOT']))
        files = {name: (sdk / 'XComGame/Classes' / (name + '.uc')).read_text(encoding='utf-8-sig')
                 for name in ('XComGameStateHistory', 'X2TacticalVisibilityHelpers',
                              'XComGameState_BattleData', 'XComGameState', 'XComGameStateContext')}
        self.assertRegex(files['XComGameStateHistory'], r'GetGameStateForObjectID\(int ObjectID,\s*optional EGameStateReturnType DesiredReturnType=eReturnType_Reference,\s*optional int HistoryIndex=-1\)')
        self.assertRegex(files['X2TacticalVisibilityHelpers'], r'GetAllVisibleEnemiesForPlayer\(int PlayerStateObjectID,\s*out array<StateObjectReference> VisibleUnits,\s*int HistoryIndex = -1')
        self.assertIn('eInterruptionStatus_Interrupt', files['XComGameState'])
        self.assertRegex(files['XComGameState_BattleData'], r'var\(\)\s+StateObjectReference\s+VictoriousPlayer;')
        core = (sdk / 'Core/Classes/Object.uc').read_text(encoding='utf-8-sig')
        self.assertRegex(core, r'GetSystemTime\(\s*out int Year,\s*out int Month,\s*out int DayOfWeek,\s*out int Day,\s*out int Hour,\s*out int Min,\s*out int Sec,\s*out int MSec\s*\)')


if __name__ == '__main__':
    unittest.main()
