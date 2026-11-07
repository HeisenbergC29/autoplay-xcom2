// Read-only concealment-risk estimate for prospective player movement paths.
// This does NOT grant targets, alter the history, or force movement.
class APX_ConcealmentPlanner extends Object config(AutoplayXCom2)
    dependson(X2GameRulesetVisibilityDataStructures, XGTacticalGameCoreNativeBase);

var config int MaxPathTilesToInspect;
var config int MaxDetectorsToInspect;
var config float ConcealmentRiskPenalty;

static function bool DestructiveTraversalBreaksConcealment(bool bIsChallenge,
    bool bConcealed, bool bDestructive)
{
    return bConcealed && bDestructive && !bIsChallenge;
}

static function float RouteConcealmentPenalty(bool bConcealed,
    bool bAtRisk, bool bUrgent, float ConfiguredPenalty)
{
    if (!bConcealed || !bAtRisk)
        return 0.0;
    if (bUrgent)
        return FMin(4.0, FMax(0.0, ConfiguredPenalty));
    return FMax(0.0, ConfiguredPenalty);
}

static function bool IsDestructiveTraversal(name TraversalName)
{
    return TraversalName == 'eTraversal_BreakWindow'
        || TraversalName == 'eTraversal_KickDoor'
        || TraversalName == 'eTraversal_BreakWall'
        || TraversalName == 'eTraversal_Phasing';
}

static function bool DetectedOnTile(bool bClearLOS, float DistanceSquared,
    float SightRadius, float DetectionRadius, bool bIgnoresDetectionDistance)
{
    if (!bClearLOS || DistanceSquared > SightRadius * SightRadius)
        return false;
    return bIgnoresDetectionDistance
        || DistanceSquared <= DetectionRadius * DetectionRadius;
}

static function bool CanIgnoreInteractiveDetectors(XComGameState_Unit Soldier)
{
    local name RetainName;

    if (Soldier == none)
        return false;
    foreach class'X2AbilityTemplateManager'.default.AbilityRetainsConcealmentVsInteractives(RetainName)
    {
        if (Soldier.HasSoldierAbility(RetainName))
            return true;
    }
    return false;
}

// Returns true for a detected risk, NOT a proven concealment break.
// A capped or unavailable sample is "uncertain": downstream uses a soft
// preference and native ability/path checks always remain authoritative.
static function bool PathRisksRevealing(XComGameState_Unit Soldier,
    const out array<TTile> Path, out string Reason)
{
    local array<PathPoint> Points;
    local PathPoint Point;
    local array<StateObjectReference> VisibleObjects, KnownEnemies;
    local StateObjectReference Ref;
    local XComGameState_Unit Detector;
    local XComGameState_InteractiveObject Interactive;
    local GameRulesCache_VisibilityInfo Visibility;
    local TTile Tile;
    local vector TilePosition, DetectorPosition;
    local float SightRadius, DetectRadius;
    local int Step, Index, Checks, Limit, PathLimit;
    local bool bChallenge, bIgnoreInteractives, bSampleClipped;

    Reason = "none";
    if (Soldier == none || !Soldier.IsConcealed() || Path.Length < 2)
        return false;
    if (`XWORLD == none || `XCOMHISTORY == none)
    {
        Reason = "world_unavailable";
        return true;
    }
    PathLimit = Clamp(default.MaxPathTilesToInspect, 2, 256);
    Limit = Clamp(default.MaxDetectorsToInspect, 1, 256);
    if (Path.Length > PathLimit)
    {
        Reason = "path_sample_limit";
        return true;
    }

    bChallenge = `XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_ChallengeData', true) != none;
    bIgnoreInteractives = CanIgnoreInteractiveDetectors(Soldier);
    if (!bChallenge)
    {
        class'X2PathSolver'.static.GetPathPointsFromPath(Soldier, Path, Points);
        // Unknown traversal geometry gets a penalty, not a hard veto.
        if (Points.Length < 2)
        {
            Reason = "path_traversal_unknown";
            return true;
        }
        foreach Points(Point)
        {
            if (DestructiveTraversalBreaksConcealment(bChallenge, true,
                IsDestructiveTraversal(name(string(Point.Traversal)))))
            {
                Reason = "destructive_traversal";
                return true;
            }
        }
    }

    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleObjectsForPlayer(
        Soldier.GetAssociatedPlayerID(), VisibleObjects, , -1, true);
    // The user chose omniscient enemy positions. Geometry may be queried
    // for route planning, but native target lists are unaffected.
    class'APX_FullIntel'.static.GetKnownEnemies(Soldier, KnownEnemies);
    bSampleClipped = VisibleObjects.Length > Limit
        || KnownEnemies.Length > Limit;

    for (Step = 1; Step < Path.Length; ++Step)
    {
        Tile = Path[Step];
        if (`XWORLD.IsTileOutOfRange(Tile))
        {
            Reason = "invalid_tile";
            return true;
        }
        TilePosition = `XWORLD.GetPositionFromTileCoordinates(Tile);
        for (Index = 0; Index < Min(VisibleObjects.Length, Limit); ++Index)
        {
            if (++Checks > Limit * PathLimit)
            {
                Reason = "detector_sample_limit";
                return true;
            }
            Ref = VisibleObjects[Index];
            if (!bIgnoreInteractives)
            {
                Interactive = XComGameState_InteractiveObject(
                    `XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
                if (Interactive != none && !Interactive.bRemovedFromPlay
                    && !Interactive.bHasBeenHacked && Interactive.DetectionRange > 0.0)
                {
                    DetectorPosition = `XWORLD.GetPositionFromTileCoordinates(
                        Interactive.TileLocation);
                    if (VSizeSq(TilePosition - DetectorPosition)
                        <= Square(Interactive.DetectionRange))
                    {
                        Reason = "interactive_detector";
                        return true;
                    }
                }
            }
            Detector = XComGameState_Unit(
                `XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
            if (Detector != none && IsDetectingUnit(Soldier, Detector, Tile, Visibility))
            {
                Reason = Detector.IsCivilian() ? "visible_civilian" : "visible_unit";
                return true;
            }
        }
        if (class'APX_FullIntel'.default.EnableFullIntel)
        {
            for (Index = 0; Index < Min(KnownEnemies.Length, Limit); ++Index)
            {
                if (++Checks > Limit * PathLimit)
                {
                    Reason = "detector_sample_limit";
                    return true;
                }
                Detector = XComGameState_Unit(
                    `XCOMHISTORY.GetGameStateForObjectID(KnownEnemies[Index].ObjectID));
                if (Detector != none
                    && IsDetectingUnit(Soldier, Detector, Tile, Visibility))
                {
                    Reason = "known_enemy";
                    return true;
                }
            }
        }
    }
    if (bSampleClipped)
    {
        Reason = "detector_sample_limit";
        return true; // Conservative estimate; move is penalized, not blocked.
    }
    return false;
}

static function bool IsDetectingUnit(XComGameState_Unit Soldier,
    XComGameState_Unit Detector, TTile Tile,
    out GameRulesCache_VisibilityInfo Visibility)
{
    local float SightRadius, DetectRadius;
    local vector TilePosition, DetectorPosition;

    if (!Detector.IsAlive() || Detector.bRemovedFromPlay
        || Detector.GetMyTemplate() == none
        || Detector.GetMyTemplate().bIsCosmetic
        || !Soldier.UnitBreaksConcealment(Detector))
        return false;

    // Cheap distance cull before the expensive native voxel LOS query.
    // The two-tile buffer keeps this estimate conservative around peek tiles.
    SightRadius = `METERSTOUNITS(Detector.GetVisibilityRadius());
    TilePosition = `XWORLD.GetPositionFromTileCoordinates(Tile);
    DetectorPosition = `XWORLD.GetPositionFromTileCoordinates(Detector.TileLocation);
    if (VSizeSq(TilePosition - DetectorPosition) > Square(SightRadius + 200.0)
        || !`XWORLD.CanSeeTileToTile(Detector.TileLocation, Tile, Visibility))
        return false;

    DetectRadius = Soldier.GetConcealmentDetectionDistance(Detector);
    return DetectedOnTile(true,
        Visibility.DefaultTargetDist, SightRadius, DetectRadius,
        Detector.DoesUnitBreaksConcealmentIgnoringDistance());
}
