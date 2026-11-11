// Read-only estimate of dangerous exploding cover near a proposed move tile.
// Uses stock destruction extents and visible enemy primary weapon templates.
// No enemy AP, ammo, aim rolls, cooldowns or hidden AI actions are inspected.
class APX_ExplosiveCoverKnowledge extends Object;

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
            break;
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
        if (Enemy == none || !Enemy.IsAlive() || Enemy.IsIncapacitated()
            || Enemy.bRemovedFromPlay || Enemy.IsMeleeOnly()
            || !UnitState.IsEnemyUnit(Enemy))
            continue;
        // The native equipped weapon template is a potential capability, not
        // a promise that the enemy can attack this cover this turn.
        if (class'APX_EnemyKnowledge'.static.PrimaryWeaponMeanDamage(Enemy) > 0.0
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
    local array<XComDestructibleActor> Seen;
    local array<TTile> BlastTiles;
    local XComDestructibleActor Destructible;
    local Actor Candidate;
    local TTile ProbeTile, BlastTile;
    local int Probe, Index, Sampled;
    local float Damage, HealthFraction;

    if (UnitState == none || `XWORLD == none || `XCOMHISTORY == none
        || !HasRelevantRangedThreat(UnitState, Tile, VisibleEnemies))
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
            Destructible = XComDestructibleActor(Candidate);
            if (Destructible == none || Seen.Find(Destructible) != INDEX_NONE)
                continue;
            Seen.AddItem(Destructible);
            if (++Sampled > 16)
                return 0.0; // Unknown; do not pretend every cover is explosive.
            if (!Destructible.HasRadialDamage())
                continue;
            Damage = float(Destructible.GetDestroyedDamagePreview());
            if (Damage <= 0.0)
                continue;
            BlastTiles.Length = 0;
            Destructible.GetRadialDamageTiles(BlastTiles);
            if (BlastTiles.Length == 0 || BlastTiles.Length > 96)
                continue;
            foreach BlastTiles(BlastTile)
            {
                // Native extents can include a soldier near an exploding car.
                // The preview is a risk, not proof that the car will explode.
                if (BlastTile == Tile)
                    return ExplosiveCoverPenalty(Damage, true, HealthFraction);
            }
        }
    }
    return 0.0;
}
