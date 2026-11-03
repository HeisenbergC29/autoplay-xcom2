// Read-only native mission score for the HUD. Never supplies tactical targets
// or awards points; ordinary unscored missions have no native value to show.
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

function ResetCache()
{
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
    return false;
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
    local int HistoryIndex, StartIndex, CurrentPoints, MaximumPoints;

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
    if (Ladder == none && ChallengeData == none)
    {
        ResetCache();
        return UnavailableText();
    }
    if (!CacheMatches(History, StartIndex, BattleData, Ladder, ChallengeData, HistoryIndex))
        RememberMission(History, StartIndex, BattleData, Ladder, ChallengeData);
    LastHistoryIndex = HistoryIndex;
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
        // The stock Challenge summary uses this native score/maximum pair.
        // Require actual ChallengeData before interpreting zero as a score.
        CurrentPoints = Manager.GetTotalScore();
        if (!bHasMaximum)
            MaximumPoints = Manager.GetMaxChallengeScore();
    }
    if (!bHasMaximum)
    {
        if (MaximumPoints <= 0)
            return UnavailableText();
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
