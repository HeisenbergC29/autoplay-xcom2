// #89/#10: runtime-only, per-unit, per-goal route memory and an explicitly
// two-step NATIVE blue march. Never creates a dash path or grants AP.
// Accept a second blue only after the first was actually dispatched this turn,
// and rescan the native cache/current contact envelope before the second order.
class APX_RouteTempo extends Object config(AutoplayXCom2);

struct RouteVisit
{
    var int UnitID;
    var TTile FromTile;
    var TTile ToTile;
    var TTile GoalTile;
    var int Turn;
    var bool bFirstBlueClear;
};

struct RouteGoal
{
    var int UnitID;
    var TTile Tile;
};

var config bool EnableSequentialBlue;
var config bool EnableSoftRouteMemory;
var config int MaxMemoryTurns;
var config int MaxVisitEntries;
var config float ReturnTilePenalty;
var config float RevisitTilePenalty;

var private XComGameStateHistory OwnedHistory;
var private int OwnedStartIndex, OwnedBattleID, OwnedPlayerID, LastHistoryIndex;
var private array<RouteVisit> Visits;
var private array<RouteGoal> Goals;

// Keep no visit after battle/load/rewind/manual OFF, never assume cached
// coordinates from a prior mission describe a valid route here.
function Reset()
{
    Visits.Length = 0;
    Goals.Length = 0;
    OwnedHistory = none;
    OwnedStartIndex = INDEX_NONE;
    OwnedBattleID = 0;
    OwnedPlayerID = 0;
    LastHistoryIndex = INDEX_NONE;
}

function bool Refresh(int LocalPlayerID, int CurrentTurn)
{
    local XComGameState_BattleData Battle;
    local int CurrentIndex, CurrentStart, Index;

    if (`XCOMHISTORY == none || LocalPlayerID <= 0 || CurrentTurn < 0)
    {
        Reset();
        return false;
    }
    Battle = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    if (Battle == none)
    {
        Reset();
        return false;
    }
    CurrentIndex = `XCOMHISTORY.GetCurrentHistoryIndex();
    CurrentStart = `XCOMHISTORY.FindStartStateIndex();
    if (OwnedHistory != `XCOMHISTORY || OwnedStartIndex != CurrentStart
        || OwnedBattleID != Battle.ObjectID || OwnedPlayerID != LocalPlayerID
        || CurrentIndex < LastHistoryIndex)
        Reset();

    OwnedHistory = `XCOMHISTORY;
    OwnedStartIndex = CurrentStart;
    OwnedBattleID = Battle.ObjectID;
    OwnedPlayerID = LocalPlayerID;
    LastHistoryIndex = CurrentIndex;

    for (Index = Visits.Length - 1; Index >= 0; --Index)
    {
        if (Visits[Index].Turn > CurrentTurn
            || CurrentTurn - Visits[Index].Turn > Clamp(MaxMemoryTurns, 1, 5))
            Visits.Remove(Index, 1);
    }
    return true;
}

// The goal is NOT inferred from the unit's last visible location. Switching
// mission goals invalidates all old memory for this unit, including a blue
// continuation grant.
function SetGoal(int UnitID, TTile Tile)
{
    local RouteGoal Entry;
    local int Index, Found;

    if (UnitID <= 0)
        return;
    Found = INDEX_NONE;
    for (Index = 0; Index < Goals.Length; ++Index)
    {
        if (Goals[Index].UnitID == UnitID)
        {
            Found = Index;
            break;
        }
    }
    if (Found == INDEX_NONE)
    {
        if (Goals.Length >= 32)
            Goals.Remove(0, 1);
        Entry.UnitID = UnitID;
        Entry.Tile = Tile;
        Goals.AddItem(Entry);
        return;
    }
    if (Goals[Found].Tile != Tile)
    {
        Goals[Found].Tile = Tile;
        for (Index = Visits.Length - 1; Index >= 0; --Index)
        {
            if (Visits[Index].UnitID == UnitID)
                Visits.Remove(Index, 1);
        }
    }
}

static function bool CanUseSecondBlue(bool bEnabled, bool bFullIntel,
    bool bActualFirstClear, bool bSameUnitGoalTurnAndTile,
    bool bAmbushActive, bool bRecentContact, bool bUrgent,
    bool bHasNativeMove, int StandardAP, int MovingAP)
{
    return bEnabled && bFullIntel && bActualFirstClear
        && bSameUnitGoalTurnAndTile && !bAmbushActive && !bRecentContact
        && !bUrgent && bHasNativeMove && StandardAP == 1 && MovingAP >= 1;
}

// This ticket comes ONLY from a successful controller-owned first blue order;
// it never outlives the current own turn or a different current destination.
function bool HasFirstBlueTicket(int UnitID, TTile Goal, TTile CurrentTile,
    int CurrentTurn)
{
    local int Index;

    for (Index = Visits.Length - 1; Index >= 0; --Index)
    {
        if (Visits[Index].UnitID != UnitID || Visits[Index].Turn != CurrentTurn
            || Visits[Index].GoalTile != Goal)
            continue;
        return Visits[Index].bFirstBlueClear
            && Visits[Index].ToTile == CurrentTile;
    }
    return false;
}

static function float SoftVisitPenalty(int CurrentTurn, int VisitTurn,
    int Window, bool bDirectReturn, bool bRevisit,
    float ReturnPenalty, float RevisitPenalty)
{
    local int Age;
    local float Strength, BasePenalty;

    Age = CurrentTurn - VisitTurn;
    Window = Clamp(Window, 1, 5);
    if (Age < 0 || Age > Window || (!bDirectReturn && !bRevisit))
        return 0.0;
    BasePenalty = bDirectReturn
        ? FClamp(ReturnPenalty, 0.0, 40.0)
        : FClamp(RevisitPenalty, 0.0, 25.0);
    Strength = float(Window + 1 - Age) / float(Window + 1);
    return BasePenalty * Strength;
}

// Positive SOFT cost, never a disallowed tile. The only legal path back
// remains available. Prefer avoiding a previous origin (A-B-A) to merely
// avoiding an older visited endpoint.
function float PenaltyFor(int UnitID, TTile Goal, TTile Destination,
    int CurrentTurn)
{
    local int Index;
    local float Value;

    if (!EnableSoftRouteMemory)
        return 0.0;
    Value = 0.0;
    for (Index = Visits.Length - 1; Index >= 0; --Index)
    {
        if (Visits[Index].UnitID != UnitID || Visits[Index].GoalTile != Goal)
            continue;
        Value = FMax(Value, SoftVisitPenalty(CurrentTurn,
            Visits[Index].Turn, MaxMemoryTurns,
            Visits[Index].FromTile == Destination,
            Visits[Index].ToTile == Destination,
            ReturnTilePenalty, RevisitTilePenalty));
    }
    return Value;
}

function RecordAccepted(int UnitID, TTile Start, TTile End, TTile Goal,
    int CurrentTurn, bool bFirstBlueClear)
{
    local RouteVisit Visit;

    if (UnitID <= 0 || Start == End || CurrentTurn < 0)
        return;
    SetGoal(UnitID, Goal);
    Visit.UnitID = UnitID;
    Visit.FromTile = Start;
    Visit.ToTile = End;
    Visit.GoalTile = Goal;
    Visit.Turn = CurrentTurn;
    Visit.bFirstBlueClear = bFirstBlueClear && EnableSequentialBlue;
    if (Visits.Length >= Clamp(MaxVisitEntries, 8, 128))
        Visits.Remove(0, 1);
    Visits.AddItem(Visit);
}

function int CountVisits()
{
    return Visits.Length;
}
