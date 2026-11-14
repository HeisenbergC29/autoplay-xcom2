// Runtime-only diagnostic observer. Never changes state, rolls RNG or issues orders.
// Records the local squad, visible contacts and public mission/scoring facts.
class APX_MissionRecorder extends Object config(AutoplayXCom2)
    dependson(X2GameRuleset, XComGameState_Ability, X2TacticalGameRulesetDataStructures,
        X2GameRulesetVisibilityDataStructures, XComGameState,
        X2StrategyGameRulesetDataStructures, X2ChallengeModeDataStructures);

var config int MaxRecords;
var config int MaxHistoryFramesPerObserve;

struct RecordedUnit
{
    var int UnitID;
    var string Snapshot;
    var string Abilities;
    var string Knowledge;
};

var private array<RecordedUnit> Units;
var private array<int> PreviousVisibleIDs;
var private int OwnerPlayerID;
var private int Sequence;
var private int Decision;
var private int HistoryCursor;
var private string SessionID;
var private string LastPhase;
var private string PreparedChoiceFields;
var private bool bStarted;
var private bool bFinished;
var private bool bLimitReported;
var private bool bEndPending;
var private int LastEndHistory;
var private string RecordedMissionType;
var private string LastGameScore;
var private string LastHUDScore;
var private int RecordedLadderIndex;
var private int RecordedLadderRung;
var private int LastRelayScanTurn;
var private int LastPatrolObservationTurn;
var private XComGameStateHistory RecordedHistory;
var private int RecordedBattleID;
var private int RecordedStartStateIndex;
var private int RecordingStartHistory;
var private int LastObservedMissionHistory;
var private bool bRecordingEpochInvalid;
var private bool bHasLadderScore;
var private array<string> RecordedScoreKeys;
var private array<string> RecordedScoreRules;
var private array<string> CompletedObjectiveIDs;
var private array<string> FailedObjectiveIDs;
var private array<int> RescuedCivilianIDs;
var private APX_MissionScore NativeScoreProbe;

function string Safe(string Value)
{
    Value = Repl(Value, "|", "/");
    Value = Repl(Value, Chr(13), " ");
    Value = Repl(Value, Chr(10), " ");
    return Value;
}

function Emit(string EventName, string Fields)
{
    if (!bStarted || bFinished)
        return;
    if (Sequence >= Clamp(MaxRecords, 100, 100000))
    {
        if (!bLimitReported)
        {
            ++Sequence;
            `log("APXREC|v=1|session=" $ SessionID $ "|seq=" $ Sequence
                $ "|event=limit|decision=" $ Decision $ "|max_records=" $ MaxRecords, true, 'AutoplayXCom2');
            bLimitReported = true;
        }
        return;
    }
    ++Sequence;
    `log("APXREC|v=1|session=" $ SessionID $ "|seq=" $ Sequence
        $ "|event=" $ Safe(EventName) $ "|decision=" $ Decision $ Fields, true, 'AutoplayXCom2');
}

function Start(int PlayerID)
{
    local XComGameState_BattleData BattleData;
    local int Year, Month, DayOfWeek, Day, Hour, Minute, Second, Millisecond;
    local string Mission;

    if (bStarted || `XCOMHISTORY == none)
        return;
    OwnerPlayerID = PlayerID;
    GetSystemTime(Year, Month, DayOfWeek, Day, Hour, Minute, Second, Millisecond);
    SessionID = string(Year) $ "-" $ Month $ "-" $ Day $ "_" $ Hour
        $ "-" $ Minute $ "-" $ Second $ "-" $ Millisecond $ "_" $ PlayerID;
    RecordedHistory = `XCOMHISTORY;
    RecordedStartStateIndex = RecordedHistory.FindStartStateIndex();
    HistoryCursor = RecordedHistory.GetCurrentHistoryIndex();
    RecordingStartHistory = HistoryCursor;
    LastObservedMissionHistory = HistoryCursor;
    BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    Mission = "unknown";
    if (BattleData != none)
    {
        Mission = BattleData.MapData.ActiveMission.sType;
        RecordedBattleID = BattleData.ObjectID;
    }
    RecordedMissionType = Mission;
    LastRelayScanTurn = -1; // include turn zero on a late F8/start.
    LastPatrolObservationTurn = -1;
    bStarted = true;
    Emit("start", "|player=" $ PlayerID $ "|mission=" $ Safe(Mission)
        $ "|difficulty=" $ `TacticalDifficultySetting $ "|history=" $ HistoryCursor
        $ "|revision=mission-report-v36|full_intel_enabled=" $ class'APX_FullIntel'.default.EnableFullIntel
        $ "|formation_area_radius_tiles=" $ class'APX_MissionPlanner'.default.SquadAreaRiskRadiusTiles
        $ "|formation_area_weight=" $ class'APX_MissionPlanner'.default.SquadAreaRiskWeight
        $ "|concealment_risk_penalty=" $ class'APX_ConcealmentPlanner'.default.ConcealmentRiskPenalty
        $ "|concealment_los_limit=" $ class'APX_ConcealmentPlanner'.default.MaxNativeLOSChecksPerInspection);
    // F8 starts observation, not the mission. Even turn one may already have
    // processed damage, objectives or native starting allowances.
    Emit("scoring_coverage", "|complete=false|reason=recording_begins_at_f8"
        $ "|history=" $ HistoryCursor);
    RegisterScoreObservers();
    Observe("start");
}

// These callbacks only observe UI objective and rescue notifications. Native
// scoring remains the game's responsibility; never call its Add* scoring APIs.
function RegisterScoreObservers()
{
    local X2EventManager EventManager;
    local Object Listener;

    EventManager = `XEVENTMGR;
    if (EventManager == none)
        return;
    Listener = self;
    EventManager.RegisterForEvent(Listener, 'MissionObjectiveMarkedCompleted',
        OnObjectiveCompleted, ELD_OnStateSubmitted);
    EventManager.RegisterForEvent(Listener, 'MissionObjectiveMarkedFailed',
        OnObjectiveFailed, ELD_OnStateSubmitted);
    // This native failure handler interrupts later listeners. Capture read-only
    // at the immediate window with higher priority; never interrupt it ourselves.
    // Actual native delivery must still be confirmed in a game report.
    EventManager.RegisterForEvent(Listener, 'ChallengeObjectiveFailed',
        OnChallengeObjectiveFailed, ELD_Immediate, 1000);
    EventManager.RegisterForEvent(Listener, 'CivilianRescued',
        OnCivilianRescued, ELD_OnStateSubmitted);
}

function UnregisterScoreObservers()
{
    local X2EventManager EventManager;
    local Object Listener;

    if (NativeScoreProbe != none)
    {
        NativeScoreProbe.Cleanup();
        NativeScoreProbe = none;
    }
    EventManager = `XEVENTMGR;
    if (EventManager == none)
        return;
    Listener = self;
    EventManager.UnRegisterFromEvent(Listener, 'MissionObjectiveMarkedCompleted');
    EventManager.UnRegisterFromEvent(Listener, 'MissionObjectiveMarkedFailed');
    EventManager.UnRegisterFromEvent(Listener, 'ChallengeObjectiveFailed');
    EventManager.UnRegisterFromEvent(Listener, 'CivilianRescued');
}

function int TurnAtHistory(int HistoryIndex)
{
    local XComGameState_Player PlayerState;

    PlayerState = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(
        OwnerPlayerID, eReturnType_Reference, HistoryIndex));
    return PlayerState != none ? PlayerState.PlayerTurnCount : -1;
}

static function bool RecordingEpochMatches(bool bSameHistory, int StartStateIndex,
    int CurrentStartStateIndex, int MinimumHistory, int CurrentHistory,
    int BattleID, int CurrentBattleID)
{
    return bSameHistory && StartStateIndex == CurrentStartStateIndex
        && CurrentHistory >= MinimumHistory && BattleID > 0
        && BattleID == CurrentBattleID;
}

function bool IsRecordingMission()
{
    local XComGameState_BattleData BattleData;
    local int CurrentHistory;

    if (!bStarted || bFinished || bLimitReported || bRecordingEpochInvalid
        || RecordedHistory == none || `XCOMHISTORY == none)
        return false;
    BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    if (BattleData == none)
        return false;
    CurrentHistory = `XCOMHISTORY.GetCurrentHistoryIndex();
    if (!RecordingEpochMatches(RecordedHistory == `XCOMHISTORY,
            RecordedStartStateIndex, `XCOMHISTORY.FindStartStateIndex(),
            Max(RecordingStartHistory, LastObservedMissionHistory), CurrentHistory,
            RecordedBattleID, BattleData.ObjectID)
        || BattleData.MapData.ActiveMission.sType != RecordedMissionType)
    {
        // This observer cannot silently become a new recording after reload,
        // another battle or a rewind. No live game state is modified.
        bRecordingEpochInvalid = true;
        return false;
    }
    LastObservedMissionHistory = CurrentHistory;
    return true;
}

function EventListenerReturn OnObjectiveCompleted(Object EventData, Object EventSource,
    XComGameState GameState, Name Event, Object CallbackData)
{
    local SeqAct_DisplayMissionObjective DisplayAction;
    local XComGameState_ObjectivesList ObjectiveList;
    local ObjectiveDisplayInfo Info;
    local string ObjectiveID, ObjectiveName;
    local int HistoryIndex;
    local bool bFound;

    if (!IsRecordingMission() || GameState == none)
        return ELR_NoInterrupt;
    DisplayAction = SeqAct_DisplayMissionObjective(EventSource);
    ObjectiveList = XComGameState_ObjectivesList(EventData);
    if (DisplayAction == none || ObjectiveList == none)
        return ELR_NoInterrupt;
    foreach ObjectiveList.ObjectiveDisplayInfos(Info)
    {
        if (Info.MissionType == RecordedMissionType && Info.TextPoolIndex == DisplayAction.TextPoolIndex
            && Info.LineIndex == DisplayAction.LineIndex && Info.GroupID == DisplayAction.GroupID
            && Info.ShowCompleted && Info.ShowCheckBox && !Info.HideInTactical)
        {
            ObjectiveName = Info.DisplayLabel;
            bFound = true;
            break;
        }
    }
    // A matching visible completed checkbox is required; do not reveal hidden
    // objectives or assign completion to unrelated strategy/UI notifications.
    if (!bFound)
        return ELR_NoInterrupt;
    ObjectiveID = RecordedMissionType $ ":" $ DisplayAction.TextPoolIndex $ ":"
        $ DisplayAction.LineIndex $ ":" $ DisplayAction.GroupID;
    if (CompletedObjectiveIDs.Find(ObjectiveID) != INDEX_NONE)
        return ELR_NoInterrupt;
    CompletedObjectiveIDs.AddItem(ObjectiveID);
    RecordObjectiveScoreRule(DisplayAction, ObjectiveID);
    HistoryIndex = GameState.HistoryIndex;
    Emit("objective_completed", "|source=mission_ui_event|objective_id=" $ Safe(ObjectiveID)
        $ "|objective_name=" $ Safe(ObjectiveName) $ "|turn=" $ TurnAtHistory(HistoryIndex)
        $ "|completion_turn=" $ TurnAtHistory(HistoryIndex) $ "|history=" $ HistoryIndex);
    return ELR_NoInterrupt;
}

// A failed displayed checkbox is a UI fact, not proof that a required mission
// objective failed. The payload has no required/optional classification.
// Preserve that uncertainty without changing Kismet or native scoring.
function EventListenerReturn OnObjectiveFailed(Object EventData, Object EventSource,
    XComGameState GameState, Name Event, Object CallbackData)
{
    local SeqAct_DisplayMissionObjective DisplayAction;
    local XComGameState_ObjectivesList ObjectiveList;
    local ObjectiveDisplayInfo Info;
    local string ObjectiveID, ObjectiveName;
    local int HistoryIndex;
    local bool bFound;

    if (!IsRecordingMission() || GameState == none)
        return ELR_NoInterrupt;
    DisplayAction = SeqAct_DisplayMissionObjective(EventSource);
    ObjectiveList = XComGameState_ObjectivesList(EventData);
    if (DisplayAction == none || ObjectiveList == none)
        return ELR_NoInterrupt;
    foreach ObjectiveList.ObjectiveDisplayInfos(Info)
    {
        if (Info.MissionType == RecordedMissionType
            && Info.TextPoolIndex == DisplayAction.TextPoolIndex
            && Info.LineIndex == DisplayAction.LineIndex
            && Info.GroupID == DisplayAction.GroupID
            && Info.ShowFailed && Info.ShowCheckBox && !Info.HideInTactical)
        {
            ObjectiveName = Info.DisplayLabel;
            bFound = true;
            break;
        }
    }
    if (!bFound)
        return ELR_NoInterrupt;
    ObjectiveID = RecordedMissionType $ ":" $ DisplayAction.TextPoolIndex $ ":"
        $ DisplayAction.LineIndex $ ":" $ DisplayAction.GroupID;
    if (FailedObjectiveIDs.Find(ObjectiveID) != INDEX_NONE)
        return ELR_NoInterrupt;
    FailedObjectiveIDs.AddItem(ObjectiveID);
    HistoryIndex = GameState.HistoryIndex;
    Emit("objective_failed", "|source=mission_ui_event|critical=false|criticality=unknown|objective_id=" $ Safe(ObjectiveID)
        $ "|objective_name=" $ Safe(ObjectiveName)
        $ "|turn=" $ TurnAtHistory(HistoryIndex) $ "|history=" $ HistoryIndex);
    return ELR_NoInterrupt;
}

// Challenge failure may have no public display checkbox. Native
// X2TacticalGameRuleset.OnChallengeObjectiveFailed handles the true fail;
// we only capture that same event, never call FailBattle ourselves.
function EventListenerReturn OnChallengeObjectiveFailed(Object EventData,
    Object EventSource, XComGameState GameState, Name Event, Object CallbackData)
{
    local int HistoryIndex;
    local string ObjectiveID;

    if (!IsRecordingMission())
        return ELR_NoInterrupt;
    ObjectiveID = RecordedMissionType $ ":challenge_objective";
    if (FailedObjectiveIDs.Find(ObjectiveID) != INDEX_NONE)
        return ELR_NoInterrupt;
    FailedObjectiveIDs.AddItem(ObjectiveID);
    HistoryIndex = `XCOMHISTORY.GetCurrentHistoryIndex();
    Emit("objective_failed", "|source=challenge_native_event|critical=true"
        $ "|objective_id=" $ Safe(ObjectiveID)
        $ "|turn=" $ TurnAtHistory(HistoryIndex)
        $ "|history=" $ HistoryIndex);
    return ELR_NoInterrupt;
}

function EventListenerReturn OnCivilianRescued(Object EventData, Object EventSource,
    XComGameState GameState, Name Event, Object CallbackData)
{
    local XComGameState_Unit Rescuer, Civilian;
    local array<StateObjectReference> VisibleObjects;
    local int CivilianID;

    if (!IsRecordingMission() || GameState == none)
        return ELR_NoInterrupt;
    // Stock TriggerEvent sends the rescuer as data and the rescued civilian
    // as source. Only the recording player's rescues belong in this ledger.
    Rescuer = XComGameState_Unit(EventData);
    Civilian = XComGameState_Unit(EventSource);
    if (Rescuer == none || Civilian == none || Rescuer.GetAssociatedPlayerID() != OwnerPlayerID
        || RescuedCivilianIDs.Find(Civilian.ObjectID) != INDEX_NONE)
        return ELR_NoInterrupt;
    RescuedCivilianIDs.AddItem(Civilian.ObjectID);
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleObjectsForPlayer(
        OwnerPlayerID, VisibleObjects, , GameState.HistoryIndex);
    if (Civilian.GetAssociatedPlayerID() == OwnerPlayerID
        || VisibleObjects.Find('ObjectID', Civilian.ObjectID) != INDEX_NONE)
        CivilianID = Civilian.ObjectID;
    Emit("civilian_rescued", "|source=mission_event|civilian_id=" $ CivilianID
        $ "|rescuer=" $ Rescuer.ObjectID $ "|turn=" $ TurnAtHistory(GameState.HistoryIndex)
        $ "|history=" $ GameState.HistoryIndex);
    return ELR_NoInterrupt;
}

function RecordGameScore(string Phase)
{
    local XComGameState_LadderProgress Ladder;
    local XComGameState_BattleData BattleData;
    local string Fields, ScorePhase;
    local int MissionPoints;
    local bool bPointsKnown, bMissionFinal;

    if (`XCOMHISTORY == none || !IsRecordingMission())
        return;
    Ladder = XComGameState_LadderProgress(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_LadderProgress', true));
    if (Ladder == none)
        return;
    if (bHasLadderScore && (Ladder.LadderIndex != RecordedLadderIndex
        || Ladder.LadderRung != RecordedLadderRung))
        return;
    bHasLadderScore = true;
    RecordedLadderIndex = Ladder.LadderIndex;
    RecordedLadderRung = Ladder.LadderRung;
    RecordBaseScoreRules();
    Fields = "|source=legacy_runtime|ladder_index=" $ Ladder.LadderIndex
        $ "|ladder_rung=" $ Ladder.LadderRung $ "|cumulative_score=" $ Ladder.CumulativeScore;
    if (NativeScoreProbe == none)
        NativeScoreProbe = new(self) class'APX_MissionScore';
    bPointsKnown = NativeScoreProbe.ReadNativeMissionPoints(MissionPoints);
    BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    // An observed terminal snapshot, after our history cursor has caught up.
    // This never promises awards that have not yet been committed by the game.
    bMissionFinal = Phase == "finish" && BattleData != none
        && BattleData.VictoriousPlayer.ObjectID != 0 && !bLimitReported
        && HistoryCursor == `XCOMHISTORY.GetCurrentHistoryIndex();
    Fields $= "|mission_points_known=" $ bPointsKnown $ "|mission_final=" $ bMissionFinal;
    if (bPointsKnown)
        Fields $= "|mission_points=" $ MissionPoints;
    if (Fields == LastGameScore && Phase != "start" && Phase != "finish")
        return;
    ScorePhase = "observe";
    if (Phase == "start" || Phase == "finish")
        ScorePhase = Phase;
    Emit("game_score", Fields $ "|phase=" $ ScorePhase
        $ "|history=" $ `XCOMHISTORY.GetCurrentHistoryIndex());
    LastGameScore = Fields;
}

// Native Get* APIs expose installed configuration without granting any points.
// A stale recorder must never read the next ladder rung's configuration.
function XComChallengeModeManager RuntimeScoreManager()
{
    local XComGameState_LadderProgress Ladder;
    local XComChallengeModeManager Manager;

    if (!bHasLadderScore || !IsRecordingMission())
        return none;
    Manager = `CHALLENGEMODE_MGR;
    if (Manager == none)
        return none;
    Ladder = XComGameState_LadderProgress(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_LadderProgress', true));
    if (Ladder == none || Ladder.LadderIndex != RecordedLadderIndex
        || Ladder.LadderRung != RecordedLadderRung)
        return none;
    return Manager;
}

function EmitScoreRule(string Fields)
{
    // Full configuration is the key: revising a rule must remain observable,
    // while repeated observations in later history frames need no duplicate.
    if (RecordedScoreRules.Find(Fields) != INDEX_NONE)
        return;
    RecordedScoreRules.AddItem(Fields);
    Emit("score_rule", "|source=legacy_runtime" $ Fields
        $ "|history=" $ `XCOMHISTORY.GetCurrentHistoryIndex());
}

function RecordBaseScoreRules()
{
    local XComChallengeModeManager Manager;
    local ChallengeSoldierScoring Soldier;
    local ChallengeTimeScoring TimeRule;

    Manager = RuntimeScoreManager();
    if (Manager == none)
        return;
    Manager.GetSoldierScoring(Soldier);
    EmitScoreRule("|kind=soldier|uninjured_bonus=" $ Soldier.UninjuredBonus
        $ "|survival_bonus=" $ Soldier.WoundedBonus $ "|rescued_bonus=" $ Soldier.RescuedCivilianBonus);
    Manager.GetTimeScoring(TimeRule);
    EmitScoreRule("|kind=time|points_per_interval=" $ TimeRule.PointsPerInterval
        $ "|interval_seconds=" $ TimeRule.IntervalInSeconds);
}

function RecordVisibleEnemyScoreRule(XComGameState_Unit UnitState)
{
    local XComChallengeModeManager Manager;
    local ChallengeEnemyScoring Enemy;

    if (UnitState == none || UnitState.GetMyTemplate() == none)
        return;
    Manager = RuntimeScoreManager();
    if (Manager == none)
        return;
    Manager.GetEnemyScoring(Enemy, string(UnitState.GetMyTemplateName()));
    EmitScoreRule("|kind=enemy|template=" $ UnitState.GetMyTemplateName()
        $ "|starting_points=" $ Enemy.StartingPoints $ "|min_points=" $ Enemy.MinPoints
        $ "|decrease_per_turn=" $ Enemy.DecreasePerTurn $ "|turn_offset=" $ Enemy.TurnOffset
        $ "|spawned_points=" $ Enemy.SpawnedPoints $ "|reinforcement_points=" $ Enemy.ReinforcementPoints
        $ "|disabled_points=" $ Enemy.DisabledPoints $ "|min_disabled_points=" $ Enemy.MinDisabledPoints);
}

function RecordObjectiveScoreRule(SeqAct_DisplayMissionObjective DisplayAction, string ObjectiveID)
{
    local XComChallengeModeManager Manager;
    local ChallengeObjectiveScoring Objective;

    if (DisplayAction == none)
        return;
    Manager = RuntimeScoreManager();
    if (Manager == none)
        return;
    Manager.GetObjectiveScoring(Objective, RecordedMissionType, DisplayAction.TextPoolIndex,
        DisplayAction.GroupID, DisplayAction.LineIndex);
    EmitScoreRule("|kind=objective|mission=" $ Safe(RecordedMissionType)
        $ "|objective_id=" $ Safe(ObjectiveID)
        $ "|text_pool_index=" $ DisplayAction.TextPoolIndex
        $ "|group_id=" $ DisplayAction.GroupID $ "|line_index=" $ DisplayAction.LineIndex
        $ "|starting_points=" $ Objective.StartingPoints $ "|min_points=" $ Objective.MinPoints
        $ "|decrease_per_turn=" $ Objective.DecreasePerTurn $ "|turn_offset=" $ Objective.TurnOffset);
}

function RecordScoreDeltas(XComGameState HistoryState)
{
    local XComGameState_ChallengeScore ScoreState;
    local string ScoreKey;

    foreach HistoryState.IterateByClassType(class'XComGameState_ChallengeScore', ScoreState)
    {
        // Native award helpers may revise an existing object. Keep each history
        // observation without treating its fields as a summable award ledger.
        ScoreKey = HistoryState.HistoryIndex $ ":" $ ScoreState.ObjectID;
        if (RecordedScoreKeys.Find(ScoreKey) != INDEX_NONE)
            continue;
        RecordedScoreKeys.AddItem(ScoreKey);
        Emit("score_delta", "|source=game_runtime|score_id=" $ ScoreState.ObjectID
            $ "|scoring_type=" $ string(ScoreState.ScoringType)
            $ "|added_points=" $ ScoreState.AddedPoints $ "|ladder_bonus=" $ ScoreState.LadderBonus
            $ "|history=" $ HistoryState.HistoryIndex
            $ "|turn=" $ TurnAtHistory(HistoryState.HistoryIndex));
    }
}

// Preserve the exact displayed value, including the comparison marker and
// missing-value glyph. A fresh recorder observes its first value after F8.
function RecordHUDScore(string DisplayText)
{
    local string Fields;

    if (!bStarted || bFinished || DisplayText == LastHUDScore)
        return;
    if (!IsRecordingMission())
        return;
    LastHUDScore = DisplayText;
    Fields = "|display=" $ Safe(DisplayText);
    if (Left(DisplayText, 1) == "~")
        Fields $= "|comparison_profile=" $ class'APX_LegacyObservedV3'.static.GetProfileID()
            $ "|comparison_status=partial|rate_source=installed_ladder_config"
            $ "|native_parity_proven=false|event_coverage_proven=false";
    Emit("hud_score", Fields);
}

function Marker(string Kind, string Details)
{
    Emit("marker", "|kind=" $ Safe(Kind) $ "|details=" $ Safe(Details));
}

function BeginDecision()
{
    PreparedChoiceFields = "";
    ++Decision;
    Emit("decision", "");
    Observe("decision");
}

function int UnitIndex(int UnitID)
{
    local int Index;
    local RecordedUnit Entry;
    Index = Units.Find('UnitID', UnitID);
    if (Index != INDEX_NONE)
        return Index;
    Entry.UnitID = UnitID;
    Units.AddItem(Entry);
    return Units.Length - 1;
}

function RecordUnit(XComGameState_Unit UnitState, bool bFriendly, bool bForce)
{
    local XComGameState_Item Weapon;
    local UnitValue SpawnedValue, KilledValue;
    local int Index, ActionPoints, Ammo;
    local string Fields, Scope;
    local bool bScoreEligible, bLadderKilled;

    if (UnitState == none || UnitState.GetMyTemplate() == none
        || UnitState.GetMyTemplate().bIsCosmetic)
        return;
    ActionPoints = -1;
    Ammo = -1;
    Scope = "visible_enemy";
    if (bFriendly)
    {
        Scope = "friendly";
        ActionPoints = UnitState.NumActionPoints();
        Weapon = UnitState.GetItemInSlot(eInvSlot_PrimaryWeapon);
        if (Weapon != none)
            Ammo = Weapon.Ammo;
    }
    Fields = "|id=" $ UnitState.ObjectID $ "|scope=" $ Scope
        $ "|template=" $ UnitState.GetMyTemplateName()
        $ "|x=" $ UnitState.TileLocation.X $ "|y=" $ UnitState.TileLocation.Y
        $ "|z=" $ UnitState.TileLocation.Z $ "|hp=" $ UnitState.GetCurrentStat(eStat_HP)
        $ "|max_hp=" $ UnitState.GetMaxStat(eStat_HP)
        $ "|shield=" $ UnitState.GetCurrentStat(eStat_ShieldHP)
        $ "|ap=" $ ActionPoints $ "|ammo=" $ Ammo
        $ "|alive=" $ UnitState.IsAlive() $ "|incapacitated=" $ UnitState.IsIncapacitated()
        $ "|removed=" $ UnitState.bRemovedFromPlay;
    if (bFriendly)
    {
        // Mirror the stock ladder's soldier eligibility checks on owned units
        // only. Enemy metrics remain limited to their ordinary visible state.
        bScoreEligible = UnitState.GetPreviousTeam() == eTeam_XCom && !UnitState.bMissionProvided
            && !UnitState.GetUnitValue('NewSpawnedUnit', SpawnedValue);
        bLadderKilled = UnitState.GetUnitValue('LadderKilledScored', KilledValue);
        Fields $= "|concealed=" $ UnitState.IsConcealed()
            $ "|bleeding_out=" $ UnitState.IsBleedingOut()
            $ "|bleeding_turns_remaining=" $ UnitState.GetBleedingOutTurnsRemaining()
            $ "|panicked=" $ UnitState.IsPanicked()
            $ "|mind_controlled=" $ UnitState.IsMindControlled()
            $ "|unconscious=" $ UnitState.IsUnconscious()
            $ "|poisoned=" $ UnitState.IsPoisoned()
            $ "|poison_cloud=" $ class'APX_HazardKnowledge'.static.IsKnownPoisonCloudAtTile(
                UnitState, UnitState.TileLocation)
            $ "|poison_cloud_harmful=" $ class'APX_HazardKnowledge'.static.NeedsPoisonEscape(UnitState)
            $ "|score_eligible=" $ bScoreEligible $ "|highest_hp=" $ UnitState.HighestHP
            $ "|lowest_hp=" $ UnitState.LowestHP $ "|ladder_killed_scored=" $ bLadderKilled;
    }
    Index = UnitIndex(UnitState.ObjectID);
    if (bForce || Units[Index].Snapshot != Fields)
    {
        Emit("unit", Fields);
        Units[Index].Snapshot = Fields;
    }
    if (bFriendly && UnitState.IsAbleToAct())
        RecordAvailability(UnitState, Index);
}

// Called only from the current native visible-enemy list. These are installed
// template parameters and public unit stats, not AP, cooldown or AI readiness.
function RecordEnemyKnowledge(XComGameState_Unit Enemy)
{
    local XComGameState_Item Weapon;
    local X2CharacterTemplate Character;
    local string Fields, WeaponName, Immunities;
    local name ImmuneType;
    local int Index, Flags;
    local float Weight, TargetWeight;

    if (Enemy == none || Enemy.GetMyTemplate() == none)
        return;
    Character = Enemy.GetMyTemplate();
    Weapon = Enemy.GetPrimaryWeapon();
    WeaponName = "unknown";
    if (Weapon != none)
        WeaponName = string(Weapon.GetMyTemplateName());
    foreach Character.ImmuneTypes(ImmuneType)
    {
        if (Immunities != "")
            Immunities $= ",";
        Immunities $= string(ImmuneType);
    }
    Weight = class'APX_EnemyKnowledge'.static.ThreatWeight(Enemy);
    Flags = class'APX_EnemyKnowledge'.static.CapabilityFlags(Enemy);
    TargetWeight = class'APX_EnemyKnowledge'.static.TargetThreatValue(Weight,
        (Flags & class'APX_EnemyKnowledge'.const.Capability_Control) != 0,
        (Flags & class'APX_EnemyKnowledge'.const.Capability_Area) != 0,
        (Flags & class'APX_EnemyKnowledge'.const.Capability_Support) != 0,
        Enemy.GetTeam() == eTeam_TheLost);
    Fields = "|source=visible_template|enemy=" $ Enemy.ObjectID
        $ "|template=" $ Enemy.GetMyTemplateName() $ "|primary_weapon=" $ Safe(WeaponName)
        $ "|weapon_mean_damage=" $ class'APX_EnemyKnowledge'.static.PrimaryWeaponMeanDamage(Enemy)
        $ "|aim=" $ Enemy.GetCurrentStat(eStat_Offense)
        $ "|mobility=" $ Enemy.GetCurrentStat(eStat_Mobility)
        $ "|armor=" $ Enemy.GetArmorMitigationForUnitFlag()
        $ "|base_hp=" $ Character.GetCharacterBaseStat(eStat_HP)
        $ "|base_aim=" $ Character.GetCharacterBaseStat(eStat_Offense)
        $ "|base_defense=" $ Character.GetCharacterBaseStat(eStat_Defense)
        $ "|base_mobility=" $ Character.GetCharacterBaseStat(eStat_Mobility)
        $ "|base_will=" $ Character.GetCharacterBaseStat(eStat_Will)
        $ "|base_dodge=" $ Character.GetCharacterBaseStat(eStat_Dodge)
        $ "|base_armor=" $ Character.GetCharacterBaseStat(eStat_ArmorMitigation)
        $ "|base_psi=" $ Character.GetCharacterBaseStat(eStat_PsiOffense)
        $ "|base_hack_defense=" $ Character.GetCharacterBaseStat(eStat_HackDefense)
        $ "|base_detection=" $ Character.GetCharacterBaseStat(eStat_DetectionRadius)
        $ "|base_crit=" $ Character.GetCharacterBaseStat(eStat_CritChance)
        $ "|can_take_cover=" $ Character.bCanTakeCover
        $ "|robotic=" $ Character.bIsRobotic
        $ "|tech_vulnerable=" $ Character.bWeakAgainstTechLikeRobot
        $ "|immune_types=" $ Safe(Immunities)
        $ "|threat_weight=" $ Weight $ "|target_threat=" $ TargetWeight
        $ "|capabilities=" $ Flags
        $ "|melee_counter_possible=" $ class'APX_EnemyKnowledge'.static.HasMeleeCounter(Enemy);
    Index = UnitIndex(Enemy.ObjectID);
    if (Units[Index].Knowledge != Fields)
    {
        Emit("enemy_knowledge", Fields);
        Units[Index].Knowledge = Fields;
    }
}

function RecordAvailability(XComGameState_Unit UnitState, int Index)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Action;
    local XComGameState_Ability Ability;
    local string Fingerprint, Fields;

    if (`TACTICALRULES == none
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), Cache))
        return;
    foreach Cache.AvailableActions(Action)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
            Action.AbilityObjectRef.ObjectID));
        if (Ability != none)
            Fingerprint $= string(Ability.GetMyTemplateName()) $ ":" $ Action.AvailableCode
                $ ":" $ Action.bInputTriggered $ ":" $ Action.bFreeAim
                $ ":" $ Action.AvailableTargets.Length $ ";";
    }
    if (Units[Index].Abilities == Fingerprint)
        return;
    Units[Index].Abilities = Fingerprint;
    foreach Cache.AvailableActions(Action)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
            Action.AbilityObjectRef.ObjectID));
        if (Ability == none)
            continue;
        Fields = "|unit=" $ UnitState.ObjectID $ "|ability=" $ Ability.GetMyTemplateName()
            $ "|code=" $ Action.AvailableCode $ "|input=" $ Action.bInputTriggered
            $ "|freeaim=" $ Action.bFreeAim $ "|targets=" $ Action.AvailableTargets.Length
            $ "|handler=" $ AbilityHandler(UnitState, Ability.GetMyTemplateName());
        Emit("ability", Fields);
    }
}

// This describes the planner responsible for evaluating an action, not a
// promise that every target or item variant is safe and will be selected.
function string AbilityHandler(XComGameState_Unit UnitState, name AbilityName)
{
    if (class'APX_CombatPlanner'.static.GetActionReason(UnitState, AbilityName)
        != "outside_combat_allowlist")
        return "combat";
    if (AbilityName == 'StandardMove')
        return "movement";
    if (AbilityName == 'Loot')
        return "loot";
    if (AbilityName == 'ThrowGrenade' || AbilityName == 'LaunchGrenade')
        return "grenade";
    if (AbilityName == 'Evac' || AbilityName == 'PlaceEvacZone')
        return "evacuation";
    if (class'APX_MissionPlanner'.static.IsObjectiveAbility(AbilityName)
        || AbilityName == 'Interact' || AbilityName == 'Interact_OpenChest'
        || AbilityName == 'Hack' || AbilityName == 'Hack_Chest'
        || AbilityName == 'Knockout' || AbilityName == 'CarryUnit')
        return "mission";
    return "unhandled";
}

// Diagnostic only: no relay ID is guessed and no target is submitted.
// Sample once each XCOM turn in the timed transmitter mission. BerserkerMP
// may have no valid ranged weapon: report actual native target availability.
function RecordSabotageRelayCandidates(int Turn)
{
    local XComGameState_Unit Soldier;
    local XComGameState_Destructible TargetObject;
    local XComGameState_Ability Ability;
    local GameRulesCache_Unit UnitCache;
    local AvailableAction Action;
    local AvailableTarget Target;
    local XComDestructibleActor Visualizer;
    local int UnitsScanned, UnitsChecked, ActionsChecked, TargetsChecked, ObjectsChecked, Shown;
    local string Fields;

    if (!IsRecordingMission() || RecordedMissionType != "SabotageTransmitter"
        || `TACTICALRULES == none
        || `XCOMHISTORY == none || `XWORLD == none)
        return;
    Emit("relay_scan", "|phase=begin|turn=" $ Turn
        $ "|scope=diagnostics_only|classification=unverified");
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Destructible', TargetObject)
    {
        if (++ObjectsChecked > 256 || Shown >= 20)
            break;
        if (TargetObject == none || TargetObject.bRemoved || TargetObject.Health <= 0
            || !TargetObject.IsTargetable(eTeam_XCom)
            || `XWORLD.IsTileOutOfRange(TargetObject.TileLocation))
            continue;
        Visualizer = XComDestructibleActor(`XCOMHISTORY.GetVisualizer(TargetObject.ObjectID));
        if (Visualizer != none && (Visualizer.bDeleteMe
            || Visualizer.ObjectID != TargetObject.ObjectID))
            Visualizer = none;
        Fields = "|turn=" $ Turn $ "|id=" $ TargetObject.ObjectID
            $ "|hp=" $ TargetObject.Health
            $ "|x=" $ TargetObject.TileLocation.X
            $ "|y=" $ TargetObject.TileLocation.Y
            $ "|z=" $ TargetObject.TileLocation.Z
            $ "|main_objective=" $ class'Helpers'.static.IsObjectiveTarget(TargetObject.ObjectID)
            $ "|actor=" $ Safe(string(Visualizer))
            $ "|type=unverified_destructible";
        if (Visualizer != none)
        {
            Fields $= "|actor_class=" $ Safe(string(Visualizer.Class))
                $ "|archetype=" $ Safe(PathName(Visualizer.ObjectArchetype));
            // Once-per-turn evidence for the melee relay guard, rather than
            // a per-candidate log flood. This is not a secondary-blast solver.
            if (class'APX_CombatPlanner'.static.IsTransmitterRelay(TargetObject))
                Fields $= "|damaged_events=" $ Visualizer.DamagedEvents.Length
                    $ "|destroyed_events=" $ Visualizer.DestroyedEvents.Length
                    $ "|annihilated_events=" $ Visualizer.AnnihilatedEvents.Length
                    $ "|radial_event_lists_clear="
                    $ class'APX_CombatPlanner'.static.RelayHasNoRadialEvent(TargetObject);
        }
        else
            Fields $= "|actor_class=unknown|archetype=unknown";
        Emit("relay_object_candidate", Fields);
        ++Shown;
    }
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Soldier)
    {
        if (++UnitsScanned > 256 || UnitsChecked >= 8
            || ActionsChecked >= 128 || TargetsChecked >= 192)
            break;
        if (Soldier == none || Soldier.bRemoved || Soldier.bRemovedFromPlay
            || !Soldier.IsAlive() || !Soldier.IsAbleToAct()
            || Soldier.GetTeam() != eTeam_XCom
            || Soldier.GetAssociatedPlayerID() != OwnerPlayerID)
            continue;
        ++UnitsChecked;
        if (!`TACTICALRULES.GetGameRulesCache_Unit(Soldier.GetReference(), UnitCache))
            continue;
        foreach UnitCache.AvailableActions(Action)
        {
            if (++ActionsChecked > 128 || TargetsChecked >= 192)
                break;
            Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
                Action.AbilityObjectRef.ObjectID));
            if (Ability == none || Ability.OwnerStateObject.ObjectID != Soldier.ObjectID
                || class'APX_CombatPlanner'.default.AttackAbilities.Find(
                    Ability.GetMyTemplateName()) == INDEX_NONE)
                continue;
            foreach Action.AvailableTargets(Target)
            {
                if (++TargetsChecked > 192)
                    break;
                TargetObject = XComGameState_Destructible(
                    `XCOMHISTORY.GetGameStateForObjectID(Target.PrimaryTarget.ObjectID));
                if (TargetObject == none || TargetObject.bRemoved || TargetObject.Health <= 0)
                    continue;
                Emit("relay_action_target", "|turn=" $ Turn
                    $ "|unit=" $ Soldier.ObjectID
                    $ "|ability=" $ Ability.GetMyTemplateName()
                    $ "|code=" $ Action.AvailableCode
                    $ "|native_available=" $ (Action.AvailableCode == 'AA_Success')
                    $ "|target=" $ TargetObject.ObjectID
                    $ "|hp=" $ TargetObject.Health
                    $ "|main_objective=" $ class'Helpers'.static.IsObjectiveTarget(TargetObject.ObjectID)
                    $ "|hostile=" $ Soldier.TargetIsEnemy(TargetObject.ObjectID));
            }
        }
    }
    Emit("relay_scan", "|phase=end|turn=" $ Turn
        $ "|objects_scanned=" $ Min(ObjectsChecked, 256)
        $ "|objects_reported=" $ Shown
        $ "|units_scanned=" $ Min(UnitsScanned, 256)
        $ "|units=" $ UnitsChecked
        $ "|actions_checked=" $ Min(ActionsChecked, 128)
        $ "|targets_checked=" $ Min(TargetsChecked, 192));
}

// Read only the authorized stored target; future tactical use is unknown.
function RecordCurrentPatrolWaypoints(int Turn)
{
    local XComGameState_AIGroup Group;
    local XComGameState_Player LocalPlayer;
    local TTile TargetTile;
    local vector Midpoint;
    local int Seen, Waypoints, HostileMembers, MemberBudget, RemainingMemberChecks;

    if (!IsRecordingMission() || !class'APX_FullIntel'.default.EnableFullIntel
        || `XCOMHISTORY == none || `XWORLD == none || `TACTICALRULES == none
        || OwnerPlayerID != `TACTICALRULES.GetLocalClientPlayerObjectID())
        return;
    LocalPlayer = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(OwnerPlayerID));
    if (LocalPlayer == none || LocalPlayer.GetTeam() != eTeam_XCom)
        return;
    MemberBudget = Clamp(class'APX_PatrolKnowledge'.default.MaxMemberReferencesPerObservation, 1, 256);
    RemainingMemberChecks = MemberBudget;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_AIGroup', Group)
    {
        if (Seen >= Clamp(class'APX_PatrolKnowledge'.default.MaxGroupsPerObservation, 1, 48)
            || RemainingMemberChecks <= 0)
            break;
        ++Seen;
        if (!class'APX_PatrolKnowledge'.static.GetCurrentPatrolWaypoint(
            Group, OwnerPlayerID, TargetTile, Midpoint, HostileMembers,
            RemainingMemberChecks))
            continue;
        ++Waypoints;
        Emit("patrol_group", "|turn=" $ Turn
            $ "|group=" $ Group.ObjectID
            $ "|members=" $ HostileMembers
            $ "|target_x=" $ TargetTile.X
            $ "|target_y=" $ TargetTile.Y
            $ "|target_z=" $ TargetTile.Z
            $ "|mid_x=" $ Midpoint.X
            $ "|mid_y=" $ Midpoint.Y
            $ "|mid_z=" $ Midpoint.Z
            $ "|is_stored_current_target=true|target_usage=unknown"
            $ "|next_waypoint_unknown=true");
    }
    Emit("patrol_scan", "|turn=" $ Turn
        $ "|groups_checked=" $ Seen
        $ "|current_waypoints=" $ Waypoints
        $ "|member_refs_checked=" $ (MemberBudget - RemainingMemberChecks)
        $ "|member_budget_exhausted=" $ string(RemainingMemberChecks <= 0)
        $ "|future_route=unknown");
}

function Observe(string Phase)
{
    local XComGameState_Unit UnitState;
    local XComGameState_Player PlayerState;
    local array<StateObjectReference> VisibleEnemies;
    local array<int> VisibleIDs;
    local StateObjectReference EnemyRef;
    local string PhaseState;
    local int Index;

    if (!IsRecordingMission())
        return;
    RecordGameScore(Phase);
    PlayerState = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(OwnerPlayerID));
    PhaseState = "|phase=" $ Safe(Phase);
    if (PlayerState != none)
    {
        PhaseState $= "|turn=" $ PlayerState.PlayerTurnCount;
        if (class'APX_FullIntel'.default.EnableFullIntel
            && PlayerState.PlayerTurnCount != LastPatrolObservationTurn)
        {
            LastPatrolObservationTurn = PlayerState.PlayerTurnCount;
            RecordCurrentPatrolWaypoints(LastPatrolObservationTurn);
        }
        if (RecordedMissionType == "SabotageTransmitter"
            && PlayerState.PlayerTurnCount != LastRelayScanTurn)
        {
            LastRelayScanTurn = PlayerState.PlayerTurnCount;
            RecordSabotageRelayCandidates(LastRelayScanTurn);
        }
    }
    if (`TACTICALRULES != none)
        PhaseState $= "|active_team=" $ string(`TACTICALRULES.GetUnitActionTeam());
    if (PhaseState != LastPhase)
    {
        Emit("phase", PhaseState);
        LastPhase = PhaseState;
    }
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', UnitState)
    {
        if (UnitState.GetAssociatedPlayerID() == OwnerPlayerID
            && UnitState.GetTeam() == eTeam_XCom)
            RecordUnit(UnitState, true, false);
    }
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
        OwnerPlayerID, VisibleEnemies);
    foreach VisibleEnemies(EnemyRef)
    {
        UnitState = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (UnitState == none || UnitState.GetMyTemplate().bIsCosmetic)
            continue;
        VisibleIDs.AddItem(UnitState.ObjectID);
        RecordUnit(UnitState, false, PreviousVisibleIDs.Find(UnitState.ObjectID) == INDEX_NONE);
        RecordVisibleEnemyScoreRule(UnitState);
        RecordEnemyKnowledge(UnitState);
    }
    for (Index = 0; Index < PreviousVisibleIDs.Length; ++Index)
    {
        if (VisibleIDs.Find(PreviousVisibleIDs[Index]) == INDEX_NONE)
            Emit("visibility_lost", "|id=" $ PreviousVisibleIDs[Index]);
    }
    PreviousVisibleIDs = VisibleIDs;
    RecordResults();
}

function bool IsOwnUnitAt(int ObjectID, int HistoryIndex)
{
    local XComGameState_Unit UnitState;
    UnitState = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        ObjectID, eReturnType_Reference, HistoryIndex));
    return UnitState != none && UnitState.GetAssociatedPlayerID() == OwnerPlayerID;
}

// Never pass -1 to the history getter as a previous frame: native -1 means
// CURRENT. The recorder's validated mission start is also a hard boundary.
static function int ResultPreviousHistoryIndex(int ResultHistoryIndex, int StartStateIndex)
{
    if (StartStateIndex < 0 || ResultHistoryIndex <= 0)
        return -1;
    if (ResultHistoryIndex <= StartStateIndex)
        return -1;
    return ResultHistoryIndex - 1;
}

static function bool ResultInvolvesLocalUnit(bool bOwnSourceAfter,
    bool bOwnSourceBefore, bool bOwnTargetEither)
{
    return bOwnSourceAfter || bOwnSourceBefore || bOwnTargetEither;
}

function bool IsOwnUnitAcrossResult(int ObjectID, int ResultHistoryIndex,
    int BeforeHistoryIndex)
{
    if (ObjectID <= 0 || ResultHistoryIndex < 0 || `XCOMHISTORY == none)
        return false;
    if (IsOwnUnitAt(ObjectID, ResultHistoryIndex))
        return true;
    return BeforeHistoryIndex >= 0
        && BeforeHistoryIndex >= RecordedStartStateIndex
        && BeforeHistoryIndex < ResultHistoryIndex
        && IsOwnUnitAt(ObjectID, BeforeHistoryIndex);
}

function RecordResults()
{
    local XComGameState HistoryState;
    local XComGameStateContext_Ability Context;
    local array<StateObjectReference> VisibleEnemies, BeforeActionEnemies;
    local StateObjectReference TargetRef;
    local int EndIndex, SourceID, TargetID, TargetIndex, BeforeHistoryIndex;
    local bool bOwnAction, bOwnActionBefore, bOwnTarget, bPrimaryOwnTarget, bSourceVisible;
    local string AbilityName, SourceScope;

    EndIndex = Min(`XCOMHISTORY.GetCurrentHistoryIndex(),
        HistoryCursor + Clamp(MaxHistoryFramesPerObserve, 16, 2048));
    while (HistoryCursor < EndIndex && !bLimitReported)
    {
        ++HistoryCursor;
        HistoryState = `XCOMHISTORY.GetGameStateFromHistory(HistoryCursor);
        if (HistoryState == none)
            continue;
        RecordScoreDeltas(HistoryState);
        Context = XComGameStateContext_Ability(HistoryState.GetContext());
        if (Context == none)
            continue;
        SourceID = Context.InputContext.SourceObject.ObjectID;
        TargetID = Context.InputContext.PrimaryTarget.ObjectID;
        BeforeHistoryIndex = ResultPreviousHistoryIndex(HistoryCursor, RecordedStartStateIndex);
        bOwnAction = IsOwnUnitAt(SourceID, HistoryCursor);
        bOwnActionBefore = false;
        if (!bOwnAction && BeforeHistoryIndex >= 0)
            bOwnActionBefore = IsOwnUnitAt(SourceID, BeforeHistoryIndex);
        // Mind control can transfer a friendly target to the enemy in this
        // very frame. Relevance and target redaction must retain its own-side
        // observation before the transfer, including secondary targets.
        bPrimaryOwnTarget = IsOwnUnitAcrossResult(TargetID, HistoryCursor, BeforeHistoryIndex);
        bOwnTarget = bPrimaryOwnTarget;
        foreach Context.InputContext.MultiTargets(TargetRef)
            bOwnTarget = bOwnTarget || IsOwnUnitAcrossResult(
                TargetRef.ObjectID, HistoryCursor, BeforeHistoryIndex);
        // Never dump unrelated enemy actions or the positions of unseen units.
        if (!ResultInvolvesLocalUnit(bOwnAction, bOwnActionBefore, bOwnTarget))
            continue;
        VisibleEnemies.Length = 0;
        BeforeActionEnemies.Length = 0;
        class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
            OwnerPlayerID, VisibleEnemies, HistoryCursor);
        if (bOwnAction && BeforeHistoryIndex >= 0)
            class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
                OwnerPlayerID, BeforeActionEnemies, BeforeHistoryIndex);
        bSourceVisible = bOwnAction || VisibleEnemies.Find('ObjectID', SourceID) != INDEX_NONE;
        SourceScope = "unseen_other";
        if (bOwnAction)
            SourceScope = "friendly";
        else if (bSourceVisible)
            SourceScope = "visible_enemy";
        AbilityName = "unseen_attack";
        if (bSourceVisible)
            AbilityName = string(Context.InputContext.AbilityTemplateName);
        else
            SourceID = 0;
        // Preserve friendly targets; redact enemy target IDs no longer visible.
        if (!bPrimaryOwnTarget
            && VisibleEnemies.Find('ObjectID', TargetID) == INDEX_NONE)
        {
            if (BeforeActionEnemies.Find('ObjectID', TargetID) == INDEX_NONE)
                TargetID = 0;
        }
        if (Context.InterruptionStatus == eInterruptionStatus_Interrupt)
        {
            Emit("interrupted", "|history=" $ HistoryCursor $ "|source=" $ SourceID
                $ "|source_scope=" $ SourceScope
                $ "|target=" $ TargetID $ "|ability=" $ Safe(AbilityName));
            continue;
        }
        Emit("result", "|history=" $ HistoryCursor $ "|source=" $ SourceID
            $ "|turn=" $ TurnAtHistory(HistoryCursor)
            $ "|source_scope=" $ SourceScope
            $ "|target=" $ TargetID $ "|ability=" $ Safe(AbilityName)
            $ "|hit=" $ string(Context.ResultContext.HitResult)
            $ "|chance=" $ Context.ResultContext.CalculatedHitChance
            $ "|interruption=" $ string(Context.InterruptionStatus)
            $ TargetHealthFields(TargetID, HistoryCursor));
        for (TargetIndex = 0; TargetIndex < Context.InputContext.MultiTargets.Length; ++TargetIndex)
        {
            TargetID = Context.InputContext.MultiTargets[TargetIndex].ObjectID;
            if (!IsOwnUnitAcrossResult(TargetID, HistoryCursor, BeforeHistoryIndex)
                && VisibleEnemies.Find('ObjectID', TargetID) == INDEX_NONE
                && BeforeActionEnemies.Find('ObjectID', TargetID) == INDEX_NONE)
                continue;
            if (TargetIndex >= Context.ResultContext.MultiTargetHitResults.Length)
                continue;
            Emit("result_target", "|history=" $ HistoryCursor $ "|source=" $ SourceID
                $ "|turn=" $ TurnAtHistory(HistoryCursor)
                $ "|source_scope=" $ SourceScope
                $ "|target=" $ TargetID $ "|ability=" $ Safe(AbilityName)
                $ "|target_index=" $ TargetIndex
                $ "|hit=" $ string(Context.ResultContext.MultiTargetHitResults[TargetIndex])
                $ TargetHealthFields(TargetID, HistoryCursor));
        }
    }
}

function string TargetHealthFields(int TargetID, int HistoryIndex)
{
    local XComGameState_Unit BeforeUnit, AfterUnit;

    if (TargetID <= 0 || HistoryIndex <= 0)
        return "";
    BeforeUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        TargetID, eReturnType_Reference, HistoryIndex - 1));
    AfterUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        TargetID, eReturnType_Reference, HistoryIndex));
    if (BeforeUnit == none || AfterUnit == none)
        return "";
    return "|target_hp_before=" $ BeforeUnit.GetCurrentStat(eStat_HP)
        $ "|target_hp_after=" $ AfterUnit.GetCurrentStat(eStat_HP)
        $ "|target_alive_after=" $ AfterUnit.IsAlive()
        $ "|target_incapacitated_after=" $ AfterUnit.IsIncapacitated()
        $ "|target_bleeding_out_after=" $ AfterUnit.IsBleedingOut()
        $ "|target_shield_before=" $ BeforeUnit.GetCurrentStat(eStat_ShieldHP)
        $ "|target_shield_after=" $ AfterUnit.GetCurrentStat(eStat_ShieldHP);
}

function string ActionFields(XComGameState_Unit UnitState, string Kind,
    AvailableAction Action, int TargetIndex, float Score)
{
    local XComGameState_Ability Ability;
    local XComGameState_Unit TargetUnit;
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage;
    local int TargetID, Chance, AllowsShield, ReleasedAllies, LinkedEnemies;
    local int ComboAbilityID, ComboTargetID;
    local float RetainedAttackValue;
    local bool bHasAPCombo;
    local array<StateObjectReference> VisibleEnemies;
    local string AbilityName, Reason;

    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
        Action.AbilityObjectRef.ObjectID));
    AbilityName = "unknown";
    Reason = "unknown";
    Chance = -1;
    if (Ability != none)
    {
        AbilityName = string(Ability.GetMyTemplateName());
        Reason = class'APX_CombatPlanner'.static.GetActionReason(UnitState, Ability.GetMyTemplateName());
        if (Ability.GetMyTemplateName() == 'ThrowGrenade' || Ability.GetMyTemplateName() == 'LaunchGrenade')
            Reason = "explosive_area_attack";
        if (class'APX_ActionEconomy'.static.IsSupportedPreparation(Ability.GetMyTemplateName()))
        {
            class'APX_MissionPlanner'.static.GetVisibleThreats(UnitState, VisibleEnemies);
            bHasAPCombo = class'APX_ActionEconomy'.static.GetRetainedAttack(UnitState, Ability,
                VisibleEnemies, ComboAbilityID, ComboTargetID, RetainedAttackValue);
        }
    }
    if (TargetIndex >= 0 && TargetIndex < Action.AvailableTargets.Length)
    {
        TargetID = Action.AvailableTargets[TargetIndex].PrimaryTarget.ObjectID;
        TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(TargetID));
        if (Ability != none && Ability.GetMyTemplate() != none && TargetUnit != none
            && Ability.GetMyTemplate().AbilityToHitCalc != none)
        {
            Chance = Ability.GetShotBreakdown(Action.AvailableTargets[TargetIndex], Breakdown);
            Ability.GetDamagePreview(Action.AvailableTargets[TargetIndex].PrimaryTarget,
                MinDamage, MaxDamage, AllowsShield);
            class'APX_CombatPlanner'.static.GetKnownSourceBenefits(UnitState, TargetUnit,
                ReleasedAllies, LinkedEnemies);
        }
    }
    return "|kind=" $ Safe(Kind) $ "|unit=" $ UnitState.ObjectID
        $ "|ability=" $ Safe(AbilityName) $ "|reason=" $ Safe(Reason) $ "|target=" $ TargetID
        $ "|target_index=" $ TargetIndex $ "|score=" $ Score $ "|chance=" $ Chance
        $ "|raw_min_damage=" $ MinDamage.Damage $ "|raw_max_damage=" $ MaxDamage.Damage
        $ "|ap_combo_available=" $ bHasAPCombo
        $ "|ap_combo_followup_ability_id=" $ ComboAbilityID $ "|ap_combo_followup_target=" $ ComboTargetID
        $ "|ap_combo_retained_attack_value=" $ RetainedAttackValue
        $ "|ap_combo_model=current_legal_attack_after_stationary_preparation"
        $ "|known_released_allies=" $ ReleasedAllies $ "|known_linked_enemies=" $ LinkedEnemies;
}

function CandidateAction(XComGameState_Unit UnitState, string Kind,
    AvailableAction Action, int TargetIndex, float Score)
{
    Emit("candidate", ActionFields(UnitState, Kind, Action, TargetIndex, Score));
}

function string MoveFields(XComGameState_Unit UnitState, const out array<TTile> Path, float Score)
{
    local array<StateObjectReference> VisibleEnemies;
    local TTile Destination;
    local float CurrentRisk, CandidateRisk, SupportScore, BestAttackNow, BestAttackAfterMove;
    local float NativeAttackValue, ProjectedAttackValue;
    local int ForecastTarget, NativeChance, ProjectedChance;
    local bool bHasForecast;

    if (Path.Length == 0)
        return "|kind=move|unit=" $ UnitState.ObjectID $ "|score=" $ Score $ "|path_tiles=0";
    Destination = Path[Path.Length - 1];
    class'APX_MissionPlanner'.static.GetVisibleThreats(UnitState, VisibleEnemies);
    CurrentRisk = class'APX_MissionPlanner'.static.ExposureRisk(UnitState, UnitState.TileLocation, VisibleEnemies);
    CandidateRisk = class'APX_MissionPlanner'.static.ExposureRisk(UnitState, Destination, VisibleEnemies);
    SupportScore = class'APX_MissionPlanner'.static.SquadPositionScore(UnitState, Destination);
    class'APX_MissionPlanner'.static.GetMoveAttackOptions(UnitState, VisibleEnemies,
        BestAttackNow, BestAttackAfterMove);
    bHasForecast = class'APX_RepositionPlanner'.static.EvaluateDestination(UnitState, Destination,
        ForecastTarget, NativeChance, ProjectedChance, NativeAttackValue, ProjectedAttackValue);
    return "|kind=move|unit=" $ UnitState.ObjectID $ "|score=" $ Score
        $ "|path_tiles=" $ Path.Length $ "|x=" $ Path[Path.Length - 1].X
        $ "|y=" $ Path[Path.Length - 1].Y $ "|z=" $ Path[Path.Length - 1].Z
        $ "|ap_before=" $ UnitState.NumActionPoints() $ "|visible_threats=" $ VisibleEnemies.Length
        $ "|current_risk=" $ CurrentRisk $ "|candidate_risk=" $ CandidateRisk
        $ "|support_score=" $ SupportScore
        $ "|current_poison_cloud=" $ class'APX_HazardKnowledge'.static.IsKnownPoisonCloudAtTile(
            UnitState, UnitState.TileLocation)
        $ "|destination_poison_cloud=" $ class'APX_HazardKnowledge'.static.IsKnownPoisonCloudAtTile(
            UnitState, Destination)
        $ "|needs_poison_escape=" $ class'APX_HazardKnowledge'.static.NeedsPoisonEscape(UnitState)
        $ "|offensive_forecast=" $ bHasForecast $ "|forecast_target=" $ ForecastTarget
        $ "|native_chance_now=" $ NativeChance $ "|projected_chance=" $ ProjectedChance
        $ "|projected_attack_value=" $ ProjectedAttackValue
        $ "|forecast_model=bounded_geometry"
        $ "|best_attack_now=" $ BestAttackNow $ "|best_attack_after_move_ap=" $ BestAttackAfterMove
        $ "|potential_attack_loss=" $ FMax(0.0, BestAttackNow - BestAttackAfterMove);
}

function CandidateMove(XComGameState_Unit UnitState, const out array<TTile> Path, float Score)
{
    Emit("candidate", MoveFields(UnitState, Path, Score));
}

// Capture the preview before dispatch. Activation can replace the global rules
// cache or consume ammunition; its post-action preview is not decision evidence.
function PrepareChosenAction(XComGameState_Unit UnitState, AvailableAction Action,
    int TargetIndex, float Score)
{
    PreparedChoiceFields = ActionFields(UnitState, "action", Action, TargetIndex, Score);
}

// Freeze the chosen center and each known affected unit, not the last center
// considered by the area planner. These records are previews; chosen.accepted
// and subsequent result_target records establish submission and actual damage.
function PrepareChosenArea(XComGameState_Unit UnitState, AvailableAction Action,
    int TargetIndex, float Score, vector AimLocation, const out array<vector> Locations)
{
    local vector Impact;
    local int PreviewTargets;

    if (UnitState == none || UnitState.GetAssociatedPlayerID() != OwnerPlayerID)
        return;
    PreparedChoiceFields = ActionFields(UnitState, "area", Action, TargetIndex, Score)
        $ "|aim_x=" $ AimLocation.X $ "|aim_y=" $ AimLocation.Y $ "|aim_z=" $ AimLocation.Z;
    if (Locations.Length == 1)
    {
        Impact = Locations[0];
        PreparedChoiceFields $= "|impact_x=" $ Impact.X $ "|impact_y=" $ Impact.Y $ "|impact_z=" $ Impact.Z;
    }
    PreviewTargets = RecordAreaTargetPreviews(UnitState, Action, TargetIndex);
    PreparedChoiceFields $= "|preview_targets=" $ PreviewTargets;
}

function int RecordAreaTargetPreviews(XComGameState_Unit UnitState,
    AvailableAction Action, int TargetIndex)
{
    local XComGameState_Ability Ability;
    local X2AbilityTemplate Template;
    local XComGameState_Item SourceWeapon, Ammo;
    local X2GrenadeTemplate Grenade;
    local AvailableTarget SelectedTarget;
    local array<StateObjectReference> VisibleUnits;
    local StateObjectReference TargetRef;
    local XComGameState_Unit TargetUnit;
    local array<X2Effect> Effects;
    local X2Effect Effect;
    local WeaponDamageValue MinDamage, MaxDamage, EmptyDamage;
    local float RawMin, RawMax, MinTotal, MaxTotal, Armor;
    local int AllowsShield, Count, CurrentHistory;
    local bool bOwnTarget, bFalloff;
    local string Scope;

    if (UnitState == none || UnitState.GetAssociatedPlayerID() != OwnerPlayerID
        || TargetIndex < 0 || TargetIndex >= Action.AvailableTargets.Length)
        return 0;
    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(Action.AbilityObjectRef.ObjectID));
    if (Ability == none || Ability.OwnerStateObject.ObjectID != UnitState.ObjectID
        || (Ability.GetMyTemplateName() != 'ThrowGrenade' && Ability.GetMyTemplateName() != 'LaunchGrenade'))
        return 0;
    Template = Ability.GetMyTemplate();
    SourceWeapon = Ability.GetSourceWeapon();
    if (Template == none || SourceWeapon == none)
        return 0;
    Ammo = Ability.GetSourceAmmo();
    if (Ammo != none)
        Grenade = X2GrenadeTemplate(Ammo.GetMyTemplate());
    else if (Template.bUseLaunchedGrenadeEffects)
        Grenade = X2GrenadeTemplate(SourceWeapon.GetLoadedAmmoTemplate(Ability));
    else if (Template.bUseThrownGrenadeEffects)
        Grenade = X2GrenadeTemplate(SourceWeapon.GetMyTemplate());
    if (Grenade == none || (Grenade.DataName != 'FragGrenade' && Grenade.DataName != 'AlienGrenade'))
        return 0;
    if (Template.bUseLaunchedGrenadeEffects)
        Effects = Grenade.LaunchedGrenadeEffects;
    else
        Effects = Grenade.ThrownGrenadeEffects;
    SelectedTarget = Action.AvailableTargets[TargetIndex];
    CurrentHistory = `XCOMHISTORY.GetCurrentHistoryIndex();
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleObjectsForPlayer(OwnerPlayerID, VisibleUnits);
    bFalloff = `SecondWaveEnabled('ExplosiveFalloff');
    foreach SelectedTarget.AdditionalTargets(TargetRef)
    {
        if (Count >= 64)
            break;
        // Test visibility before reading target health, armor or effects.
        bOwnTarget = IsOwnUnitAt(TargetRef.ObjectID, CurrentHistory);
        if (!bOwnTarget && VisibleUnits.Find('ObjectID', TargetRef.ObjectID) == INDEX_NONE)
            continue;
        TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(TargetRef.ObjectID));
        if (TargetUnit == none || TargetUnit.GetMyTemplate().bIsCosmetic)
            continue;
        RawMin = 0.0;
        RawMax = 0.0;
        MinTotal = 0.0;
        MaxTotal = 0.0;
        Armor = TargetUnit.GetArmorMitigationForUnitFlag();
        foreach Effects(Effect)
        {
            if (Effect == none)
                continue;
            MinDamage = EmptyDamage;
            MaxDamage = EmptyDamage;
            AllowsShield = 0;
            // Grenades use secondary effects. Ability.GetDamagePreview on the
            // empty primary target would misleadingly report zero damage.
            Effect.GetDamagePreview(TargetRef, Ability, false, MinDamage, MaxDamage, AllowsShield);
            RawMin += MinDamage.Damage;
            RawMax += MaxDamage.Damage;
            if (X2Effect_ApplyWeaponDamage(Effect) != none
                && X2Effect_ApplyWeaponDamage(Effect).bIgnoreArmor)
            {
                MinTotal += MinDamage.Damage;
                MaxTotal += MaxDamage.Damage;
            }
            else
            {
                MinTotal += class'APX_CombatPlanner'.static.PreviewDamageAfterArmor(
                    MinDamage.Damage, Armor, MinDamage.Pierce, 1);
                MaxTotal += class'APX_CombatPlanner'.static.PreviewDamageAfterArmor(
                    MaxDamage.Damage, Armor, MaxDamage.Pierce, 1);
            }
        }
        // The stock preview omits explosive falloff. Preserve the raw preview
        // and flag its limitation; do not present its minimum as a safe floor.
        if (bFalloff)
            MinTotal = 0.0;
        Scope = bOwnTarget ? "friendly" : "visible";
        Emit("area_target_preview", "|source=" $ UnitState.ObjectID $ "|target=" $ TargetRef.ObjectID
            $ "|ability=" $ Ability.GetMyTemplateName() $ "|target_scope=" $ Scope
            $ "|target_hp=" $ TargetUnit.GetCurrentStat(eStat_HP)
            $ "|target_shield=" $ TargetUnit.GetCurrentStat(eStat_ShieldHP)
            $ "|preview_raw_min_damage=" $ RawMin $ "|preview_raw_max_damage=" $ RawMax
            $ "|preview_min_damage=" $ MinTotal $ "|preview_max_damage=" $ MaxTotal
            $ "|explosive_falloff=" $ bFalloff);
        ++Count;
    }
    return Count;
}

function PrepareChosenMove(XComGameState_Unit UnitState, const out array<TTile> Path, float Score)
{
    PreparedChoiceFields = MoveFields(UnitState, Path, Score);
    RecordMoveThreatPreviews(UnitState, Path);
}

// Selected moves only: candidate scans do not multiply the per-enemy traces.
// These previews use the same currently visible enemy list as movement scoring.
function RecordMoveThreatPreviews(XComGameState_Unit UnitState, const out array<TTile> Path)
{
    local array<StateObjectReference> VisibleEnemies;
    local StateObjectReference EnemyRef;
    local XComGameState_Unit Enemy;
    local TTile CurrentTile, DestinationTile, EnemyTile;
    local vector CurrentLocation, DestinationLocation, EnemyLocation;
    local GameRulesCache_VisibilityInfo CurrentVisibility, DestinationVisibility;
    local float Angle, MeleeReach, Weight, TargetWeight;
    local string CurrentCover, DestinationCover;
    local bool bCurrentLOS, bDestinationLOS, bCurrentDefaultView, bDestinationDefaultView;
    local int Count, MarkedAimBonus;

    if (UnitState == none || UnitState.GetAssociatedPlayerID() != OwnerPlayerID || Path.Length < 2)
        return;
    MarkedAimBonus = class'APX_EnemyKnowledge'.static.KnownMarkedAimBonus(UnitState);
    TargetWeight = class'APX_EnemyKnowledge'.static.TargetStatusWeight(UnitState);
    CurrentTile = UnitState.TileLocation;
    DestinationTile = Path[Path.Length - 1];
    CurrentLocation = `XWORLD.GetPositionFromTileCoordinates(CurrentTile);
    DestinationLocation = `XWORLD.GetPositionFromTileCoordinates(DestinationTile);
    class'APX_MissionPlanner'.static.GetVisibleThreats(UnitState, VisibleEnemies);
    foreach VisibleEnemies(EnemyRef)
    {
        if (Count >= 64)
            break;
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (!class'APX_CombatPlanner'.static.IsVisibleHostile(UnitState, Enemy, VisibleEnemies))
            continue;
        EnemyTile = Enemy.TileLocation;
        EnemyLocation = `XWORLD.GetPositionFromTileCoordinates(EnemyTile);
        CurrentCover = string(`XWORLD.GetCoverTypeForTarget(EnemyLocation, CurrentLocation, Angle));
        DestinationCover = string(`XWORLD.GetCoverTypeForTarget(EnemyLocation, DestinationLocation, Angle));
        bCurrentLOS = `XWORLD.CanSeeTileToTile(EnemyTile, CurrentTile, CurrentVisibility);
        bDestinationLOS = `XWORLD.CanSeeTileToTile(EnemyTile, DestinationTile, DestinationVisibility);
        // Stock Bind validation uses bVisibleFromDefault from this query but
        // explicitly checks cover separately: tile LOS does not fill TargetCover.
        bCurrentDefaultView = bCurrentLOS && CurrentVisibility.bVisibleFromDefault;
        bDestinationDefaultView = bDestinationLOS && DestinationVisibility.bVisibleFromDefault;
        MeleeReach = class'APX_MissionPlanner'.static.GetMeleeThreatReach(Enemy);
        Weight = class'APX_EnemyKnowledge'.static.ThreatWeight(Enemy);
        Emit("move_threat_preview", "|source=" $ UnitState.ObjectID $ "|enemy=" $ Enemy.ObjectID
            $ "|enemy_template=" $ Enemy.GetMyTemplateName() $ "|melee_only=" $ Enemy.IsMeleeOnly()
            $ "|melee_threat_reach=" $ MeleeReach $ "|threat_weight=" $ Weight
            $ "|marked_aim_bonus=" $ MarkedAimBonus $ "|target_status_weight=" $ TargetWeight
            $ "|current_distance=" $ class'APX_MissionPlanner'.static.TileDistance(CurrentTile, EnemyTile)
            $ "|destination_distance=" $ class'APX_MissionPlanner'.static.TileDistance(DestinationTile, EnemyTile)
            $ "|current_threat_risk=" $ class'APX_MissionPlanner'.static.ThreatRiskAtTile(UnitState, Enemy, CurrentTile, MeleeReach, Weight)
            $ "|destination_threat_risk=" $ class'APX_MissionPlanner'.static.ThreatRiskAtTile(UnitState, Enemy, DestinationTile, MeleeReach, Weight)
            $ "|current_cover=" $ CurrentCover $ "|destination_cover=" $ DestinationCover
            $ "|current_los=" $ bCurrentLOS $ "|destination_los=" $ bDestinationLOS
            $ "|current_default_view=" $ bCurrentDefaultView
            $ "|destination_default_view=" $ bDestinationDefaultView);
        ++Count;
    }
}

function ChosenAction(XComGameState_Unit UnitState, AvailableAction Action,
    int TargetIndex, float Score, bool bAccepted)
{
    if (PreparedChoiceFields == "")
        PreparedChoiceFields = "|kind=action|unit=" $ UnitState.ObjectID
            $ "|score=" $ Score $ "|preview_missing=true";
    Emit("chosen", PreparedChoiceFields $ "|accepted=" $ bAccepted);
}

function ChosenMove(XComGameState_Unit UnitState, const out array<TTile> Path,
    float Score, bool bAccepted)
{
    if (PreparedChoiceFields == "")
        PreparedChoiceFields = "|kind=move|unit=" $ UnitState.ObjectID
            $ "|score=" $ Score $ "|preview_missing=true";
    Emit("chosen", PreparedChoiceFields $ "|accepted=" $ bAccepted);
}

function Finish(string Reason)
{
    local XComGameState_BattleData BattleData;
    local string Outcome;
    local int PendingHistory;

    if (!bStarted || bFinished)
        return;
    if (!IsRecordingMission())
    {
        // Closing a stale observer cannot borrow the next world's outcome.
        // Leave this session incomplete rather than inventing a native result.
        Emit("recording_context_lost", "|reason=history_or_mission_changed"
            $ "|history=" $ HistoryCursor);
        UnregisterScoreObservers();
        bFinished = true;
        return;
    }
    if (`XCOMHISTORY != none)
    {
        PendingHistory = Max(0, `XCOMHISTORY.GetCurrentHistoryIndex() - HistoryCursor);
        BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
            class'XComGameState_BattleData', true));
    }
    // HasTacticalGameEnded can become true while the last action and winner
    // are still being committed. The controller retries Finish on later ticks.
    // Wait for authoritative battle data instead of freezing a partial snapshot
    // and treating the default false bLocalPlayerWon value as a loss.
    if (Reason == "tactical_game_ended"
        && (BattleData == none || BattleData.VictoriousPlayer.ObjectID == 0))
    {
        if (!bEndPending || LastEndHistory != HistoryCursor + PendingHistory)
        {
            bEndPending = true;
            LastEndHistory = HistoryCursor + PendingHistory;
            Observe("ending");
            Emit("ending", "|reason=" $ Safe(Reason) $ "|outcome=unknown"
                $ "|history=" $ LastEndHistory);
        }
        return;
    }
    Observe("finish");
    if (`XCOMHISTORY != none)
        PendingHistory = Max(0, `XCOMHISTORY.GetCurrentHistoryIndex() - HistoryCursor);
    RecordGameScore("finish");
    Outcome = "unknown";
    if (BattleData != none && BattleData.VictoriousPlayer.ObjectID != 0)
        Outcome = BattleData.bLocalPlayerWon ? "win" : "loss";
    Emit("end", "|reason=" $ Safe(Reason) $ "|outcome=" $ Outcome
        $ "|history=" $ HistoryCursor $ "|history_pending=" $ PendingHistory);
    UnregisterScoreObservers();
    bFinished = true;
}
