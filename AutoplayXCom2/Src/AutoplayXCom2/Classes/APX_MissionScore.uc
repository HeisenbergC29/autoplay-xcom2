// Read-only mission score for the HUD. Native points take precedence; ordinary
// unscored missions use the separately marked, partial installed-rate v3 profile.
class APX_MissionScore extends Object
    dependson(XComGameState, X2ChallengeModeDataStructures);

var localized string UnavailableLabel;

var private XComGameStateHistory CachedHistory;
var private int CachedStartIndex;
var private int CachedBattleID;
var private string CachedMissionType;
var private int CachedLadderID;
var private int CachedLadderIndex;
var private int CachedLadderRung;
var private int CachedChallengeID;
var private int CachedMaximum;
var private int CachedBaseline;
var private int LastHistoryIndex;
var private bool bHasMaximum;
var private bool bHasBaseline;
var private APX_LegacyObservedV3 ComparisonCounter;
var private int LastNativePoints;
var private bool bHasNativePoints;

// Score APIs can rebuild the history cache. A latent submission is not done
// until EndLatentUpdate has run and BuildingLatentGameState is cleared, even
// if IsDoingLatentSubmission has already become false.
static function bool CanQueryScoreHistory(bool bHasRules, bool bBuilding,
    bool bSubmitting)
{
    return bHasRules && !bBuilding && !bSubmitting;
}

static function bool CanReadScoreNow()
{
    local X2TacticalGameRuleset Rules;

    Rules = `TACTICALRULES;
    if (Rules == none)
        return false;
    return CanQueryScoreHistory(true, Rules.BuildingLatentGameState,
        Rules.IsDoingLatentSubmission());
}

function bool ReadNativeMissionPoints(out int Points)
{
    GetText();
    Points = LastNativePoints;
    return bHasNativePoints;
}

// GetTotalScore's native implementation sums these committed entries, skips
// None and the TotalScore rollup, and does not add LadderBonus. Unlike that
// aggregator, this read does not explicitly rebuild the history object cache.
static function int ChallengePointContribution(bool bNone, bool bTotal,
    int AddedPoints)
{
    if (bNone || bTotal)
        return 0;
    return AddedPoints;
}

function bool ReadChallengePoints(XComGameStateHistory History, out int Points)
{
    local XComGameState_ChallengeScore Score;
    local int Inspected;

    Points = 0;
    if (History == none || !CanReadScoreNow())
        return false;
    foreach History.IterateByClassType(class'XComGameState_ChallengeScore', Score)
    {
        if (++Inspected > 4096)
        {
            // Never expose a bounded subtotal as the complete native total.
            Points = 0;
            return false;
        }
        if (Score == none)
        {
            Points = 0;
            return false;
        }
        Points += ChallengePointContribution(Score.ScoringType == CMPT_None,
            Score.ScoringType == CMPT_TotalScore, Score.AddedPoints);
    }
    // With actual ChallengeData, no scoring entries is the native zero.
    return true;
}

function string UnavailableText()
{
    if (Len(UnavailableLabel) > 0)
        return UnavailableLabel;
    return "--";
}

static function int MissionPoints(int CumulativePoints, int StartingPoints)
{
    // Penalties can make a mission's current contribution negative.
    return CumulativePoints - StartingPoints;
}

static function string FormatPoints(int CurrentPoints, int MaximumPoints)
{
    return string(CurrentPoints) $ "/" $ string(MaximumPoints);
}

function Cleanup()
{
    if (ComparisonCounter != none)
    {
        ComparisonCounter.Cleanup();
        ComparisonCounter = none;
    }
}

function ResetCache()
{
    Cleanup();
    CachedHistory = none;
    CachedStartIndex = -1;
    CachedBattleID = 0;
    CachedMissionType = "";
    CachedLadderID = 0;
    CachedLadderIndex = 0;
    CachedLadderRung = 0;
    CachedChallengeID = 0;
    CachedMaximum = 0;
    CachedBaseline = 0;
    LastHistoryIndex = -1;
    bHasMaximum = false;
    bHasBaseline = false;
    bHasNativePoints = false;
    LastNativePoints = 0;
}

function bool CacheMatches(XComGameStateHistory History, int StartIndex,
    XComGameState_BattleData BattleData, XComGameState_LadderProgress Ladder,
    XComGameState_ChallengeData ChallengeData, int HistoryIndex)
{
    if (CachedHistory != History || CachedStartIndex != StartIndex)
        return false;
    if (CachedBattleID != BattleData.ObjectID || HistoryIndex < LastHistoryIndex)
        return false;
    if (CachedMissionType != BattleData.MapData.ActiveMission.sType)
        return false;
    if (Ladder != none)
        return CachedLadderID == Ladder.ObjectID
            && CachedLadderIndex == Ladder.LadderIndex
            && CachedLadderRung == Ladder.LadderRung;
    if (ChallengeData != none)
        return CachedLadderID == 0 && CachedChallengeID == ChallengeData.ObjectID;
    return CachedLadderID == 0 && CachedChallengeID == 0;
}

function RememberMission(XComGameStateHistory History, int StartIndex,
    XComGameState_BattleData BattleData, XComGameState_LadderProgress Ladder,
    XComGameState_ChallengeData ChallengeData)
{
    ResetCache();
    CachedHistory = History;
    CachedStartIndex = StartIndex;
    CachedBattleID = BattleData.ObjectID;
    CachedMissionType = BattleData.MapData.ActiveMission.sType;
    if (Ladder != none)
    {
        CachedLadderID = Ladder.ObjectID;
        CachedLadderIndex = Ladder.LadderIndex;
        CachedLadderRung = Ladder.LadderRung;
    }
    if (ChallengeData != none)
        CachedChallengeID = ChallengeData.ObjectID;
}

function bool ReadLadderBaseline(XComGameStateHistory History,
    XComGameState_BattleData BattleData, XComGameState_LadderProgress Ladder)
{
    local XComGameState_BattleData StartingBattle;
    local XComGameState_LadderProgress StartingLadder;

    // Use the actual tactical start, including after a mid-mission load.
    // Neither HUD creation nor pressing F8 establishes the mission baseline.
    StartingBattle = XComGameState_BattleData(History.GetGameStateForObjectID(
        BattleData.ObjectID, eReturnType_Reference, CachedStartIndex));
    StartingLadder = XComGameState_LadderProgress(History.GetGameStateForObjectID(
        Ladder.ObjectID, eReturnType_Reference, CachedStartIndex));
    if (StartingBattle == none || StartingLadder == none)
        return false;
    if (StartingBattle.ObjectID != BattleData.ObjectID)
        return false;
    if (StartingBattle.MapData.ActiveMission.sType != CachedMissionType)
        return false;
    if (StartingLadder.ObjectID != Ladder.ObjectID)
        return false;
    if (StartingLadder.LadderIndex != Ladder.LadderIndex || StartingLadder.LadderRung != Ladder.LadderRung)
        return false;
    CachedBaseline = StartingLadder.CumulativeScore;
    bHasBaseline = true;
    return true;
}

function string GetText()
{
    local XComGameStateHistory History;
    local XComGameState_BattleData BattleData;
    local XComGameState_LadderProgress Ladder;
    local XComGameState_ChallengeData ChallengeData;
    local XComChallengeModeManager Manager;
    local array<ScoreTableEntry> ScoreTable;
    local int HistoryIndex, StartIndex, CurrentPoints, MaximumPoints, ComparisonPoints;

    bHasNativePoints = false;
    LastNativePoints = 0;
    // All modes share this gate, including comparison and recorder reads.
    // Return unknown, never a cached value presented as a fresh native score.
    if (!CanReadScoreNow())
        return UnavailableText();
    History = `XCOMHISTORY;
    if (History == none)
    {
        ResetCache();
        return UnavailableText();
    }
    HistoryIndex = History.GetCurrentHistoryIndex();
    StartIndex = History.FindStartStateIndex();
    BattleData = XComGameState_BattleData(History.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    if (BattleData == none || StartIndex < 0 || HistoryIndex < StartIndex)
    {
        ResetCache();
        return UnavailableText();
    }
    Ladder = XComGameState_LadderProgress(History.GetSingleGameStateObjectForClass(
        class'XComGameState_LadderProgress', true));
    ChallengeData = XComGameState_ChallengeData(History.GetSingleGameStateObjectForClass(
        class'XComGameState_ChallengeData', true));
    if (!CacheMatches(History, StartIndex, BattleData, Ladder, ChallengeData, HistoryIndex))
        RememberMission(History, StartIndex, BattleData, Ladder, ChallengeData);
    LastHistoryIndex = HistoryIndex;
    if (Ladder == none && ChallengeData == none)
    {
        if (ComparisonCounter == none)
            ComparisonCounter = new(self) class'APX_LegacyObservedV3';
        ComparisonPoints = ComparisonCounter.GetObservedScore();
        if (!ComparisonCounter.IsReady())
            return UnavailableText();
        // Tilde distinguishes the partial comparison from native game points.
        // Never invent a maximum from unseen enemies or optional objectives.
        return "~" $ string(ComparisonPoints) $ "/" $ UnavailableText();
    }
    Manager = `CHALLENGEMODE_MGR;
    if (Manager == none)
        return UnavailableText();

    if (Ladder != none)
    {
        if (!bHasBaseline && !ReadLadderBaseline(History, BattleData, Ladder))
            return UnavailableText();
        CurrentPoints = MissionPoints(Ladder.CumulativeScore, CachedBaseline);
        if (!bHasMaximum)
        {
            // Same native total as the stock Legacy scoring dialog. Only its
            // aggregate reaches the HUD; no hidden enemy state is inspected.
            MaximumPoints = Manager.GetChallengeMaxPossibleScoreTable(ScoreTable);
        }
    }
    else
    {
        // Preserve native integer awards/penalties without calling the native
        // aggregator that force-rebuilds history (the v27 crash call chain).
        if (!ReadChallengePoints(History, CurrentPoints))
            return UnavailableText();
        if (!bHasMaximum)
            MaximumPoints = Manager.GetMaxChallengeScore();
    }
    LastNativePoints = CurrentPoints;
    bHasNativePoints = true;
    if (!bHasMaximum)
    {
        if (MaximumPoints <= 0)
            // A valid current score does not depend on knowing its ceiling.
            // Leave the maximum uncached so a later native read can fill it.
            return string(CurrentPoints) $ "/" $ UnavailableText();
        CachedMaximum = MaximumPoints;
        bHasMaximum = true;
    }
    return FormatPoints(CurrentPoints, CachedMaximum);
}

defaultproperties
{
    CachedStartIndex=-1
    LastHistoryIndex=-1
}
