// Runtime-only diagnostic observer. Never changes state, rolls RNG or issues orders.
// Records only the local squad and contacts visible to that player.
class APX_MissionRecorder extends Object config(AutoplayXCom2)
    dependson(X2GameRuleset, XComGameState_Ability, X2TacticalGameRulesetDataStructures);

var config int MaxRecords;
var config int MaxHistoryFramesPerObserve;

struct RecordedUnit
{
    var int UnitID;
    var string Snapshot;
    var string Abilities;
};

var private array<RecordedUnit> Units;
var private array<int> PreviousVisibleIDs;
var private int OwnerPlayerID;
var private int Sequence;
var private int Decision;
var private int HistoryCursor;
var private string SessionID;
var private string LastPhase;
var private string PreparedChoiceFields;
var private bool bStarted;
var private bool bFinished;
var private bool bLimitReported;
var private bool bEndPending;
var private int LastEndHistory;

function string Safe(string Value)
{
    Value = Repl(Value, "|", "/");
    Value = Repl(Value, Chr(13), " ");
    Value = Repl(Value, Chr(10), " ");
    return Value;
}

function Emit(string EventName, string Fields)
{
    if (!bStarted || bFinished)
        return;
    if (Sequence >= Clamp(MaxRecords, 100, 100000))
    {
        if (!bLimitReported)
        {
            ++Sequence;
            `log("APXREC|v=1|session=" $ SessionID $ "|seq=" $ Sequence
                $ "|event=limit|decision=" $ Decision $ "|max_records=" $ MaxRecords, true, 'AutoplayXCom2');
            bLimitReported = true;
        }
        return;
    }
    ++Sequence;
    `log("APXREC|v=1|session=" $ SessionID $ "|seq=" $ Sequence
        $ "|event=" $ Safe(EventName) $ "|decision=" $ Decision $ Fields, true, 'AutoplayXCom2');
}

function Start(int PlayerID)
{
    local XComGameState_BattleData BattleData;
    local int Year, Month, DayOfWeek, Day, Hour, Minute, Second, Millisecond;
    local string Mission;

    if (bStarted || `XCOMHISTORY == none)
        return;
    OwnerPlayerID = PlayerID;
    GetSystemTime(Year, Month, DayOfWeek, Day, Hour, Minute, Second, Millisecond);
    SessionID = string(Year) $ "-" $ Month $ "-" $ Day $ "_" $ Hour
        $ "-" $ Minute $ "-" $ Second $ "-" $ Millisecond $ "_" $ PlayerID;
    HistoryCursor = `XCOMHISTORY.GetCurrentHistoryIndex();
    BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
        class'XComGameState_BattleData', true));
    Mission = "unknown";
    if (BattleData != none)
        Mission = BattleData.MapData.ActiveMission.sType;
    bStarted = true;
    Emit("start", "|player=" $ PlayerID $ "|mission=" $ Safe(Mission)
        $ "|difficulty=" $ `TacticalDifficultySetting $ "|history=" $ HistoryCursor
        $ "|revision=mission-report-v4");
    Observe("start");
}

function Marker(string Kind, string Details)
{
    Emit("marker", "|kind=" $ Safe(Kind) $ "|details=" $ Safe(Details));
}

function BeginDecision()
{
    PreparedChoiceFields = "";
    ++Decision;
    Emit("decision", "");
    Observe("decision");
}

function int UnitIndex(int UnitID)
{
    local int Index;
    local RecordedUnit Entry;
    Index = Units.Find('UnitID', UnitID);
    if (Index != INDEX_NONE)
        return Index;
    Entry.UnitID = UnitID;
    Units.AddItem(Entry);
    return Units.Length - 1;
}

function RecordUnit(XComGameState_Unit UnitState, bool bFriendly, bool bForce)
{
    local XComGameState_Item Weapon;
    local int Index, ActionPoints, Ammo;
    local string Fields, Scope;

    if (UnitState == none || UnitState.GetMyTemplate() == none
        || UnitState.GetMyTemplate().bIsCosmetic)
        return;
    ActionPoints = -1;
    Ammo = -1;
    Scope = "visible_enemy";
    if (bFriendly)
    {
        Scope = "friendly";
        ActionPoints = UnitState.NumActionPoints();
        Weapon = UnitState.GetItemInSlot(eInvSlot_PrimaryWeapon);
        if (Weapon != none)
            Ammo = Weapon.Ammo;
    }
    Fields = "|id=" $ UnitState.ObjectID $ "|scope=" $ Scope
        $ "|template=" $ UnitState.GetMyTemplateName()
        $ "|x=" $ UnitState.TileLocation.X $ "|y=" $ UnitState.TileLocation.Y
        $ "|z=" $ UnitState.TileLocation.Z $ "|hp=" $ UnitState.GetCurrentStat(eStat_HP)
        $ "|max_hp=" $ UnitState.GetMaxStat(eStat_HP)
        $ "|shield=" $ UnitState.GetCurrentStat(eStat_ShieldHP)
        $ "|ap=" $ ActionPoints $ "|ammo=" $ Ammo
        $ "|alive=" $ UnitState.IsAlive() $ "|incapacitated=" $ UnitState.IsIncapacitated()
        $ "|removed=" $ UnitState.bRemovedFromPlay;
    if (bFriendly)
        Fields $= "|concealed=" $ UnitState.IsConcealed()
            $ "|bleeding_out=" $ UnitState.IsBleedingOut()
            $ "|panicked=" $ UnitState.IsPanicked()
            $ "|mind_controlled=" $ UnitState.IsMindControlled();
    Index = UnitIndex(UnitState.ObjectID);
    if (bForce || Units[Index].Snapshot != Fields)
    {
        Emit("unit", Fields);
        Units[Index].Snapshot = Fields;
    }
    if (bFriendly && UnitState.IsAbleToAct())
        RecordAvailability(UnitState, Index);
}

function RecordAvailability(XComGameState_Unit UnitState, int Index)
{
    local GameRulesCache_Unit Cache;
    local AvailableAction Action;
    local XComGameState_Ability Ability;
    local string Fingerprint, Fields;

    if (`TACTICALRULES == none
        || !`TACTICALRULES.GetGameRulesCache_Unit(UnitState.GetReference(), Cache))
        return;
    foreach Cache.AvailableActions(Action)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
            Action.AbilityObjectRef.ObjectID));
        if (Ability != none)
            Fingerprint $= string(Ability.GetMyTemplateName()) $ ":" $ Action.AvailableCode
                $ ":" $ Action.bInputTriggered $ ":" $ Action.bFreeAim
                $ ":" $ Action.AvailableTargets.Length $ ";";
    }
    if (Units[Index].Abilities == Fingerprint)
        return;
    Units[Index].Abilities = Fingerprint;
    foreach Cache.AvailableActions(Action)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
            Action.AbilityObjectRef.ObjectID));
        if (Ability == none)
            continue;
        Fields = "|unit=" $ UnitState.ObjectID $ "|ability=" $ Ability.GetMyTemplateName()
            $ "|code=" $ Action.AvailableCode $ "|input=" $ Action.bInputTriggered
            $ "|freeaim=" $ Action.bFreeAim $ "|targets=" $ Action.AvailableTargets.Length
            $ "|handler=" $ AbilityHandler(UnitState, Ability.GetMyTemplateName());
        Emit("ability", Fields);
    }
}

// This describes the planner responsible for evaluating an action, not a
// promise that every target or item variant is safe and will be selected.
function string AbilityHandler(XComGameState_Unit UnitState, name AbilityName)
{
    if (class'APX_CombatPlanner'.static.GetActionReason(UnitState, AbilityName)
        != "outside_combat_allowlist")
        return "combat";
    if (AbilityName == 'StandardMove')
        return "movement";
    if (AbilityName == 'ThrowGrenade' || AbilityName == 'LaunchGrenade')
        return "grenade";
    if (AbilityName == 'Evac' || AbilityName == 'PlaceEvacZone')
        return "evacuation";
    if (class'APX_MissionPlanner'.static.IsObjectiveAbility(AbilityName)
        || AbilityName == 'Interact' || AbilityName == 'Interact_OpenChest'
        || AbilityName == 'Hack' || AbilityName == 'Hack_Chest'
        || AbilityName == 'Knockout' || AbilityName == 'CarryUnit')
        return "mission";
    return "unhandled";
}

function Observe(string Phase)
{
    local XComGameState_Unit UnitState;
    local XComGameState_Player PlayerState;
    local array<StateObjectReference> VisibleEnemies;
    local array<int> VisibleIDs;
    local StateObjectReference EnemyRef;
    local string PhaseState;
    local int Index;

    if (!bStarted || bFinished || bLimitReported || `XCOMHISTORY == none)
        return;
    PlayerState = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(OwnerPlayerID));
    PhaseState = "|phase=" $ Safe(Phase);
    if (PlayerState != none)
        PhaseState $= "|turn=" $ PlayerState.PlayerTurnCount;
    if (`TACTICALRULES != none)
        PhaseState $= "|active_team=" $ string(`TACTICALRULES.GetUnitActionTeam());
    if (PhaseState != LastPhase)
    {
        Emit("phase", PhaseState);
        LastPhase = PhaseState;
    }
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', UnitState)
    {
        if (UnitState.GetAssociatedPlayerID() == OwnerPlayerID
            && UnitState.GetTeam() == eTeam_XCom)
            RecordUnit(UnitState, true, false);
    }
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
        OwnerPlayerID, VisibleEnemies);
    foreach VisibleEnemies(EnemyRef)
    {
        UnitState = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (UnitState == none || UnitState.GetMyTemplate().bIsCosmetic)
            continue;
        VisibleIDs.AddItem(UnitState.ObjectID);
        RecordUnit(UnitState, false, PreviousVisibleIDs.Find(UnitState.ObjectID) == INDEX_NONE);
    }
    for (Index = 0; Index < PreviousVisibleIDs.Length; ++Index)
    {
        if (VisibleIDs.Find(PreviousVisibleIDs[Index]) == INDEX_NONE)
            Emit("visibility_lost", "|id=" $ PreviousVisibleIDs[Index]);
    }
    PreviousVisibleIDs = VisibleIDs;
    RecordResults();
}

function bool IsOwnUnitAt(int ObjectID, int HistoryIndex)
{
    local XComGameState_Unit UnitState;
    UnitState = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        ObjectID, eReturnType_Reference, HistoryIndex));
    return UnitState != none && UnitState.GetAssociatedPlayerID() == OwnerPlayerID;
}

function RecordResults()
{
    local XComGameState HistoryState;
    local XComGameStateContext_Ability Context;
    local array<StateObjectReference> VisibleEnemies, BeforeActionEnemies;
    local StateObjectReference TargetRef;
    local int EndIndex, SourceID, TargetID, TargetIndex;
    local bool bOwnAction, bOwnTarget, bSourceVisible;
    local string AbilityName, SourceScope;

    EndIndex = Min(`XCOMHISTORY.GetCurrentHistoryIndex(),
        HistoryCursor + Clamp(MaxHistoryFramesPerObserve, 16, 2048));
    while (HistoryCursor < EndIndex && !bLimitReported)
    {
        ++HistoryCursor;
        HistoryState = `XCOMHISTORY.GetGameStateFromHistory(HistoryCursor);
        if (HistoryState == none)
            continue;
        Context = XComGameStateContext_Ability(HistoryState.GetContext());
        if (Context == none)
            continue;
        SourceID = Context.InputContext.SourceObject.ObjectID;
        TargetID = Context.InputContext.PrimaryTarget.ObjectID;
        bOwnAction = IsOwnUnitAt(SourceID, HistoryCursor);
        bOwnTarget = IsOwnUnitAt(TargetID, HistoryCursor);
        foreach Context.InputContext.MultiTargets(TargetRef)
            bOwnTarget = bOwnTarget || IsOwnUnitAt(TargetRef.ObjectID, HistoryCursor);
        // Never dump unrelated enemy actions or the positions of unseen units.
        if (!bOwnAction && !bOwnTarget)
            continue;
        VisibleEnemies.Length = 0;
        BeforeActionEnemies.Length = 0;
        class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
            OwnerPlayerID, VisibleEnemies, HistoryCursor);
        if (bOwnAction && HistoryCursor > 0)
            class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
                OwnerPlayerID, BeforeActionEnemies, HistoryCursor - 1);
        bSourceVisible = bOwnAction || VisibleEnemies.Find('ObjectID', SourceID) != INDEX_NONE;
        SourceScope = "unseen_other";
        if (bOwnAction)
            SourceScope = "friendly";
        else if (bSourceVisible)
            SourceScope = "visible_enemy";
        AbilityName = "unseen_attack";
        if (bSourceVisible)
            AbilityName = string(Context.InputContext.AbilityTemplateName);
        else
            SourceID = 0;
        // Preserve friendly targets; redact enemy target IDs no longer visible.
        if (!IsOwnUnitAt(TargetID, HistoryCursor)
            && VisibleEnemies.Find('ObjectID', TargetID) == INDEX_NONE)
        {
            if (BeforeActionEnemies.Find('ObjectID', TargetID) == INDEX_NONE)
                TargetID = 0;
        }
        if (Context.InterruptionStatus == eInterruptionStatus_Interrupt)
        {
            Emit("interrupted", "|history=" $ HistoryCursor $ "|source=" $ SourceID
                $ "|source_scope=" $ SourceScope
                $ "|target=" $ TargetID $ "|ability=" $ Safe(AbilityName));
            continue;
        }
        Emit("result", "|history=" $ HistoryCursor $ "|source=" $ SourceID
            $ "|source_scope=" $ SourceScope
            $ "|target=" $ TargetID $ "|ability=" $ Safe(AbilityName)
            $ "|hit=" $ string(Context.ResultContext.HitResult)
            $ "|chance=" $ Context.ResultContext.CalculatedHitChance
            $ "|interruption=" $ string(Context.InterruptionStatus)
            $ TargetHealthFields(TargetID, HistoryCursor));
        for (TargetIndex = 0; TargetIndex < Context.InputContext.MultiTargets.Length; ++TargetIndex)
        {
            TargetID = Context.InputContext.MultiTargets[TargetIndex].ObjectID;
            if (!IsOwnUnitAt(TargetID, HistoryCursor)
                && VisibleEnemies.Find('ObjectID', TargetID) == INDEX_NONE
                && BeforeActionEnemies.Find('ObjectID', TargetID) == INDEX_NONE)
                continue;
            if (TargetIndex >= Context.ResultContext.MultiTargetHitResults.Length)
                continue;
            Emit("result_target", "|history=" $ HistoryCursor $ "|source=" $ SourceID
                $ "|source_scope=" $ SourceScope
                $ "|target=" $ TargetID $ "|ability=" $ Safe(AbilityName)
                $ "|target_index=" $ TargetIndex
                $ "|hit=" $ string(Context.ResultContext.MultiTargetHitResults[TargetIndex])
                $ TargetHealthFields(TargetID, HistoryCursor));
        }
    }
}

function string TargetHealthFields(int TargetID, int HistoryIndex)
{
    local XComGameState_Unit BeforeUnit, AfterUnit;

    if (TargetID <= 0 || HistoryIndex <= 0)
        return "";
    BeforeUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        TargetID, eReturnType_Reference, HistoryIndex - 1));
    AfterUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
        TargetID, eReturnType_Reference, HistoryIndex));
    if (BeforeUnit == none || AfterUnit == none)
        return "";
    return "|target_hp_before=" $ BeforeUnit.GetCurrentStat(eStat_HP)
        $ "|target_hp_after=" $ AfterUnit.GetCurrentStat(eStat_HP)
        $ "|target_shield_before=" $ BeforeUnit.GetCurrentStat(eStat_ShieldHP)
        $ "|target_shield_after=" $ AfterUnit.GetCurrentStat(eStat_ShieldHP);
}

function string ActionFields(XComGameState_Unit UnitState, string Kind,
    AvailableAction Action, int TargetIndex, float Score)
{
    local XComGameState_Ability Ability;
    local XComGameState_Unit TargetUnit;
    local ShotBreakdown Breakdown;
    local WeaponDamageValue MinDamage, MaxDamage;
    local int TargetID, Chance, AllowsShield;
    local string AbilityName, Reason;

    Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(
        Action.AbilityObjectRef.ObjectID));
    AbilityName = "unknown";
    Reason = "unknown";
    Chance = -1;
    if (Ability != none)
    {
        AbilityName = string(Ability.GetMyTemplateName());
        Reason = class'APX_CombatPlanner'.static.GetActionReason(UnitState, Ability.GetMyTemplateName());
    }
    if (TargetIndex >= 0 && TargetIndex < Action.AvailableTargets.Length)
    {
        TargetID = Action.AvailableTargets[TargetIndex].PrimaryTarget.ObjectID;
        TargetUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(TargetID));
        if (Ability != none && Ability.GetMyTemplate() != none && TargetUnit != none
            && Ability.GetMyTemplate().AbilityToHitCalc != none)
        {
            Chance = Ability.GetShotBreakdown(Action.AvailableTargets[TargetIndex], Breakdown);
            Ability.GetDamagePreview(Action.AvailableTargets[TargetIndex].PrimaryTarget,
                MinDamage, MaxDamage, AllowsShield);
        }
    }
    return "|kind=" $ Safe(Kind) $ "|unit=" $ UnitState.ObjectID
        $ "|ability=" $ Safe(AbilityName) $ "|reason=" $ Safe(Reason) $ "|target=" $ TargetID
        $ "|target_index=" $ TargetIndex $ "|score=" $ Score $ "|chance=" $ Chance
        $ "|raw_min_damage=" $ MinDamage.Damage $ "|raw_max_damage=" $ MaxDamage.Damage;
}

function CandidateAction(XComGameState_Unit UnitState, string Kind,
    AvailableAction Action, int TargetIndex, float Score)
{
    Emit("candidate", ActionFields(UnitState, Kind, Action, TargetIndex, Score));
}

function string MoveFields(XComGameState_Unit UnitState, const out array<TTile> Path, float Score)
{
    local array<StateObjectReference> VisibleEnemies;
    local TTile Destination;
    local float CurrentRisk, CandidateRisk, SupportScore;

    if (Path.Length == 0)
        return "|kind=move|unit=" $ UnitState.ObjectID $ "|score=" $ Score $ "|path_tiles=0";
    Destination = Path[Path.Length - 1];
    class'APX_MissionPlanner'.static.GetVisibleThreats(UnitState, VisibleEnemies);
    CurrentRisk = class'APX_MissionPlanner'.static.ExposureRisk(UnitState, UnitState.TileLocation, VisibleEnemies);
    CandidateRisk = class'APX_MissionPlanner'.static.ExposureRisk(UnitState, Destination, VisibleEnemies);
    SupportScore = class'APX_MissionPlanner'.static.SquadPositionScore(UnitState, Destination);
    return "|kind=move|unit=" $ UnitState.ObjectID $ "|score=" $ Score
        $ "|path_tiles=" $ Path.Length $ "|x=" $ Path[Path.Length - 1].X
        $ "|y=" $ Path[Path.Length - 1].Y $ "|z=" $ Path[Path.Length - 1].Z
        $ "|ap_before=" $ UnitState.NumActionPoints() $ "|visible_threats=" $ VisibleEnemies.Length
        $ "|current_risk=" $ CurrentRisk $ "|candidate_risk=" $ CandidateRisk
        $ "|support_score=" $ SupportScore;
}

function CandidateMove(XComGameState_Unit UnitState, const out array<TTile> Path, float Score)
{
    Emit("candidate", MoveFields(UnitState, Path, Score));
}

// Capture the preview before dispatch. Activation can replace the global rules
// cache or consume ammunition; its post-action preview is not decision evidence.
function PrepareChosenAction(XComGameState_Unit UnitState, AvailableAction Action,
    int TargetIndex, float Score)
{
    PreparedChoiceFields = ActionFields(UnitState, "action", Action, TargetIndex, Score);
}

function PrepareChosenMove(XComGameState_Unit UnitState, const out array<TTile> Path, float Score)
{
    PreparedChoiceFields = MoveFields(UnitState, Path, Score);
}

function ChosenAction(XComGameState_Unit UnitState, AvailableAction Action,
    int TargetIndex, float Score, bool bAccepted)
{
    if (PreparedChoiceFields == "")
        PreparedChoiceFields = "|kind=action|unit=" $ UnitState.ObjectID
            $ "|score=" $ Score $ "|preview_missing=true";
    Emit("chosen", PreparedChoiceFields $ "|accepted=" $ bAccepted);
}

function ChosenMove(XComGameState_Unit UnitState, const out array<TTile> Path,
    float Score, bool bAccepted)
{
    if (PreparedChoiceFields == "")
        PreparedChoiceFields = "|kind=move|unit=" $ UnitState.ObjectID
            $ "|score=" $ Score $ "|preview_missing=true";
    Emit("chosen", PreparedChoiceFields $ "|accepted=" $ bAccepted);
}

function Finish(string Reason)
{
    local XComGameState_BattleData BattleData;
    local string Outcome;
    local int PendingHistory;

    if (!bStarted || bFinished)
        return;
    if (`XCOMHISTORY != none)
    {
        PendingHistory = Max(0, `XCOMHISTORY.GetCurrentHistoryIndex() - HistoryCursor);
        BattleData = XComGameState_BattleData(`XCOMHISTORY.GetSingleGameStateObjectForClass(
            class'XComGameState_BattleData', true));
    }
    // HasTacticalGameEnded can become true while the last action and winner
    // are still being committed. The controller retries Finish on later ticks.
    // Wait for authoritative battle data instead of freezing a partial snapshot
    // and treating the default false bLocalPlayerWon value as a loss.
    if (Reason == "tactical_game_ended"
        && (BattleData == none || BattleData.VictoriousPlayer.ObjectID == 0))
    {
        if (!bEndPending || LastEndHistory != HistoryCursor + PendingHistory)
        {
            bEndPending = true;
            LastEndHistory = HistoryCursor + PendingHistory;
            Observe("ending");
            Emit("ending", "|reason=" $ Safe(Reason) $ "|outcome=unknown"
                $ "|history=" $ LastEndHistory);
        }
        return;
    }
    Observe("finish");
    if (`XCOMHISTORY != none)
        PendingHistory = Max(0, `XCOMHISTORY.GetCurrentHistoryIndex() - HistoryCursor);
    Outcome = "unknown";
    if (BattleData != none && BattleData.VictoriousPlayer.ObjectID != 0)
        Outcome = BattleData.bLocalPlayerWon ? "win" : "loss";
    Emit("end", "|reason=" $ Safe(Reason) $ "|outcome=" $ Outcome
        $ "|history=" $ HistoryCursor $ "|history_pending=" $ PendingHistory);
    bFinished = true;
}
