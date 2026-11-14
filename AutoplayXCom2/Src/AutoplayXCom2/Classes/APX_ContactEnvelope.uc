// Current-state contact envelope for native, already-known tactical actors.
// -1 UNKNOWN; 0 CLEAR at the explicitly declared CURRENT movement horizon;
//  1 CAUTION (real known source of possible detection/fire).
// No future movement prediction, RNG sampling, forced native LOS, or hidden AP.
class APX_ContactEnvelope extends Object config(AutoplayXCom2)
    dependson(X2GameRulesetVisibilityDataStructures, XGTacticalGameCoreNativeBase);

var config int MaxGroups;
var config int MaxMembers;
var config int MaxDetectors;
var config int MaxTiles;
var config int MaxLOS;
var config float CautionRoutePenalty;
var config float UnknownRoutePenalty;

// This is an estimate of native concealment conditions, not an attack target.
// When a DETECTOR moves to observe a stationary target, directional cover
// matters. A moving concealed soldier does not gain that cover exception.
static function bool ConcealedContactPossible(bool bNativeLOS, bool bStationary,
    bool bDirectionCovered, float DistSq, float DetectionRadius,
    bool bIgnoreDistance)
{
    if (!bNativeLOS || (bStationary && bDirectionCovered))
        return false;
    return bIgnoreDistance || DistSq <= FMax(0.0, DetectionRadius) * FMax(0.0, DetectionRadius);
}

static function bool SnapshotBudgetsValid(int Groups, int Members,
    int Detectors, int Tiles, int LOS)
{
    return Groups > 0 && Members > 0 && Detectors > 0 && Tiles > 0 && LOS > 0;
}

static function float PathStatusPenalty(int Status)
{
    if (Status == 1)
        return FClamp(default.CautionRoutePenalty, 0.0, 60.0);
    if (Status < 0)
        return FClamp(default.UnknownRoutePenalty, 0.0, 30.0);
    return 0.0;
}

// Called only once per APX_Controller.MakeDecision. All soldiers/candidates
// reuse these references and the same remaining integer budgets. A snapshot
// containing truncated actors is never allowed to certify a Clear corridor.
static function bool BuildSnapshot(XComGameState_Unit Soldier,
    out array<StateObjectReference> KnownUnits,
    out array<StateObjectReference> KnownInteractives,
    out string Reason, out int RemainingGroups, out int RemainingMembers)
{
    local array<StateObjectReference> VisibleObjects;
    local StateObjectReference Ref;
    local XComGameState_Unit UnitState;
    local XComGameState_InteractiveObject Interactive;
    local XComGameState_AIGroup Group;
    local int Index, Scanned;
    local string PatrolReason;

    KnownUnits.Length = 0;
    KnownInteractives.Length = 0;
    Reason = "none";
    if (Soldier == none || `XCOMHISTORY == none || `XWORLD == none
        || `TACTICALRULES == none)
    {
        Reason = "world_or_soldier_unavailable";
        return false;
    }
    if (!class'APX_FullIntel'.default.EnableFullIntel)
    {
        // No read across the user's native visibility boundary.
        Reason = "limited_visibility";
        return false;
    }
    if (Soldier.GetTeam() != eTeam_XCom
        || Soldier.GetAssociatedPlayerID() != `TACTICALRULES.GetLocalClientPlayerObjectID())
    {
        Reason = "invalid_local_owner";
        return false;
    }
    class'APX_FullIntel'.static.GetKnownEnemies(Soldier, KnownUnits);
    if (KnownUnits.Length > Clamp(default.MaxDetectors, 1, 64))
    {
        Reason = "detector_snapshot_truncated";
        return false;
    }
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleObjectsForPlayer(
        Soldier.GetAssociatedPlayerID(), VisibleObjects, , -1, true);
    if (VisibleObjects.Length > 256)
    {
        Reason = "visible_object_snapshot_truncated";
        return false;
    }
    for (Index = 0; Index < VisibleObjects.Length; ++Index)
    {
        Ref = VisibleObjects[Index];
        UnitState = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
        if (UnitState != none && UnitState.IsCivilian() && UnitState.IsAlive()
            && !UnitState.bRemovedFromPlay && UnitState.GetMyTemplate() != none
            && !UnitState.GetMyTemplate().bIsCosmetic
            && KnownUnits.Find('ObjectID', Ref.ObjectID) == INDEX_NONE)
            KnownUnits.AddItem(Ref);
        Interactive = XComGameState_InteractiveObject(
            `XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
        if (Interactive != none && !Interactive.bRemovedFromPlay
            && !Interactive.bHasBeenHacked && Interactive.DetectionRange > 0.0)
            KnownInteractives.AddItem(Ref);
        if (KnownUnits.Length + KnownInteractives.Length > Clamp(default.MaxDetectors, 1, 64))
        {
            Reason = "detector_snapshot_truncated";
            return false;
        }
    }

    // Patrol lists and their clock may be stale. We check all groups once,
    // including member-ref budget. The waypoint NEVER narrows a safety radius.
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_AIGroup', Group)
    {
        if (RemainingGroups <= 0)
        {
            Reason = "group_budget";
            return false;
        }
        --RemainingGroups;
        if (Group == none || Group.bRemoved)
            continue;
        ++Scanned;
        if (!class'APX_PatrolKnowledge'.static.StoredPatrolEvidence(
            Group, Soldier.GetAssociatedPlayerID(), RemainingMembers, PatrolReason))
        {
            if (PatrolReason != "not_listed_patrol")
            {
                Reason = PatrolReason;
                return false;
            }
        }
    }
    Reason = "current_known_contacts";
    return true;
}

// Evaluate the ENTIRE native-proposed route against a single current snapshot.
// A nonzero future horizon is UNKNOWN: stored patrol waypoints are not selected
// next-turn paths. Incomplete LOS/peeks or exhausted budget remain UNKNOWN.
static function int AssessRoute(XComGameState_Unit Soldier, const out array<TTile> Path,
    const out array<StateObjectReference> KnownUnits,
    const out array<StateObjectReference> KnownInteractives,
    bool bSnapshotComplete, string SnapshotReason, int HorizonAITurns,
    out int RemainingDetectors, out int RemainingTiles, out int RemainingLOS,
    out string Reason)
{
    local XComGameState_Unit Detector;
    local XComGameState_InteractiveObject Interactive;
    local GameRulesCache_VisibilityInfo Visibility;
    local StateObjectReference Ref;
    local vector TilePosition, DetectorPosition;
    local TTile Tile;
    local float SightRange, DetectRange, DistanceSq, CoverAngle;
    local bool bIgnoresDistance, bLOS, bCovered;
    local int Step, Index, Status;
    local array<PathPoint> Points;
    local PathPoint Point;

    Reason = SnapshotReason;
    if (!bSnapshotComplete || Soldier == none || `XWORLD == none
        || `XCOMHISTORY == none || Path.Length < 2
        || HorizonAITurns < 0 || HorizonAITurns > 0)
    {
        if (HorizonAITurns > 0)
            Reason = "future_patrol_route_unselected";
        return -1;
    }
    if (RemainingDetectors <= 0 || RemainingTiles < Path.Length || RemainingLOS <= 0)
    {
        Reason = "decision_budget";
        return -1;
    }
    if (Soldier.IsConcealed()
        && `XCOMHISTORY.GetSingleGameStateObjectForClass(
            class'XComGameState_ChallengeData', true) == none)
    {
        class'X2PathSolver'.static.GetPathPointsFromPath(Soldier, Path, Points);
        if (Points.Length < 2 || Points.Length > 256)
        {
            Reason = "traversal_unknown";
            return -1;
        }
        foreach Points(Point)
        {
            if (class'APX_ConcealmentPlanner'.static.IsDestructiveTraversal(
                name(string(Point.Traversal))))
            {
                Reason = "destructive_traversal";
                return 1;
            }
        }
    }
    Status = 0;
    for (Step = 0; Step < Path.Length; ++Step)
    {
        if (RemainingTiles <= 0)
        {
            Reason = "tile_budget";
            return -1;
        }
        --RemainingTiles;
        Tile = Path[Step];
        if (`XWORLD.IsTileOutOfRange(Tile))
        {
            Reason = "invalid_tile";
            return -1;
        }
        TilePosition = `XWORLD.GetPositionFromTileCoordinates(Tile);
        for (Index = 0; Index < KnownInteractives.Length; ++Index)
        {
            if (RemainingDetectors <= 0)
            {
                Reason = "detector_budget";
                return -1;
            }
            --RemainingDetectors;
            Ref = KnownInteractives[Index];
            Interactive = XComGameState_InteractiveObject(
                `XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
            if (Interactive == none)
            {
                Reason = "interactive_snapshot_changed";
                return -1;
            }
            if (Interactive.bRemovedFromPlay || Interactive.bHasBeenHacked
                || Interactive.DetectionRange <= 0.0)
                continue;
            DetectorPosition = `XWORLD.GetPositionFromTileCoordinates(Interactive.TileLocation);
            if (Soldier.IsConcealed()
                && VSizeSq(TilePosition - DetectorPosition) <= Square(Interactive.DetectionRange))
            {
                Reason = "interactive_detector";
                return 1;
            }
        }
        for (Index = 0; Index < KnownUnits.Length; ++Index)
        {
            if (RemainingDetectors <= 0)
            {
                Reason = "detector_budget";
                return -1;
            }
            --RemainingDetectors;
            Ref = KnownUnits[Index];
            Detector = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
            if (Detector == none || Detector.GetMyTemplate() == none)
            {
                Reason = "unit_snapshot_changed";
                return -1;
            }
            if (!Detector.IsAlive() || Detector.IsIncapacitated()
                || Detector.bRemovedFromPlay || Detector.GetMyTemplate().bIsCosmetic)
                continue;
            if (!Soldier.IsEnemyUnit(Detector) && !Detector.IsCivilian())
                continue;
            if (Soldier.IsConcealed() && !Soldier.UnitBreaksConcealment(Detector))
                continue;
            if (!Soldier.IsConcealed() && Detector.IsCivilian())
                continue;
            DetectorPosition = `XWORLD.GetPositionFromTileCoordinates(Detector.TileLocation);
            DistanceSq = VSizeSq(TilePosition - DetectorPosition);
            SightRange = `METERSTOUNITS(Detector.GetVisibilityRadius());
            if (SightRange < 0.0)
            {
                Reason = "visibility_radius_unknown";
                return -1;
            }
            if (Soldier.IsConcealed())
            {
                DetectRange = Soldier.GetConcealmentDetectionDistance(Detector);
                bIgnoresDistance = Detector.DoesUnitBreaksConcealmentIgnoringDistance();
                // Keep peek/geometry uncertainty near a known detector.
                if (!bIgnoresDistance && DistanceSq > Square(DetectRange + 200.0))
                    continue;
            }
            else if (DistanceSq > Square(SightRange + 200.0))
                continue;
            if (RemainingLOS <= 0)
            {
                Reason = "los_budget";
                return -1;
            }
            --RemainingLOS;
            bLOS = `XWORLD.CanSeeTileToTile(Detector.TileLocation, Tile, Visibility);
            if (!bLOS)
            {
                // A geometric false does not prove absence of gameplay peek LOS.
                Status = -1;
                Reason = "native_peek_unverified";
                continue;
            }
            if (!Soldier.IsConcealed())
            {
                Reason = "revealed_native_geometry_los";
                return 1;
            }
            bCovered = `XWORLD.GetCoverTypeForTarget(
                DetectorPosition, TilePosition, CoverAngle) != CT_None;
            if (ConcealedContactPossible(true, false, bCovered,
                DistanceSq, DetectRange, bIgnoresDistance))
            {
                Reason = "moving_soldier_detection";
                return 1;
            }
        }
    }
    if (Status == 0)
        Reason = "clear_current_snapshot_only";
    return Status;
}
