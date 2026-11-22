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

/** Match the leader and the complete ordered roster used to build the native patrol. */
static function bool MatchesPatrolRoster(XGAIPatrolGroup Patrol, XComGameState_AIGroup Group)
{
    local int Index;

    if (Patrol == none || Group == none || Group.m_arrMembers.Length < 1
        || Group.m_arrMembers.Length > 24 || Patrol.m_arrUnitIDs.Length != Group.m_arrMembers.Length)
        return false;
    for (Index = 0; Index < Patrol.m_arrUnitIDs.Length; ++Index)
    {
        if (Patrol.m_arrUnitIDs[Index] <= 0
            || Patrol.m_arrUnitIDs[Index] != Group.m_arrMembers[Index].ObjectID)
            return false;
    }
    return true;
}

/**
 * Find the current history leader in its owner's existing navigator registry.
 * A missing, ambiguous or differently owned registration supplies no patrol.
 * Nothing is retained across a load or requested from a refreshing getter.
 */
static function XGAIPatrolGroup RegisteredLeaderPatrol(XComGameState_AIGroup Group,
    XComGameState_Unit Leader, XComGameState_Player Owner)
{
    local XGAIPlayer AIActor;
    local XGAIPatrolGroup Patrol, Match;

    if (Group == none || Leader == none || Owner == none
        || Group.m_arrMembers.Length < 1 || Group.m_arrMembers.Length > 24
        || Group.m_arrMembers[0].ObjectID != Leader.ObjectID
        || Leader.GroupMembershipID != Group.ObjectID
        || Leader.ControllingPlayer.ObjectID != Owner.ObjectID)
        return none;
    AIActor = XGAIPlayer(Owner.GetVisualizer());
    if (AIActor == none || AIActor.ObjectID != Owner.ObjectID || AIActor.m_kNav == none
        || AIActor.m_kNav.m_kPlayer != AIActor || AIActor.m_kNav.m_arrPatrolGroups.Length > 48)
        return none;
    foreach AIActor.m_kNav.m_arrPatrolGroups(Patrol)
    {
        if (Patrol == none || Patrol.m_kPlayer != AIActor || Patrol.m_arrUnitIDs.Length == 0
            || Patrol.m_arrUnitIDs[0] != Leader.ObjectID)
            continue;
        if (Match != none || !MatchesPatrolRoster(Patrol, Group))
            return none;
        Match = Patrol;
    }
    return Match;
}

/** Compare the two observed tiles with both ends of the already stored path. */
static function bool MatchesDisplacement(TTile TurnStart, TTile Position, TTile PathStart, TTile PathEnd)
{
    return TurnStart != Position && TurnStart == PathStart && Position == PathEnd;
}

/**
 * Qualify actual net displacement relative to the unit's recorded turn start.
 * A missing segment or different endpoint cannot establish patrol movement.
 * Being back at the turn-start tile says nothing about intermediate steps.
 */
static function string LeaderMotionEvidence(XGAIPatrolGroup Patrol, XComGameState_Unit Leader)
{
    local int PathLength;

    if (Patrol == none || Leader == none || `XWORLD == none
        || `XWORLD.IsTileOutOfRange(Leader.TurnStartLocation)
        || `XWORLD.IsTileOutOfRange(Leader.TileLocation))
        return "patrol_motion_unobserved";
    if (Leader.TurnStartLocation == Leader.TileLocation)
        return "patrol_no_net_displacement";
    PathLength = Patrol.m_arrGroupPath.Length;
    if (PathLength >= 2 && MatchesDisplacement(Leader.TurnStartLocation, Leader.TileLocation,
            Patrol.m_arrGroupPath[0], Patrol.m_arrGroupPath[PathLength - 1]))
        return "completed_leader_segment";
    return "patrol_motion_unobserved";
}

/**
 * Select only a fresh hostile group's stored waypoint with independently
 * observed leader movement. Green movement uses the live navigator registry,
 * which can exist even when the serialized patrol list is empty. Never ask the
 * navigator to select or recompute a segment. Reasons qualify absent evidence.
 */
static function bool StoredPatrolEvidence(XComGameState_AIGroup Group,
    int LocalPlayerID, out int RemainingMemberChecks, out string Reason)
{
    local XComGameState_AIPlayerData AIData;
    local XComGameState_Player AIPlayer, LocalPlayer;
    local XComGameState_Unit Leader;
    local XGAIPatrolGroup Patrol;
    local vector Midpoint;
    local TTile TargetTile;
    local int Hostiles, ScannedAI;
    local bool bFound, bListed;
    local string Motion;

    Reason = "not_listed_patrol";
    if (!class'APX_FullIntel'.default.EnableFullIntel || Group == none || Group.bRemoved
        || `XCOMHISTORY == none || `XWORLD == none || `TACTICALRULES == none
        || LocalPlayerID != `TACTICALRULES.GetLocalClientPlayerObjectID())
    {
        Reason = "patrol_context_missing";
        return false;
    }
    if (Group.m_arrMembers.Length == 0)
        return false;
    if (RemainingMemberChecks <= 0)
    {
        Reason = "patrol_member_budget";
        return false;
    }
    RemainingMemberChecks = ConsumeMemberReference(RemainingMemberChecks);
    Leader = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        Group.m_arrMembers[0].ObjectID));
    if (Leader == none || Leader.bRemoved || Leader.bRemovedFromPlay
        || !Leader.IsAlive() || Leader.IsIncapacitated())
        return false;
    LocalPlayer = XComGameState_Player(
        `XCOMHISTORY.GetGameStateForObjectID(LocalPlayerID));
    AIPlayer = XComGameState_Player(
        `XCOMHISTORY.GetGameStateForObjectID(Leader.ControllingPlayer.ObjectID));
    if (LocalPlayer == none || LocalPlayer.GetTeam() != eTeam_XCom)
    {
        Reason = "patrol_owner_unknown";
        return false;
    }
    if (AIPlayer == none || AIPlayer.GetTeam() != Leader.GetTeam()
        || !class'XGPlayerNativeBase'.static.AreEnemyTeams(
            LocalPlayer.GetTeam(), AIPlayer.GetTeam()))
        return false;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_AIPlayerData', AIData)
    {
        if (++ScannedAI > 8)
        {
            Reason = "ai_data_scan_limit";
            return false;
        }
        if (AIData != none && AIData.m_iPlayerObjectID == AIPlayer.ObjectID)
        {
            bFound = true;
            break;
        }
    }
    if (!bFound)
        return false;
    if (AIData.PatrolGroupList.Length > 48)
    {
        Reason = "patrol_list_limit";
        return false;
    }
    bListed = AIData.PatrolGroupList.Find('ObjectID', Group.ObjectID) != INDEX_NONE;
    Patrol = RegisteredLeaderPatrol(Group, Leader, AIPlayer);
    if (!bListed && Patrol == none)
        return false;
    // An optional navigator entry without a witnessed segment cannot become
    // a patrol candidate or conceal a different group's positive observation.
    Motion = LeaderMotionEvidence(Patrol, Leader);
    if (!bListed && Motion != "completed_leader_segment")
    {
        Reason = Motion;
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
    if (Motion != "completed_leader_segment")
    {
        Reason = Motion;
        return false;
    }
    Reason = bListed ? "stored_list_completed_segment" : "navigator_completed_segment";
    return true;
}
