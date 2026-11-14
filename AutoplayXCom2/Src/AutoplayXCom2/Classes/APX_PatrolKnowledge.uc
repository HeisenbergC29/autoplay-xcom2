// Read-only, user-authorized stored patrol metadata (target, native AI clock).
// The next chosen route or action is NOT present in a usual green patrol.
// Never request an AI decision, inspect private alert knowledge or roll RNG.
class APX_PatrolKnowledge extends Object config(AutoplayXCom2);

var config int MaxGroupsPerObservation;
var config int MaxMemberReferencesPerObservation;

static function bool EligiblePatrolMember(bool bAlive, bool bIncapacitated,
    bool bRemoved, bool bCivilian, bool bCosmetic, bool bHostile,
    bool bTileInWorld)
{
    return bAlive && !bIncapacitated && !bRemoved && !bCivilian
        && !bCosmetic && bHostile && bTileInWorld;
}

static function bool FiniteWaypointCoordinate(float Value)
{
    // Reject NaN/infinity before native world-to-tile conversion. This bound
    // comfortably exceeds tactical maps; zero has no documented null contract.
    return Value >= -100000000.0 && Value <= 100000000.0;
}

static function bool UsableStoredWaypoint(float X, float Y, float Z,
    bool bTileInWorld)
{
    return FiniteWaypointCoordinate(X) && FiniteWaypointCoordinate(Y)
        && FiniteWaypointCoordinate(Z) && bTileInWorld;
}

static function int ConsumeMemberReference(int Remaining)
{
    return Max(0, Remaining - 1);
}

// All groups share the caller's member-reference budget. A partially inspected
// group is not emitted with a misleading complete member count or midpoint.
// This does not identify an unengaged patrol or guarantee future use of target.
static function bool GetCurrentPatrolWaypoint(XComGameState_AIGroup Group,
    int LocalPlayerID, out TTile Waypoint, out vector Midpoint,
    out int HostileMembers, out int RemainingMemberChecks)
{
    local XComGameState_Player LocalPlayer;
    local XComGameState_Unit Member;
    local StateObjectReference Ref;
    local array<int> SeenMembers;
    local vector Target;

    HostileMembers = 0;
    Midpoint = vect(0,0,0);
    if (!class'APX_FullIntel'.default.EnableFullIntel || Group == none || Group.bRemoved
        || `XWORLD == none || `XCOMHISTORY == none || `TACTICALRULES == none
        || LocalPlayerID != `TACTICALRULES.GetLocalClientPlayerObjectID())
        return false;
    LocalPlayer = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(LocalPlayerID));
    if (LocalPlayer == none || LocalPlayer.GetTeam() != eTeam_XCom)
        return false;
    Target = Group.CurrentTargetLocation;
    if (!FiniteWaypointCoordinate(Target.X) || !FiniteWaypointCoordinate(Target.Y)
        || !FiniteWaypointCoordinate(Target.Z))
        return false;
    Waypoint = `XWORLD.GetTileCoordinatesFromPosition(Target);
    if (!UsableStoredWaypoint(Target.X, Target.Y, Target.Z,
        !`XWORLD.IsTileOutOfRange(Waypoint)))
        return false;

    foreach Group.m_arrMembers(Ref)
    {
        if (RemainingMemberChecks <= 0)
            return false;
        // Duplicate and invalid references also consume budget, before any
        // state lookup, so iteration itself has one global upper bound.
        RemainingMemberChecks = ConsumeMemberReference(RemainingMemberChecks);
        if (SeenMembers.Find(Ref.ObjectID) != INDEX_NONE)
            continue;
        SeenMembers.AddItem(Ref.ObjectID);
        Member = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
        if (Member == none || Member.GetMyTemplate() == none)
            continue;
        if (!EligiblePatrolMember(Member.IsAlive(), Member.IsIncapacitated(),
            Member.bRemoved || Member.bRemovedFromPlay, Member.IsCivilian()
                || Member.GetMyTemplateName() == 'HostileVIPCivilian',
            Member.GetMyTemplate().bIsCosmetic,
            class'XGPlayerNativeBase'.static.AreEnemyTeams(
                LocalPlayer.GetTeam(), Member.GetTeam()),
            !`XWORLD.IsTileOutOfRange(Member.TileLocation)))
            continue;
        ++HostileMembers;
        Midpoint += `XWORLD.GetPositionFromTileCoordinates(Member.TileLocation);
    }
    if (HostileMembers <= 0)
        return false;
    Midpoint /= float(HostileMembers);
    return true;
}


// Native AI clock: AIPlayerData.StatsData.TurnCount, not the local squad turn.
// A negative/default/future/stale timestamp cannot certify a usable waypoint.
static function int StoredWaypointAge(int AITurn, int DestinationTurn)
{
    if (AITurn <= 0 || DestinationTurn < 0 || DestinationTurn > AITurn || AITurn - DestinationTurn > 2)
        return -1;
    return AITurn - DestinationTurn;
}

// Check only actual AIPlayerData.PatrolGroupList membership; any other group
// has no asserted current patrol route and is ignored for waypoint freshness.
// A listed group with incomplete metadata is UNKNOWN (not an empty corridor).
static function bool StoredPatrolEvidence(XComGameState_AIGroup Group,
    int LocalPlayerID, out int RemainingMemberChecks, out string Reason)
{
    local XComGameState_AIPlayerData AIData;
    local XComGameState_Player AIPlayer, LocalPlayer;
    local vector Midpoint;
    local TTile TargetTile;
    local int Hostiles, ScannedAI;
    local bool bFound;

    Reason = "not_listed_patrol";
    if (Group == none || `XCOMHISTORY == none || `XWORLD == none)
    {
        Reason = "patrol_context_missing";
        return false;
    }
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_AIPlayerData', AIData)
    {
        if (++ScannedAI > 8)
        {
            Reason = "ai_data_scan_limit";
            return false;
        }
        if (AIData == none
            || AIData.PatrolGroupList.Find('ObjectID', Group.ObjectID) == INDEX_NONE)
            continue;
        bFound = true;
        break;
    }
    if (!bFound)
        return false;
    LocalPlayer = XComGameState_Player(
        `XCOMHISTORY.GetGameStateForObjectID(LocalPlayerID));
    AIPlayer = XComGameState_Player(
        `XCOMHISTORY.GetGameStateForObjectID(AIData.m_iPlayerObjectID));
    if (LocalPlayer == none || AIPlayer == none
        || LocalPlayer.GetTeam() != eTeam_XCom
        || !class'XGPlayerNativeBase'.static.AreEnemyTeams(
            LocalPlayer.GetTeam(), AIPlayer.GetTeam()))
    {
        Reason = "patrol_owner_unknown";
        return false;
    }
    if (StoredWaypointAge(AIData.StatsData.TurnCount,
        Group.TurnCountForLastDestination) < 0)
    {
        Reason = "patrol_ai_clock_stale_or_unknown";
        return false;
    }
    if (!GetCurrentPatrolWaypoint(Group, LocalPlayerID, TargetTile,
        Midpoint, Hostiles, RemainingMemberChecks))
    {
        Reason = "patrol_members_or_waypoint_unknown";
        return false;
    }
    if (VSizeSq(Midpoint - Group.CurrentTargetLocation) <=
        FMax(0.0, Group.DESTINATION_REACHED_SIZE_SQ))
    {
        Reason = "patrol_waypoint_reached";
        return false;
    }
    Reason = "fresh_current_waypoint_not_full_route";
    return true;
}
