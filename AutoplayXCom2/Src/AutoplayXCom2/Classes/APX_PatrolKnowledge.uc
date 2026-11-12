// The user-authorized exception exposes only this stored CURRENT target.
// Its current tactical use and the next AI decision remain unknown. Never
// request a new AI decision, inspect private alert knowledge or roll RNG.
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
