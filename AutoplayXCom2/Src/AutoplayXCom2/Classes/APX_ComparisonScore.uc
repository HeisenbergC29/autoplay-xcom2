// Runtime observation of the frozen wotc_legacy_observed_v1 comparison profile.
// Always partial: this is not a native score, and never supplies tactical orders.
class APX_ComparisonScore extends Object
    dependson(XComGameState, XComGameStateContext_Ability,
        X2StrategyGameRulesetDataStructures, X2GameRulesetVisibilityDataStructures);

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
var private array<ObservedUnit> Units;
var private array<string> CompletedObjectives;
var private array<int> ObjectivePoints;
var private array<int> RescuedCivilianIDs;

// These values mirror tools/legacy-score-rules.json, not a mode's native table.
static function int DecayedPoints(int StartingPoints, int MinimumPoints,
    int DecreasePerTurn, int TurnOffset, int Turn)
{
    return Max(MinimumPoints, StartingPoints - Max(0, Turn - TurnOffset) * DecreasePerTurn);
}

static function int EnemyPoints(name TemplateName, int Turn)
{
    if (Turn < 0)
        return 0;
    if (TemplateName == 'Muton')
        return DecayedPoints(3000, 2000, 200, 1, Turn);
    if (TemplateName == 'Faceless' || TemplateName == 'Viper' || TemplateName == 'Sectoid' || TemplateName == 'PsiZombieCivilian')
        return DecayedPoints(1500, 1000, 100, 1, Turn);
    // Unobserved template overrides/origin remain provisional. The received
    // SDK's explicit default is used, exactly as in the offline comparison.
    return DecayedPoints(500, 100, 100, 1, Turn);
}

static function int SoldierPoints(bool bEligible, bool bWounded, bool bLost)
{
    local int Points;

    if (!bEligible)
        return 0;
    Points = 6000;
    if (bWounded)
        Points -= 1000;
    if (bLost)
        Points -= 5000;
    return Points;
}

static function int CompletedObjectivePoints(int Turn)
{
    if (Turn < 0)
        return 0;
    return DecayedPoints(10000, 5000, 1000, 1, Turn);
}

function bool IsReady()
{
    return bInitialized;
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
    ObservedHistory = History;
    OwnerPlayerID = PlayerID;
    BattleID = BattleData.ObjectID;
    MissionType = BattleData.MapData.ActiveMission.sType;
    StartIndex = CurrentStart;
    HistoryCursor = CurrentStart - 1;
    LastHistoryIndex = CurrentIndex;
    bInitialized = true;
    RegisterEvents();
    return true;
}

function int TurnAtHistory(int HistoryIndex)
{
    local XComGameState_Player PlayerState;

    PlayerState = XComGameState_Player(ObservedHistory.GetGameStateForObjectID(
        OwnerPlayerID, eReturnType_Reference, HistoryIndex));
    return PlayerState != none ? PlayerState.PlayerTurnCount : -1;
}

function int UnitIndex(XComGameState_Unit UnitState, bool bFriendly)
{
    local ObservedUnit Entry;
    local int Index;

    Index = Units.Find('ID', UnitState.ObjectID);
    if (Index != INDEX_NONE)
        return Index;
    Entry.ID = UnitState.ObjectID;
    Entry.TemplateName = UnitState.GetMyTemplateName();
    Entry.bOriginalFriendly = bFriendly;
    Entry.LastHP = UnitState.GetCurrentStat(eStat_HP);
    Units.AddItem(Entry);
    return Units.Length - 1;
}

// UnitState must already be owned or visible at this exact history frame.
function ObserveUnit(XComGameState_Unit UnitState, bool bFriendly, int HistoryIndex)
{
    local UnitValue SpawnedValue, KilledValue;
    local int Index;
    local float HP;

    if (UnitState == none || UnitState.GetMyTemplate() == none || UnitState.GetMyTemplate().bIsCosmetic)
        return;
    Index = UnitIndex(UnitState, bFriendly);
    HP = UnitState.GetCurrentStat(eStat_HP);
    if (Units[Index].bOriginalFriendly)
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
        if (!UnitState.IsAlive() && Units[Index].bSeenAliveEnemy
            && !Units[Index].bEliminated && TurnAtHistory(HistoryIndex) >= 0)
        {
            Units[Index].bEliminated = true;
            Units[Index].EliminationPoints = EnemyPoints(Units[Index].TemplateName, TurnAtHistory(HistoryIndex));
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
        return;
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
            ObjectivePoints.AddItem(CompletedObjectivePoints(Turn));
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

    if (!EnsureMission())
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
        if (Units[Index].bOriginalFriendly)
            Score += SoldierPoints(Units[Index].bEligible, Units[Index].bWounded, Units[Index].bLost);
        else if (Units[Index].bEliminated)
            Score += Units[Index].EliminationPoints;
    }
    foreach ObjectivePoints(Points)
        Score += Points;
    return Score + RescuedCivilianIDs.Length * 1000;
}

defaultproperties
{
    StartIndex=-1
    HistoryCursor=-1
    LastHistoryIndex=-1
}
