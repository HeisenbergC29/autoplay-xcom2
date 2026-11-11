// Read-only estimate of dangerous exploding cover near a proposed move tile.
// Uses stock destruction extents and known enemy weapon/ability templates.
// No enemy AP, ammo, aim rolls, cooldowns or hidden AI actions are inspected.
class APX_ExplosiveCoverKnowledge extends Object;

static function bool BlastExtentsContain(int X, int Y, int Z,
    int MinX, int MinY, int MinZ, int MaxX, int MaxY, int MaxZ)
{
    return X >= MinX && X <= MaxX && Y >= MinY && Y <= MaxY
        && Z >= MinZ && Z <= MaxZ;
}

static function bool FutureBlastStillPossible(int Health, bool bDestroyed,
    bool bDead, bool bDestructionStarted)
{
    return Health > 0 && !bDestroyed && !bDead && !bDestructionStarted;
}

static function int RemainingInspectionBudget(int RemainingChecks)
{
    return Max(0, RemainingChecks - 1);
}

// The controller owns one budget across all unit movement searches. Unknown
// endpoints do not receive a cheaper score than the largest known penalty.
static function float InspectRiskAtTile(XComGameState_Unit UnitState, TTile Tile,
    const out array<StateObjectReference> VisibleEnemies, out int RemainingCoverChecks)
{
    if (UnitState == none || `XWORLD == none || `XCOMHISTORY == none)
        return 0.0;
    if (VisibleEnemies.Length == 0 && !class'APX_FullIntel'.default.EnableFullIntel)
        return 0.0;
    if (RemainingCoverChecks <= 0)
        return 42.0;
    RemainingCoverChecks = RemainingInspectionBudget(RemainingCoverChecks);
    return RiskAtTile(UnitState, Tile, VisibleEnemies);
}

static function float ExplosiveCoverPenalty(float NativeUnitDamage,
    bool bArmedRangedEnemyNearby, float HealthFraction)
{
    if (!bArmedRangedEnemyNearby || NativeUnitDamage <= 0.0)
        return 0.0;
    return FMin(42.0, 12.0 + FMin(18.0, NativeUnitDamage * 2.0)
        + (1.0 - FClamp(HealthFraction, 0.0, 1.0)) * 12.0);
}

static function bool HasRelevantRangedThreat(
    XComGameState_Unit UnitState, TTile Position,
    const out array<StateObjectReference> VisibleEnemies)
{
    local XComGameState_Unit Enemy;
    local StateObjectReference Ref;
    local int Checked;

    foreach VisibleEnemies(Ref)
    {
        if (++Checked > 32)
            return true; // Uninspected contacts may still threaten scenery.
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
        if (Enemy == none || !Enemy.IsAlive() || Enemy.IsIncapacitated()
            || Enemy.bRemovedFromPlay || Enemy.IsMeleeOnly()
            || !UnitState.IsEnemyUnit(Enemy))
            continue;
        // The native equipped weapon template is a potential capability, not
        // a promise that the enemy can attack this cover this turn.
        if ((class'APX_EnemyKnowledge'.static.PrimaryWeaponMeanDamage(Enemy) > 0.0
                || (class'APX_EnemyKnowledge'.static.CapabilityFlags(Enemy)
                    & 2) != 0)
            && Abs(Enemy.TileLocation.X - Position.X) <= 22
            && Abs(Enemy.TileLocation.Y - Position.Y) <= 22
            && Abs(Enemy.TileLocation.Z - Position.Z) <= 2)
            return true;
    }
    return false;
}

static function float RiskAtTile(XComGameState_Unit UnitState, TTile Tile,
    const out array<StateObjectReference> VisibleEnemies)
{
    local array<Actor> Actors;
    local array<StateObjectReference> ThreatRefs;
    local array<Actor> Seen;
    local XComDestructibleActor Destructible;
    local XComDestructibleActor_Action_RadialDamage RadialEvent;
    local Actor Candidate;
    local TTile ProbeTile, MinTile, MaxTile;
    local int Probe, Index, SampledActors, SampledEvents;
    local float Damage, HealthFraction, WorstRisk;

    if (UnitState == none || `XWORLD == none || `XCOMHISTORY == none)
        return 0.0;
    ThreatRefs = VisibleEnemies;
    if (class'APX_FullIntel'.default.EnableFullIntel)
        class'APX_FullIntel'.static.GetKnownEnemies(UnitState, ThreatRefs);
    if (!HasRelevantRangedThreat(UnitState, Tile, ThreatRefs))
        return 0.0;

    HealthFraction = UnitState.GetCurrentStat(eStat_HP)
        / FMax(1.0, UnitState.GetMaxStat(eStat_HP));
    // Sample only the destination and its four cardinal neighbors, not every
    // object on the whole map. A car immediately beside cover is included.
    for (Probe = 0; Probe < 5; ++Probe)
    {
        ProbeTile = Tile;
        switch (Probe)
        {
        case 1: ++ProbeTile.X; break;
        case 2: --ProbeTile.X; break;
        case 3: ++ProbeTile.Y; break;
        case 4: --ProbeTile.Y; break;
        }
        if (`XWORLD.IsTileOutOfRange(ProbeTile))
            continue;
        Actors = `XWORLD.GetActorsOnTile(ProbeTile, true);
        foreach Actors(Candidate)
        {
            // Count actor entries, including duplicates, to bound iteration
            // as well as the expensive event inspections across all probes.
            if (SampledActors >= 16)
                return 42.0;
            ++SampledActors;
            if (Candidate == none || Seen.Find(Candidate) != INDEX_NONE)
                continue;
            Seen.AddItem(Candidate);
            Destructible = XComDestructibleActor(Candidate);
            if (Destructible == none)
                continue;
            if (!FutureBlastStillPossible(Destructible.Health,
                Destructible.IsInState('_Destroyed'), Destructible.IsInState('Dead'),
                Destructible.IsInState('_DestructionStarted')))
                continue;
            // GetRadialDamageTiles builds an unbounded UC tile array. Read
            // the same stock event extents directly without enumerating it.
            if (Destructible.DestroyedEvents.Length > 32 - SampledEvents)
                return 42.0;
            Damage = 0.0;
            for (Index = 0; Index < Destructible.DestroyedEvents.Length; ++Index)
            {
                if (SampledEvents >= 32)
                    return 42.0;
                ++SampledEvents;
                RadialEvent = XComDestructibleActor_Action_RadialDamage(
                    Destructible.DestroyedEvents[Index].Action);
                if (RadialEvent == none || RadialEvent.UnitDamage <= 0.0)
                    continue;
                RadialEvent.GetBlastExtents(MinTile, MaxTile);
                if (BlastExtentsContain(Tile.X, Tile.Y, Tile.Z,
                    MinTile.X, MinTile.Y, MinTile.Z, MaxTile.X, MaxTile.Y, MaxTile.Z))
                    Damage += RadialEvent.UnitDamage;
            }
            // Sum only nominal event damage whose extents contain this tile;
            // do not add different cars as though all must detonate together.
            WorstRisk = FMax(WorstRisk,
                ExplosiveCoverPenalty(Damage, true, HealthFraction));
        }
    }
    return WorstRisk;
}
