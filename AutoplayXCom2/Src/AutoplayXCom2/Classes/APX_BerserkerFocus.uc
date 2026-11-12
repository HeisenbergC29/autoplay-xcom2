// Bounded, read-only squad focus for the BerserkerMP SabotageTransmitter.
// Group membership and current active positions are full-intel observations,
// not future AI routes or permission to attack outside the native cache.
class APX_BerserkerFocus extends Object config(AutoplayXCom2);

var config bool EnableBerserkerGroupFocus;
var config int OpeningContactTurns;
var config int MinimumContactTimerTurns;
var config float MaximumOpeningContactDistance;
var config int MaxGroupsPerDecision;
var config int MaxMemberRefsPerDecision;
var config int MaxFriendlyUnitsPerDecision;

// An old group gets a soft bonus, but a substantially nearer threat can win.
// This score never bypasses action, movement, hazard or formation legality.
static function float GroupPriority(float Distance, int Members, bool bRetained)
{
    if (Members <= 0 || Distance < 0.0)
        return -10000.0;
    if (bRetained)
        return 48.0 - Distance - FMax(0.0, float(Members - 3)) * 2.0;
    return 36.0 - Distance - FMax(0.0, float(Members - 3)) * 2.0;
}

// Spend only a bounded early window confronting an actual nearby pod. If
// the real native timer cannot be read, preserve the proven X4/relay route.
// After native X4 completion, the mandatory sweep always takes precedence.
static function bool ShouldUseContactGoal(bool bEnabled, bool bPlantCompleted,
    int TimerTurns, int PlayerTurn, float TargetDistance, int LivingFriendlies,
    int MaxOpeningTurns, int MinTimerTurns, float MaxDistance)
{
    if (!bEnabled || LivingFriendlies <= 0 || TargetDistance < 0.0)
        return false;
    if (bPlantCompleted)
        return true;
    return LivingFriendlies >= 3
        && TimerTurns >= MinTimerTurns
        && PlayerTurn >= 1 && PlayerTurn <= MaxOpeningTurns
        && TargetDistance <= MaxDistance;
}

// A focus target is merely a soft preference for a NATIVE-LEGAL attack.
// Do not turn a low-HP last defender into a sacrificial attacker.
static function float FocusAttackBonus(bool bInFocus, bool bOpeningContact,
    float OwnHealthFraction, float EnemyHealthFraction)
{
    if (!bInFocus || OwnHealthFraction < 0.55)
        return 0.0;
    if (bOpeningContact)
        return 34.0 + FClamp(1.0 - EnemyHealthFraction, 0.0, 1.0) * 14.0;
    return 16.0 + FClamp(1.0 - EnemyHealthFraction, 0.0, 1.0) * 10.0;
}

// A real, native-legal relay remains an option during the opening contact.
// It should not automatically beat a safe focused punch while plenty of
// real timer turns remain. The cap is not an AP/ability modification.
static function float ContactRelayScore(float NativeScore, bool bOpeningContact)
{
    if (!bOpeningContact || NativeScore <= 0.0)
        return NativeScore;
    return FMin(NativeScore, 26.0);
}

// This is the stock UI timer's public remaining-turn counter, not a guessed
// deadline from a score label or a hidden enemy decision.
static function int ReadActiveTimerTurns()
{
    local XComGameState_UITimer TimerState;

    if (`XCOMHISTORY == none)
        return -1;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_UITimer', TimerState)
    {
        if (TimerState != none && !TimerState.bRemoved && TimerState.IsTimer
            && TimerState.ShouldShow && !TimerState.IsSuspended())
            return TimerState.TimerValue;
    }
    return -1;
}

// The entire squad shares ONE centroid for target selection. No member of
// an enemy AIGroup is presumed visible for attack just because its position
// is available to this permitted full-intel planning calculation.
static function bool SelectSquadContact(int PlayerID, int PreviousGroupID,
    out int GroupID, out int TargetID, out TTile TargetTile,
    out float TargetDistance, out int LivingFriendlies, out int GroupMembers)
{
    local XComGameState_Unit Friend, Enemy, Representative;
    local XComGameState_AIGroup Group;
    local StateObjectReference Ref;
    local float CenterX, CenterY, BestScore, Distance, DistanceSq;
    local float NearestDistanceSq, CandidateScore;
    local int GroupsChecked, RefsChecked, Members, CandidateID;
    local TTile CandidateTile;
    local float CandidateDistance;

    GroupID = 0;
    TargetID = 0;
    GroupMembers = 0;
    TargetDistance = -1.0;
    LivingFriendlies = 0;
    if (!default.EnableBerserkerGroupFocus
        || !class'APX_FullIntel'.default.EnableFullIntel
        || `XCOMHISTORY == none || `XWORLD == none || PlayerID <= 0)
        return false;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', Friend)
    {
        if (LivingFriendlies >= Clamp(default.MaxFriendlyUnitsPerDecision, 1, 16))
            break;
        if (Friend == none || Friend.GetTeam() != eTeam_XCom
            || Friend.GetAssociatedPlayerID() != PlayerID
            || Friend.GetMyTemplateName() != 'BerserkerMP'
            || !Friend.IsAlive() || Friend.IsIncapacitated()
            || Friend.bRemoved || Friend.bRemovedFromPlay)
            continue;
        if (Representative == none)
            Representative = Friend;
        CenterX += float(Friend.TileLocation.X);
        CenterY += float(Friend.TileLocation.Y);
        ++LivingFriendlies;
    }
    if (Representative == none || LivingFriendlies <= 0)
        return false;
    CenterX /= float(LivingFriendlies);
    CenterY /= float(LivingFriendlies);
    BestScore = -10000.0;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_AIGroup', Group)
    {
        if (++GroupsChecked > Clamp(default.MaxGroupsPerDecision, 1, 32))
            break;
        if (Group == none || Group.bRemoved || Group.m_arrMembers.Length == 0
            || Group.m_arrMembers.Length > 24)
            continue;
        if (RefsChecked + Group.m_arrMembers.Length >
            Clamp(default.MaxMemberRefsPerDecision, 1, 256))
            break;
        RefsChecked += Group.m_arrMembers.Length;
        Members = 0;
        CandidateID = 0;
        NearestDistanceSq = 100000000.0;
        foreach Group.m_arrMembers(Ref)
        {
            Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(Ref.ObjectID));
            if (Enemy == none || Enemy.GetMyTemplate() == none
                || !Enemy.IsAlive() || Enemy.IsIncapacitated()
                || Enemy.bRemoved || Enemy.bRemovedFromPlay || Enemy.IsCivilian()
                || Enemy.GetMyTemplate().bIsCosmetic
                || Enemy.GetMyTemplateName() == 'HostileVIPCivilian'
                || !Representative.IsEnemyUnit(Enemy)
                || `XWORLD.IsTileOutOfRange(Enemy.TileLocation))
                continue;
            ++Members;
            DistanceSq = (float(Enemy.TileLocation.X) - CenterX)
                * (float(Enemy.TileLocation.X) - CenterX)
                + (float(Enemy.TileLocation.Y) - CenterY)
                * (float(Enemy.TileLocation.Y) - CenterY);
            if (DistanceSq < NearestDistanceSq)
            {
                NearestDistanceSq = DistanceSq;
                CandidateID = Enemy.ObjectID;
                CandidateTile = Enemy.TileLocation;
            }
        }
        if (CandidateID <= 0)
            continue;
        CandidateDistance = Sqrt(NearestDistanceSq);
        CandidateScore = GroupPriority(CandidateDistance, Members,
            Group.ObjectID == PreviousGroupID);
        if (CandidateScore > BestScore)
        {
            BestScore = CandidateScore;
            GroupID = Group.ObjectID;
            TargetID = CandidateID;
            TargetTile = CandidateTile;
            TargetDistance = CandidateDistance;
            GroupMembers = Members;
        }
    }
    return TargetID > 0;
}
