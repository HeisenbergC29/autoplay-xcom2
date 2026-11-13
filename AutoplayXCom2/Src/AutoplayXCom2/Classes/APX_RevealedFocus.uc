// Soft, bounded, read-only contact choice for revealed ranged XCOM squads.
// Native visibility, ability availability, LOS and action costs remain final.
class APX_RevealedFocus extends Object config(AutoplayXCom2);

var config bool EnableRevealedGroupFocus;
var config int MaxGroupsPerDecision;
var config int MaxMembersPerDecision;
var config int MaxFriendlyStatesPerDecision;
var config int MaxSquadSize;

static function bool CanFocus(bool bEnabled, bool bFullIntel,
    bool bConcealed, bool bDeadline, bool bBleeding, int RangedSoldiers)
{
    return bEnabled && bFullIntel && !bConcealed && !bDeadline
        && !bBleeding && RangedSoldiers >= 2;
}

static function float PodPriority(float Distance, int Members, bool bPrevious)
{
    if (Distance < 0.0 || Members < 1)
        return -10000.0;
    if (bPrevious)
        return 38.0 - Distance - FMax(0.0, float(Members - 3)) * 2.0;
    return 29.0 - Distance - FMax(0.0, float(Members - 3)) * 2.0;
}

static function float MemberPriority(float Distance, float HealthFraction)
{
    if (Distance < 0.0)
        return -10000.0;
    return -Distance + FClamp(1.0 - HealthFraction, 0.0, 1.0) * 4.0;
}

// A small boost selects a known native-legal shot on the shared opponent.
// Never award points to an illegal attack, melee, AoE or an inaccessible tile.
static function float LegalShotFocusBonus(bool bInPod, bool bPrimary,
    bool bNativeLegal, bool bRanged, float HealthFraction)
{
    if (!bInPod || !bNativeLegal || !bRanged)
        return 0.0;
    if (bPrimary)
        return 14.0 + FClamp(1.0 - HealthFraction, 0.0, 1.0) * 8.0;
    return 5.0;
}

// No selected enemy is an instruction to attack: it only changes soft score
// after the original combat candidate and route checks admit an action.
static function bool SelectContact(int PlayerID, int PreviousGroupID,
    out int GroupID, out int PrimaryTargetID, out TTile PrimaryTile,
    out int LivingRanged, out float DistanceToPod, out int PodMembers)
{
    local XComGameState_Unit Friend, Enemy, Representative;
    local XComGameState_AIGroup Group;
    local StateObjectReference Member;
    local array<int> SeenIDs;
    local float CenterX, CenterY, DistSq, Dist, NearestDist;
    local float BestGroupScore, GroupScore, PrimaryScore, MemberScore;
    local int FriendStates, GroupCount, ReferenceCount, Members;
    local int CandidatePrimaryID;
    local TTile CandidateTile;

    GroupID = 0;
    PrimaryTargetID = 0;
    LivingRanged = 0;
    PodMembers = 0;
    DistanceToPod = -1.0;
    if (!default.EnableRevealedGroupFocus
        || !class'APX_FullIntel'.default.EnableFullIntel
        || PlayerID <= 0 || `XCOMHISTORY == none || `XWORLD == none
        || `TACTICALRULES == none
        || PlayerID != `TACTICALRULES.GetLocalClientPlayerObjectID())
        return false;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Friend)
    {
        // Count rejected states too; partial enumeration would skew centroid.
        if (++FriendStates > Clamp(default.MaxFriendlyStatesPerDecision, 1, 256))
            return false;
        if (Friend == none || Friend.GetMyTemplate() == none
            || Friend.GetTeam() != eTeam_XCom
            || Friend.GetAssociatedPlayerID() != PlayerID
            || Friend.GetMyTemplateName() == 'BerserkerMP'
            || Friend.IsMeleeOnly()
            || !class'APX_SquadPlanner'.static.IsLocalSoldier(Friend, PlayerID)
            || `XWORLD.IsTileOutOfRange(Friend.TileLocation))
            continue;
        if (++LivingRanged > Clamp(default.MaxSquadSize, 2, 16))
            return false;
        if (Representative == none)
            Representative = Friend;
        CenterX += float(Friend.TileLocation.X);
        CenterY += float(Friend.TileLocation.Y);
    }
    if (LivingRanged < 2 || Representative == none)
        return false;
    CenterX /= float(LivingRanged);
    CenterY /= float(LivingRanged);

    BestGroupScore = -10000.0;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_AIGroup', Group)
    {
        if (++GroupCount > Clamp(default.MaxGroupsPerDecision, 1, 32))
            return false;
        if (Group == none || Group.bRemoved || Group.m_arrMembers.Length == 0)
            continue;
        if (ReferenceCount + Group.m_arrMembers.Length >
            Clamp(default.MaxMembersPerDecision, 1, 256))
            return false;
        ReferenceCount += Group.m_arrMembers.Length;
        NearestDist = 100000000.0;
        Members = 0;
        CandidatePrimaryID = 0;
        PrimaryScore = -10000.0;
        SeenIDs.Length = 0;
        foreach Group.m_arrMembers(Member)
        {
            if (Member.ObjectID <= 0 || SeenIDs.Find(Member.ObjectID) != INDEX_NONE)
                continue;
            SeenIDs.AddItem(Member.ObjectID);
            Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Member.ObjectID));
            if (Enemy == none || Enemy.GetMyTemplate() == none
                || !Enemy.IsAlive() || Enemy.IsIncapacitated()
                || Enemy.bRemoved || Enemy.bRemovedFromPlay
                || Enemy.IsCivilian() || Enemy.GetMyTemplate().bIsCosmetic
                || Enemy.GetMyTemplateName() == 'HostileVIPCivilian'
                || !Representative.IsEnemyUnit(Enemy)
                || `XWORLD.IsTileOutOfRange(Enemy.TileLocation)
                || class'APX_CombatPlanner'.static.IsReclaimableControlledSquadmate(
                    Representative, Enemy))
                continue;
            ++Members;
            DistSq = Square(float(Enemy.TileLocation.X) - CenterX)
                + Square(float(Enemy.TileLocation.Y) - CenterY);
            Dist = Sqrt(DistSq);
            NearestDist = FMin(NearestDist, Dist);
            MemberScore = MemberPriority(Dist, Enemy.GetCurrentStat(eStat_HP)
                / FMax(1.0, Enemy.GetMaxStat(eStat_HP)));
            if (MemberScore > PrimaryScore)
            {
                PrimaryScore = MemberScore;
                CandidatePrimaryID = Enemy.ObjectID;
                CandidateTile = Enemy.TileLocation;
            }
        }
        if (CandidatePrimaryID <= 0)
            continue;
        GroupScore = PodPriority(NearestDist, Members, Group.ObjectID == PreviousGroupID);
        if (GroupScore > BestGroupScore)
        {
            BestGroupScore = GroupScore;
            GroupID = Group.ObjectID;
            PrimaryTargetID = CandidatePrimaryID;
            PrimaryTile = CandidateTile;
            DistanceToPod = NearestDist;
            PodMembers = Members;
        }
    }
    return PrimaryTargetID > 0;
}
