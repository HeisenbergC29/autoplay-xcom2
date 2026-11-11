// Stock AIGroup stores the CURRENT green-alert patrol destination.
// It does not expose a deterministic future route: the next destination is
// chosen when the current destination is reached or expires, and can depend
// on XCOM's current location. Never request new AI decisions or roll RNG.
class APX_PatrolKnowledge extends Object config(AutoplayXCom2);

var config int MaxGroupsPerObservation;

static function bool IsReadOnlyPatrolCandidate(bool bEngaged,
    bool bPendingScamper, bool bObjectiveGuard, bool bInterceptObjective,
    int MemberCount)
{
    return !bEngaged && !bPendingScamper && !bObjectiveGuard
        && !bInterceptObjective && MemberCount > 0;
}

// This method returns a real CURRENT goal from the game-state history.
// It is not the entire patrol path and is never guaranteed to stay fixed.
static function bool GetCurrentPatrolWaypoint(XComGameState_AIGroup Group,
    out TTile Waypoint)
{
    local vector Target;
    if (Group == none || `XWORLD == none
        || !IsReadOnlyPatrolCandidate(Group.IsEngaged(),
            Group.bPendingScamper, Group.bObjective,
            Group.bInterceptObjectiveLocation, Group.m_arrMembers.Length))
        return false;
    Target = Group.CurrentTargetLocation;
    if (VSizeSq(Target) <= 1.0)
        return false;
    Waypoint = `XWORLD.GetTileCoordinatesFromPosition(Target);
    return !`XWORLD.IsTileOutOfRange(Waypoint);
}

static function bool IsNearCurrentWaypoint(TTile Current, TTile Destination,
    int MaxHorizontalTiles)
{
    return Abs(Current.X - Destination.X) <= Max(1, MaxHorizontalTiles)
        && Abs(Current.Y - Destination.Y) <= Max(1, MaxHorizontalTiles)
        && Abs(Current.Z - Destination.Z) <= 2;
}
