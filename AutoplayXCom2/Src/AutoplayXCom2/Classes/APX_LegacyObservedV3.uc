// Runtime observation of installed Legacy config rates, deliberately partial.
// Never overwrite archived observed_v2, mutate game state or certify a native total.
// Stock config(Ladder) supplies mission/template tables and their DLC overrides.
// Non-Ladder scoring uses those rates only for observed, qualified public events.
class APX_LegacyObservedV3 extends Object
    dependson(XComGameState, XComGameStateContext_Ability,
        X2StrategyGameRulesetDataStructures, X2GameRulesetVisibilityDataStructures,
        X2ChallengeModeDataStructures, XComGameState_LadderProgress,
        X2TacticalGameRulesetDataStructures);

struct ObservedUnit
{
    var int ID;
    var name TemplateName;
    var bool bOriginalFriendly;
    var bool bEligible;
    var bool bWounded;
    var bool bLost;
    var bool bSeenAliveEnemy;
    var bool bEliminated;
    var int EliminationPoints;
    var bool bUnknownEnemyOrigin;
    var float LastHP;
};

var private XComGameStateHistory ObservedHistory;
var private int OwnerPlayerID;
var private int BattleID;
var private string MissionType;
var private int StartIndex;
var private int HistoryCursor;
var private int LastHistoryIndex;
var private bool bInitialized;
var private bool bEventsRegistered;
var private bool bVerifiedTacticalStart;
var private bool bEarlyEventCoverage;
var private bool bObjectiveHistoryGap;
var private int ReplayedObjectiveCount;
var private bool bUnresolvedEnemyOrigins;
var private int UnresolvedOriginCount;
var private array<ObservedUnit> Units;
var private array<string> CompletedObjectives;
var private array<int> ObjectivePoints;
var private array<int> RescuedCivilianIDs;

static function string GetProfileID()
{
    return "wotc_legacy_config_observed_v3_partial";
}

// Explicit observed decay convention applied to installed Legacy rates.
// Native award qualification and exact boundary parity remain unproven.
static function int DecayedPoints(int StartingPoints, int MinimumPoints,
    int DecreasePerTurn, int TurnOffset, int Turn)
{
    return Max(MinimumPoints, StartingPoints - Max(0, Turn - TurnOffset) * DecreasePerTurn);
}


static function bool InstalledRateCountsSupported(int EnemyCount, int ObjectiveCount)
{
    return EnemyCount > 0 && EnemyCount <= 512
        && ObjectiveCount > 0 && ObjectiveCount <= 512;
}

static function bool HasInstalledRates()
{
    // Fail closed when the installed config(Ladder) was not loaded. The
    // native SDK's structdefaults alone are the *wrong* tables for WOTC.
    // A truncated table must not silently fall back to the wrong default.
    return InstalledRateCountsSupported(
        class'XComGameState_LadderProgress'.default.DefaultEnemyScoringTable.Length,
        class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable.Length);
}

static function ChallengeEnemyScoring FindEnemyRule(name TemplateName)
{
    local ChallengeEnemyScoring Rate;
    local int Index;

    Rate = class'XComGameState_LadderProgress'.default.DefaultEnemyScoring;
    for (Index = 0;
         Index < Min(512, class'XComGameState_LadderProgress'.default.DefaultEnemyScoringTable.Length);
         ++Index)
    {
        if (class'XComGameState_LadderProgress'.default.DefaultEnemyScoringTable[Index].CharacterTemplateName
            != TemplateName)
            continue;
        Rate = class'XComGameState_LadderProgress'.default.DefaultEnemyScoringTable[Index];
        break;
    }
    return Rate;
}

// Source classification is deliberately evidence-gated. An enemy already in
// a verified tactical start is an ordinary encounter. NewSpawnedUnit is a native
// explicit spawned marker. Other late arrivals may be reinforcements or
// summons; do not misaward ordinary points when their source is unknown.
static function int EnemyPoints(name TemplateName, int Turn, bool bConfirmedSpawned)
{
    local ChallengeEnemyScoring Rate;

    if (Turn < 0 || !HasInstalledRates())
        return 0;
    Rate = FindEnemyRule(TemplateName);
    if (bConfirmedSpawned)
        return Rate.SpawnedPoints;
    return DecayedPoints(Rate.StartingPoints, Rate.MinPoints,
        Rate.DecreasePerTurn, Rate.TurnOffset, Turn);
}

static function int SoldierPenaltyPoints(bool bEligible, bool bWounded, bool bLost,
    int UninjuredBonus, int WoundedBonus)
{
    local int Points;

    if (!bEligible)
        return 0;
    Points = 0;
    // Stock handlers only submit deductions when the configured bonus is
    // positive. A zero/negative config must never become a positive award.
    if (bWounded && UninjuredBonus > 0)
        Points -= UninjuredBonus;
    if (bLost && WoundedBonus > 0)
        Points -= WoundedBonus;
    return Points;
}

static function int SoldierPoints(bool bEligible, bool bWounded, bool bLost)
{
    local ChallengeSoldierScoring Rate;

    if (!HasInstalledRates())
        return 0;
    Rate = class'XComGameState_LadderProgress'.default.DefaultSoldierScoring;
    // Stock LadderProgress.OnUnitDamage/OnUnitKilled subtract precisely
    // UninjuredBonus on FIRST wound and WoundedBonus on loss.
    return SoldierPenaltyPoints(bEligible, bWounded, bLost,
        Rate.UninjuredBonus, Rate.WoundedBonus);
}

// 0 ordinary, 1 explicitly spawned, -1 unknown/protected. Merely finding
// an object in an arbitrary archive start is not proof of enemy origin.
static function int ClassifyEnemyOrigin(bool bExplicitSpawned, bool bVerifiedStart,
    bool bHasStartUnit, bool bStartedXCom, bool bStartedEnemy, bool bPreviousXCom)
{
    if (bStartedXCom || bPreviousXCom)
        return -1;
    if (bExplicitSpawned)
        return 1;
    if (bVerifiedStart && bHasStartUnit && bStartedEnemy)
        return 0;
    return -1;
}

static function int CompletedObjectivePoints(int Turn, name MissionName,
    int TextPoolIndex, int GroupID, int LineIndex)
{
    local ChallengeObjectiveScoring Rate;
    local int Index;

    if (Turn < 0 || !HasInstalledRates())
        return 0;
    Rate = class'XComGameState_LadderProgress'.default.DefaultObjectiveScoring;
    for (Index = 0;
         Index < Min(512, class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable.Length);
         ++Index)
    {
        if (class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable[Index].MissionType != MissionName
            || class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable[Index].TextPoolIndex != TextPoolIndex
            || class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable[Index].GroupID != GroupID
            || class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable[Index].LineIndex != LineIndex)
            continue;
        Rate = class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable[Index];
        break;
    }
    return DecayedPoints(Rate.StartingPoints, Rate.MinPoints,
        Rate.DecreasePerTurn, Rate.TurnOffset, Turn);
}

function string GetCoverageStatus()
{
    if (!bInitialized || !HasInstalledRates())
        return "unavailable_rates";
    if (bUnresolvedEnemyOrigins)
        return "partial_unknown_enemy_origin";
    if (!bVerifiedTacticalStart)
        return "partial_unverified_tactical_start";
    if (bObjectiveHistoryGap)
        return "partial_objective_history_gap";
    // Historical objective transitions can be replayed, but the native
    // CivilianRescued event has no equally reliable state-only substitute.
    if (!bEarlyEventCoverage)
        return "partial_civilian_listener_started_late";
    // Even with full observed history, the native disabled/restart/bonus
    // award qualification is not exposed by the UC SDK.
    return "partial_native_disabled_restart_bonus_unverified";
}

function bool IsReady()
{
    return bInitialized && HasInstalledRates();
}

function Cleanup()
{
    local Object Listener;
    local X2EventManager EventManager;

    if (bEventsRegistered)
    {
        EventManager = `XEVENTMGR;
        if (EventManager != none)
        {
            Listener = self;
            EventManager.UnRegisterFromEvent(Listener, 'MissionObjectiveMarkedCompleted');
            EventManager.UnRegisterFromEvent(Listener, 'CivilianRescued');
        }
    }
    bEventsRegistered = false;
    bVerifiedTacticalStart = false;
    bEarlyEventCoverage = false;
    bObjectiveHistoryGap = false;
    ReplayedObjectiveCount = 0;
    bUnresolvedEnemyOrigins = false;
    UnresolvedOriginCount = 0;
    bInitialized = false;
    ObservedHistory = none;
    OwnerPlayerID = 0;
    BattleID = 0;
    MissionType = "";
    StartIndex = -1;
    HistoryCursor = -1;
    LastHistoryIndex = -1;
    Units.Length = 0;
    CompletedObjectives.Length = 0;
    ObjectivePoints.Length = 0;
    RescuedCivilianIDs.Length = 0;
}

function RegisterEvents()
{
    local Object Listener;
    local X2EventManager EventManager;

    EventManager = `XEVENTMGR;
    if (EventManager == none || bEventsRegistered)
        return;
    Listener = self;
    EventManager.RegisterForEvent(Listener, 'MissionObjectiveMarkedCompleted',
        OnObjectiveCompleted, ELD_OnStateSubmitted);
    EventManager.RegisterForEvent(Listener, 'CivilianRescued',
        OnCivilianRescued, ELD_OnStateSubmitted);
    bEventsRegistered = true;
}

function bool HasCurrentMission()
{
    local XComGameState_BattleData BattleData;

    if (!bInitialized || `XCOMHISTORY == none || `XCOMHISTORY != ObservedHistory)
        return false;
    if (`XCOMHISTORY.FindStartStateIndex() != StartIndex
        || `XCOMHISTORY.GetCurrentHistoryIndex() < LastHistoryIndex)
        return false;
    if (`XCOMHISTORY.GetSingleGameStateObjectForClass(class'XComGameState_LadderProgress', true) != none
        || `XCOMHISTORY.GetSingleGameStateObjectForClass(class'XComGameState_ChallengeData', true) != none)
        return false;
    BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    return BattleData != none && BattleData.ObjectID == BattleID
        && BattleData.MapData.ActiveMission.sType == MissionType;
}

function bool EnsureMission()
{
    local WorldInfo World;
    local XComTacticalController PC;
    local XComGameStateHistory History;
    local XComGameState_BattleData BattleData, StartingBattle;
    local XComGameState StartState;
    local XComGameStateContext_TacticalGameRule StartContext;
    local int CurrentIndex, CurrentStart, PlayerID;

    History = `XCOMHISTORY;
    World = class'WorldInfo'.static.GetWorldInfo();
    if (History == none || World == none)
    {
        Cleanup();
        return false;
    }
    PC = XComTacticalController(World.GetALocalPlayerController());
    if (PC == none || PC.m_XGPlayer == none)
    {
        Cleanup();
        return false;
    }
    PlayerID = PC.m_XGPlayer.ObjectID;
    BattleData = XComGameState_BattleData(History.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    CurrentIndex = History.GetCurrentHistoryIndex();
    CurrentStart = History.FindStartStateIndex();
    if (PlayerID <= 0 || BattleData == none || CurrentStart < 0 || CurrentIndex < CurrentStart
        || History.GetSingleGameStateObjectForClass(class'XComGameState_LadderProgress', true) != none
        || History.GetSingleGameStateObjectForClass(class'XComGameState_ChallengeData', true) != none)
    {
        Cleanup();
        return false;
    }
    if (HasCurrentMission() && OwnerPlayerID == PlayerID)
    {
        LastHistoryIndex = CurrentIndex;
        RegisterEvents();
        return true;
    }
    Cleanup();
    StartingBattle = XComGameState_BattleData(History.GetGameStateForObjectID(
        BattleData.ObjectID, eReturnType_Reference, CurrentStart));
    if (StartingBattle == none || StartingBattle.MapData.ActiveMission.sType != BattleData.MapData.ActiveMission.sType)
        return false;
    StartState = History.GetGameStateFromHistory(CurrentStart);
    if (StartState != none)
        StartContext = XComGameStateContext_TacticalGameRule(StartState.GetContext());
    bVerifiedTacticalStart = StartContext != none
        && StartContext.GameRuleType == eGameRule_TacticalGameStart;
    ObservedHistory = History;
    OwnerPlayerID = PlayerID;
    BattleID = BattleData.ObjectID;
    MissionType = BattleData.MapData.ActiveMission.sType;
    StartIndex = CurrentStart;
    HistoryCursor = CurrentStart - 1;
    LastHistoryIndex = CurrentIndex;
    bInitialized = true;
    bEarlyEventCoverage = bVerifiedTacticalStart && CurrentIndex <= CurrentStart + 1;
    RegisterEvents();
    `log("Legacy observed rates|profile=" $ GetProfileID()
        $ "|enemy_entries=" $ class'XComGameState_LadderProgress'.default.DefaultEnemyScoringTable.Length
        $ "|objective_entries=" $ class'XComGameState_LadderProgress'.default.DefaultObjectiveScoringTable.Length
        $ "|verified_tactical_start=" $ string(bVerifiedTacticalStart)
        $ "|early_event_coverage=" $ string(bEarlyEventCoverage), true, 'AutoplayXCom2');
    return true;
}

function int TurnAtHistory(int HistoryIndex)
{
    local XComGameState_Player PlayerState;

    PlayerState = XComGameState_Player(ObservedHistory.GetGameStateForObjectID(
        OwnerPlayerID, eReturnType_Reference, HistoryIndex));
    return PlayerState != none ? PlayerState.PlayerTurnCount : -1;
}

function int UnitIndex(XComGameState_Unit UnitState)
{
    local ObservedUnit Entry;
    local XComGameState_Unit StartingUnit;
    local UnitValue SpawnedValue;
    local int Index;

    Index = Units.Find('ID', UnitState.ObjectID);
    if (Index != INDEX_NONE)
        return Index;
    Entry.ID = UnitState.ObjectID;
    Entry.TemplateName = UnitState.GetMyTemplateName();
    if (bVerifiedTacticalStart)
    {
        StartingUnit = XComGameState_Unit(ObservedHistory.GetGameStateForObjectID(
            UnitState.ObjectID, eReturnType_Reference, StartIndex));
        Entry.bOriginalFriendly = StartingUnit != none
            && StartingUnit.GetTeam() == eTeam_XCom
            && StartingUnit.GetAssociatedPlayerID() == OwnerPlayerID;
        if (Entry.bOriginalFriendly)
            Entry.bEligible = StartingUnit.GetPreviousTeam() == eTeam_XCom
                && !StartingUnit.bMissionProvided
                && !StartingUnit.GetUnitValue('NewSpawnedUnit', SpawnedValue);
    }
    Entry.LastHP = UnitState.GetCurrentStat(eStat_HP);
    Units.AddItem(Entry);
    return Units.Length - 1;
}

// UnitState must already be owned or visible at this exact history frame.
function ObserveUnit(XComGameState_Unit UnitState, bool bFriendly, int HistoryIndex)
{
    local UnitValue SpawnedValue, KilledValue;
    local XComGameState_Unit StartingEnemy;
    local int Index, Turn, Origin;
    local float HP;
    local bool bExplicitSpawned, bStartedXCom, bStartedEnemy;

    if (UnitState == none || UnitState.GetMyTemplate() == none || UnitState.GetMyTemplate().bIsCosmetic)
        return;
    Index = UnitIndex(UnitState);
    HP = UnitState.GetCurrentStat(eStat_HP);
    // A verified original soldier remains a soldier while mind-controlled.
    // Without a verified start, current own + native previous-team metadata
    // can qualify an observed penalty, but cannot establish original ownership.
    if (Units[Index].bOriginalFriendly || Units[Index].bEligible
        || (bFriendly && UnitState.GetPreviousTeam() == eTeam_XCom))
    {
        if (bFriendly)
        {
            Units[Index].bEligible = Units[Index].bEligible
                || (UnitState.GetPreviousTeam() == eTeam_XCom && !UnitState.bMissionProvided
                    && !UnitState.GetUnitValue('NewSpawnedUnit', SpawnedValue));
            Units[Index].bWounded = Units[Index].bWounded || UnitState.HighestHP > UnitState.LowestHP;
            Units[Index].bLost = Units[Index].bLost
                || UnitState.GetUnitValue('LadderKilledScored', KilledValue);
        }
        else
        {
            // A now-hostile former soldier exposes ordinary visible HP only.
            Units[Index].bWounded = Units[Index].bWounded || HP < Units[Index].LastHP;
        }
        Units[Index].bLost = Units[Index].bLost || !UnitState.IsAlive();
    }
    else
    {
        if (!bFriendly && UnitState.IsAlive())
            Units[Index].bSeenAliveEnemy = true;
        Turn = TurnAtHistory(HistoryIndex);
        if (!UnitState.IsAlive() && Units[Index].bSeenAliveEnemy
            && !Units[Index].bEliminated && Turn >= 0)
        {
            bExplicitSpawned = UnitState.GetUnitValue('NewSpawnedUnit', SpawnedValue);
            if (bVerifiedTacticalStart)
            {
                StartingEnemy = XComGameState_Unit(ObservedHistory.GetGameStateForObjectID(
                    UnitState.ObjectID, eReturnType_Reference, StartIndex));
                if (StartingEnemy != none)
                {
                    bStartedXCom = StartingEnemy.GetTeam() == eTeam_XCom;
                    bStartedEnemy = StartingEnemy.IsEnemyTeam(eTeam_XCom);
                }
            }
            Origin = ClassifyEnemyOrigin(bExplicitSpawned, bVerifiedTacticalStart,
                StartingEnemy != none, bStartedXCom, bStartedEnemy,
                UnitState.GetPreviousTeam() == eTeam_XCom);
            Units[Index].bEliminated = true;
            if (Origin < 0)
            {
                // Missing/unverified start or an original XCOM/neutral unit
                // is not proof of ordinary enemy origin. Never award it by
                // guessing from current visibility or archive presence.
                Units[Index].bUnknownEnemyOrigin = true;
                bUnresolvedEnemyOrigins = true;
                ++UnresolvedOriginCount;
            }
            else
                Units[Index].EliminationPoints = EnemyPoints(
                    Units[Index].TemplateName, Turn, Origin == 1);
        }
    }
    Units[Index].LastHP = HP;
}

function bool IsOwnUnitAt(int UnitID, int HistoryIndex)
{
    local XComGameState_Unit UnitState;

    UnitState = XComGameState_Unit(ObservedHistory.GetGameStateForObjectID(
        UnitID, eReturnType_Reference, HistoryIndex));
    return UnitState != none && UnitState.GetAssociatedPlayerID() == OwnerPlayerID;
}

function ObserveResultTarget(int UnitID, int HistoryIndex,
    array<StateObjectReference> VisibleNow, array<StateObjectReference> VisibleBefore, bool bOwnAction)
{
    local XComGameState_Unit UnitState;
    local bool bOwnTarget;

    if (UnitID <= 0)
        return;
    bOwnTarget = IsOwnUnitAt(UnitID, HistoryIndex);
    if (!bOwnTarget && VisibleNow.Find('ObjectID', UnitID) == INDEX_NONE
        && (!bOwnAction || VisibleBefore.Find('ObjectID', UnitID) == INDEX_NONE))
        return;
    if (bOwnAction && HistoryIndex > StartIndex
        && VisibleBefore.Find('ObjectID', UnitID) != INDEX_NONE)
    {
        UnitState = XComGameState_Unit(ObservedHistory.GetGameStateForObjectID(
            UnitID, eReturnType_Reference, HistoryIndex - 1));
        ObserveUnit(UnitState, false, HistoryIndex - 1);
    }
    UnitState = XComGameState_Unit(ObservedHistory.GetGameStateForObjectID(
        UnitID, eReturnType_Reference, HistoryIndex));
    ObserveUnit(UnitState, bOwnTarget, HistoryIndex);
}

// Replay actual archived objective transitions for a late F8 enable or load.
// The stock SeqAct_DisplayMissionObjective triggers the event on the first
// ShowCompleted transition when neither completion nor failure was set before.
// Do not award for a completed objective merely present in a start snapshot,
// and do not guess when a required historical state is unavailable.
function ObserveObjectiveHistory(XComGameState Frame, int HistoryIndex)
{
    local XComGameState_ObjectivesList CurrentList, PreviousList;
    local ObjectiveDisplayInfo CurrentInfo, PreviousInfo;
    local string ObjectiveID;
    local bool bPreviouslySet;
    local int Turn;

    if (Frame == none || HistoryIndex <= StartIndex)
        return;
    if (ObservedHistory.GetGameStateFromHistory(HistoryIndex - 1) == none)
    {
        bObjectiveHistoryGap = true;
        return;
    }
    foreach Frame.IterateByClassType(class'XComGameState_ObjectivesList', CurrentList)
    {
        if (CurrentList.ObjectiveDisplayInfos.Length > 128)
        {
            bObjectiveHistoryGap = true;
            continue;
        }
        PreviousList = XComGameState_ObjectivesList(ObservedHistory.GetGameStateForObjectID(
            CurrentList.ObjectID, eReturnType_Reference, HistoryIndex - 1));
        if (PreviousList != none && PreviousList.ObjectiveDisplayInfos.Length > 128)
        {
            bObjectiveHistoryGap = true;
            continue;
        }
        foreach CurrentList.ObjectiveDisplayInfos(CurrentInfo)
        {
            if (CurrentInfo.MissionType != MissionType
                || !CurrentInfo.ShowCompleted || !CurrentInfo.ShowCheckBox
                || CurrentInfo.HideInTactical)
                continue;
            ObjectiveID = MissionType $ ":" $ CurrentInfo.TextPoolIndex $ ":"
                $ CurrentInfo.LineIndex $ ":" $ CurrentInfo.GroupID;
            // A live event listener may already have counted this completion.
            if (CompletedObjectives.Find(ObjectiveID) != INDEX_NONE)
                continue;

            bPreviouslySet = false;
            if (PreviousList != none)
            {
                foreach PreviousList.ObjectiveDisplayInfos(PreviousInfo)
                {
                    if (PreviousInfo.MissionType != CurrentInfo.MissionType
                        || PreviousInfo.TextPoolIndex != CurrentInfo.TextPoolIndex
                        || PreviousInfo.GroupID != CurrentInfo.GroupID
                        || PreviousInfo.LineIndex != CurrentInfo.LineIndex)
                        continue;
                    bPreviouslySet = PreviousInfo.ShowCompleted || PreviousInfo.ShowFailed;
                    break;
                }
            }
            if (bPreviouslySet)
                continue;
            Turn = TurnAtHistory(HistoryIndex);
            if (Turn < 0 || CompletedObjectives.Length >= 128)
            {
                bObjectiveHistoryGap = true;
                continue;
            }
            CompletedObjectives.AddItem(ObjectiveID);
            ObjectivePoints.AddItem(CompletedObjectivePoints(Turn,
                name(MissionType), CurrentInfo.TextPoolIndex,
                CurrentInfo.GroupID, CurrentInfo.LineIndex));
            ++ReplayedObjectiveCount;
            `log("Legacy objective history replay|profile=" $ GetProfileID()
                $ "|history=" $ HistoryIndex
                $ "|recovered=" $ ReplayedObjectiveCount, true, 'AutoplayXCom2');
        }
    }
}

function ObserveFrame(int HistoryIndex)
{
    local XComGameState Frame;
    local XComGameState_Unit UnitState;
    local XComGameStateContext_Ability Context;
    local StateObjectReference UnitRef;
    local array<StateObjectReference> VisibleNow, VisibleBefore;
    local bool bOwnAction;

    Frame = ObservedHistory.GetGameStateFromHistory(HistoryIndex);
    if (Frame == none)
    {
        bObjectiveHistoryGap = true;
        return;
    }
    ObserveObjectiveHistory(Frame, HistoryIndex);
    // Ownership metadata is the gate; do not inspect hidden enemy fields.
    foreach Frame.IterateByClassType(class'XComGameState_Unit', UnitState)
    {
        if (UnitState.GetAssociatedPlayerID() == OwnerPlayerID && UnitState.GetTeam() == eTeam_XCom)
            ObserveUnit(UnitState, true, HistoryIndex);
    }
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
        OwnerPlayerID, VisibleNow, HistoryIndex);
    foreach VisibleNow(UnitRef)
    {
        UnitState = XComGameState_Unit(ObservedHistory.GetGameStateForObjectID(
            UnitRef.ObjectID, eReturnType_Reference, HistoryIndex));
        ObserveUnit(UnitState, false, HistoryIndex);
    }
    Context = XComGameStateContext_Ability(Frame.GetContext());
    if (Context == none || Context.InterruptionStatus == eInterruptionStatus_Interrupt)
        return;
    bOwnAction = IsOwnUnitAt(Context.InputContext.SourceObject.ObjectID, HistoryIndex);
    if (bOwnAction && HistoryIndex > StartIndex)
        class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
            OwnerPlayerID, VisibleBefore, HistoryIndex - 1);
    ObserveResultTarget(Context.InputContext.PrimaryTarget.ObjectID,
        HistoryIndex, VisibleNow, VisibleBefore, bOwnAction);
    foreach Context.InputContext.MultiTargets(UnitRef)
        ObserveResultTarget(UnitRef.ObjectID, HistoryIndex, VisibleNow, VisibleBefore, bOwnAction);
}

function EventListenerReturn OnObjectiveCompleted(Object EventData, Object EventSource,
    XComGameState GameState, Name Event, Object CallbackData)
{
    local SeqAct_DisplayMissionObjective DisplayAction;
    local XComGameState_ObjectivesList ObjectiveList;
    local ObjectiveDisplayInfo Info;
    local string ObjectiveID;
    local int Turn;

    if (!HasCurrentMission() || GameState == none || GameState.HistoryIndex < StartIndex)
        return ELR_NoInterrupt;
    DisplayAction = SeqAct_DisplayMissionObjective(EventSource);
    ObjectiveList = XComGameState_ObjectivesList(EventData);
    if (DisplayAction == none || ObjectiveList == none)
        return ELR_NoInterrupt;
    foreach ObjectiveList.ObjectiveDisplayInfos(Info)
    {
        if (Info.MissionType != MissionType || Info.TextPoolIndex != DisplayAction.TextPoolIndex
            || Info.LineIndex != DisplayAction.LineIndex || Info.GroupID != DisplayAction.GroupID
            || !Info.ShowCompleted || !Info.ShowCheckBox || Info.HideInTactical)
            continue;
        ObjectiveID = MissionType $ ":" $ Info.TextPoolIndex $ ":" $ Info.LineIndex $ ":" $ Info.GroupID;
        Turn = TurnAtHistory(GameState.HistoryIndex);
        if (CompletedObjectives.Find(ObjectiveID) == INDEX_NONE && Turn >= 0)
        {
            CompletedObjectives.AddItem(ObjectiveID);
            ObjectivePoints.AddItem(CompletedObjectivePoints(Turn,
                name(MissionType), DisplayAction.TextPoolIndex,
                DisplayAction.GroupID, DisplayAction.LineIndex));
        }
        break;
    }
    return ELR_NoInterrupt;
}

function EventListenerReturn OnCivilianRescued(Object EventData, Object EventSource,
    XComGameState GameState, Name Event, Object CallbackData)
{
    local XComGameState_Unit Rescuer, Civilian;

    if (!HasCurrentMission() || GameState == none || GameState.HistoryIndex < StartIndex)
        return ELR_NoInterrupt;
    Rescuer = XComGameState_Unit(EventData);
    Civilian = XComGameState_Unit(EventSource);
    if (Rescuer != none && Civilian != none && Rescuer.GetAssociatedPlayerID() == OwnerPlayerID
        && RescuedCivilianIDs.Find(Civilian.ObjectID) == INDEX_NONE)
        RescuedCivilianIDs.AddItem(Civilian.ObjectID);
    return ELR_NoInterrupt;
}

function int GetObservedScore()
{
    local int EndIndex, Index, Score, Points;

    if (!EnsureMission() || !HasInstalledRates())
        return 0;
    // Bound native history/visibility work. A mid-mission load catches up over
    // several HUD ticks, rather than blocking a frame on the entire mission.
    EndIndex = Min(ObservedHistory.GetCurrentHistoryIndex(), HistoryCursor + 256);
    while (HistoryCursor < EndIndex)
    {
        ++HistoryCursor;
        ObserveFrame(HistoryCursor);
    }
    for (Index = 0; Index < Units.Length; ++Index)
    {
        if (Units[Index].bEligible)
            Score += SoldierPoints(Units[Index].bEligible, Units[Index].bWounded, Units[Index].bLost);
        else if (Units[Index].bEliminated)
            Score += Units[Index].EliminationPoints;
    }
    foreach ObjectivePoints(Points)
        Score += Points;
    return Score + RescuedCivilianIDs.Length
        * class'XComGameState_LadderProgress'.default.DefaultSoldierScoring.RescuedCivilianBonus;
}

defaultproperties
{
    StartIndex=-1
    HistoryCursor=-1
    LastHistoryIndex=-1
}
