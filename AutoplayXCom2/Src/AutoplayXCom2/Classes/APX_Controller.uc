// One runtime-only actor per tactical HUD. Never serialized into a campaign.
class APX_Controller extends Actor config(AutoplayXCom2) dependson(X2GameRuleset);

var config name ToggleKey;
var config float DecisionInterval;
var config int MaxActionsPerTurn;
var config int MaxSameActionPerTurn;
var config bool AutoEndTurn;
var config bool AutoCompleteOwnedHacks;

var localized string StatusOff;
var localized string StatusActive;
var localized string StatusWaiting;
var localized string StatusModal;
var localized string StatusNoPlan;
var localized string StatusRejected;
var localized string StatusLimit;
var localized string StatusUnavailable;

struct ActionUse
{
    var int UnitID;
    var int AbilityID;
    var int TargetID;
    var int Count;
};

var private bool bEnabled;
var private bool bToggleWasDown;
var private float UntilDecision;
var private int LastTurn;
var private int ActionsThisTurn;
var private int MeaningfulActionsThisTurn;
var private bool bEndTurnRequested;
var private array<ActionUse> ActionUses;
var private string Status;
var private int OwnedAbilityID;
var private int OwnedSourceID;
var private UIHackingScreen OwnedHackScreen;
var private float HackScreenAge;

static function APX_Controller GetOrCreate()
{
    local WorldInfo World;
    local APX_Controller Existing;

    World = class'WorldInfo'.static.GetWorldInfo();
    if (World == none)
        return none;
    foreach World.AllActors(class'APX_Controller', Existing)
    {
        if (!Existing.bDeleteMe)
            return Existing;
    }
    return World.Spawn(class'APX_Controller');
}

simulated event PostBeginPlay()
{
    super.PostBeginPlay();
    LastTurn = INDEX_NONE;
    Status = StatusOff;
}

function bool IsEnabled()
{
    return bEnabled;
}

function string GetStatusText()
{
    return Status @ "[" $ string(ToggleKey) $ "]";
}

function Stop(string Reason)
{
    bEnabled = false;
    Status = StatusOff;
    UntilDecision = 0.0;
    OwnedAbilityID = 0;
    OwnedSourceID = 0;
    OwnedHackScreen = none;
    `log("Stopped:" @ Reason, , 'AutoplayXCom2');
}

function StopWithStatus(string Reason, string DisplayStatus)
{
    Stop(Reason);
    Status = DisplayStatus;
}

function Toggle()
{
    if (bEnabled)
    {
        Stop("User toggle");
        return;
    }
    // Also checked on every decision; never take over multiplayer or replays.
    if (`TACTICALRULES == none || !`TACTICALRULES.TacticalGameIsInPlay()
        || class'Engine'.static.GetEngine().IsMultiPlayerGame()
        || `REPLAY.bInReplay || `REPLAY.bInTutorial)
    {
        Status = StatusUnavailable;
        return;
    }
    bEnabled = true;
    UntilDecision = FMax(0.25, DecisionInterval);
    Status = StatusActive;
    // Enabling midway through a turn should not count earlier player actions.
    LastTurn = INDEX_NONE;
    `log("Enabled", , 'AutoplayXCom2');
}

simulated event Tick(float DeltaTime)
{
    local XComTacticalController PC;
    local bool bToggleDown;

    PC = XComTacticalController(WorldInfo.GetALocalPlayerController());
    if (PC == none || PC.PlayerInput == none)
        return;

    // Poll the physical key independently of the HUD. Stock HUD is hidden on
    // enemy/reflex turns. Escape stops without consuming the game's pause key.
    bToggleDown = PC.PlayerInput.PressedKeys.Find(ToggleKey) != INDEX_NONE;
    if (bToggleDown && !bToggleWasDown)
        Toggle();
    bToggleWasDown = bToggleDown;
    if (bEnabled && PC.PlayerInput.PressedKeys.Find('Escape') != INDEX_NONE)
        Stop("Escape");
    if (!bEnabled)
        return;

    if (`TACTICALRULES == none || !`TACTICALRULES.TacticalGameIsInPlay()
        || `TACTICALRULES.HasTacticalGameEnded())
    {
        Stop("Mission ended or world changed");
        return;
    }
    if (class'Engine'.static.GetEngine().IsMultiPlayerGame()
        || `REPLAY.bInReplay || `REPLAY.bInTutorial)
    {
        StopWithStatus("Unsupported game mode", StatusUnavailable);
        return;
    }
    if (WorldInfo.Pauser != none)
    {
        Status = StatusModal;
        return;
    }

    // A hack issued by us owns a blocking screen and visualization. Handle it
    // before the idle check; never dismiss unrelated dialogs or player hacks.
    if (HandleOwnedHack(DeltaTime))
        return;

    if (`SCREENSTACK == none || `SCREENSTACK.IsInputBlocked
        || UITacticalHUD(`SCREENSTACK.GetCurrentScreen()) == none)
    {
        Status = StatusModal;
        return;
    }
    if (!`TACTICALRULES.IsInState('TurnPhase_UnitActions')
        || `TACTICALRULES.GetUnitActionTeam() != eTeam_XCom
        || `TACTICALRULES.UnitActionPlayerIsAI()
        || !`TACTICALRULES.IsWaitingForNewStates()
        || !class'XComGameStateVisualizationMgr'.static.VisualizerIdleAndUpToDateWithHistory()
        || `TACTICALRULES.WaitingForVisualizer())
    {
        Status = StatusWaiting;
        return;
    }

    UntilDecision -= DeltaTime;
    if (UntilDecision > 0.0)
        return;
    UntilDecision = FMax(0.25, DecisionInterval);
    Status = StatusActive;
    MakeDecision(PC);
}

function bool HandleOwnedHack(float DeltaTime)
{
    local UIHackingScreen Hack;
    local int Index, BestReward;
    local float Chance, BestChance;

    if (`SCREENSTACK == none)
        return false;
    Hack = UIHackingScreen(`SCREENSTACK.GetCurrentScreen());
    if (Hack == none)
    {
        OwnedHackScreen = none;
        HackScreenAge = 0.0;
        return false;
    }
    Status = StatusModal;
    if (!AutoCompleteOwnedHacks || !Hack.bIsInited || Hack.OriginalContext == none
        || OwnedAbilityID == 0
        || Hack.OriginalContext.InputContext.AbilityRef.ObjectID != OwnedAbilityID
        || Hack.OriginalContext.InputContext.SourceObject.ObjectID != OwnedSourceID)
        return true;
    if (`SCREENSTACK.IsInputBlocked)
        return true;
    if (OwnedHackScreen != Hack)
    {
        OwnedHackScreen = Hack;
        HackScreenAge = 0.0;
    }
    HackScreenAge += DeltaTime;
    if (Hack.bWaitingForInput)
    {
        Hack.HackEnded();
        OwnedAbilityID = 0;
        OwnedSourceID = 0;
        OwnedHackScreen = none;
        return true;
    }
    if (Hack.m_hackStarted || Hack.HackRewards.Length < 3
        || Hack.FinalizeHackAbility == none
        || HackScreenAge < FMax(2.0, Hack.m_introDuration + 0.25))
        return true;

    // Use the displayed success chances only, never the hidden RNG result.
    // Objective hacks still apply their stock guaranteed mission effect.
    BestReward = INDEX_NONE;
    BestChance = -1.0;
    for (Index = 1; Index < Hack.HackRewards.Length; ++Index)
    {
        if (Hack.HackRewards[Index].bBadThing)
            continue;
        Chance = Hack.GetHackChance(Index);
        if (Chance > BestChance)
        {
            BestChance = Chance;
            BestReward = Index;
        }
    }
    if (BestReward != INDEX_NONE)
    {
        Hack.SelectedHackRewardOption = BestReward;
        Hack.RefreshPreviewState();
        Hack.InitiateHack();
    }
    return true;
}

function MakeDecision(XComTacticalController PC)
{
    local XComGameState_Unit UnitState, BestUnit;
    local XComGameState_Player PlayerState;
    local XComGameState_Ability Ability;
    local StateObjectReference PlayerRef;
    local AvailableAction Candidate, BestAction;
    local array<TTile> CandidatePath, BestPath;
    local int TargetIndex, BestTargetIndex;
    local float Score, BestScore;
    local bool bMove, bHavePlan, bSuccess;

    PlayerRef = `TACTICALRULES.GetCachedUnitActionPlayerRef();
    PlayerState = XComGameState_Player(`XCOMHISTORY.GetGameStateForObjectID(PlayerRef.ObjectID));
    if (PlayerState == none || PC.m_XGPlayer == none
        || PC.m_XGPlayer.ObjectID != PlayerRef.ObjectID)
        return;
    if (PlayerState.PlayerTurnCount != LastTurn)
    {
        LastTurn = PlayerState.PlayerTurnCount;
        ActionsThisTurn = 0;
        MeaningfulActionsThisTurn = 0;
        ActionUses.Length = 0;
        bEndTurnRequested = false;
    }
    if (bEndTurnRequested)
        return;
    if (ActionsThisTurn >= Max(1, MaxActionsPerTurn))
    {
        StopWithStatus("Per-turn action budget reached", StatusLimit);
        return;
    }

    BestScore = -10000.0;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', UnitState)
    {
        if (UnitState.GetAssociatedPlayerID() != PlayerRef.ObjectID
            || UnitState.GetTeam() != eTeam_XCom || !UnitState.IsAbleToAct()
            || UnitState.GetMyTemplate().bIsCosmetic)
            continue;

        if (class'APX_CombatPlanner'.static.ChooseAction(UnitState, Candidate, TargetIndex, Score)
            && Score > BestScore && CanUseAction(UnitState, Candidate, TargetIndex))
        {
            BestAction = Candidate;
            BestTargetIndex = TargetIndex;
            BestScore = Score;
            BestUnit = UnitState;
            bMove = false;
            bHavePlan = true;
        }
        if (class'APX_MissionPlanner'.static.ChooseInteraction(UnitState, Candidate, TargetIndex, Score)
            && Score > BestScore && CanUseAction(UnitState, Candidate, TargetIndex))
        {
            BestAction = Candidate;
            BestTargetIndex = TargetIndex;
            BestScore = Score;
            BestUnit = UnitState;
            bMove = false;
            bHavePlan = true;
        }
        CandidatePath.Length = 0;
        if (class'APX_MissionPlanner'.static.ChooseMove(UnitState, CandidatePath, Score)
            && Score > BestScore)
        {
            BestPath = CandidatePath;
            BestScore = Score;
            BestUnit = UnitState;
            bMove = true;
            bHavePlan = true;
        }
    }

    // Avoid burning whole turns on overwatch forever when no objective, attack
    // or useful move can be found. An unknown scripted objective needs a human.
    if ((!bHavePlan || BestScore <= 2.0) && MeaningfulActionsThisTurn == 0)
    {
        StopWithStatus("No constructive action or understood mission goal", StatusNoPlan);
        return;
    }
    if (!bHavePlan)
    {
        if (AutoEndTurn)
        {
            bEndTurnRequested = PC.PerformEndTurn(ePlayerEndTurnType_PlayerInput);
            if (!bEndTurnRequested)
                StopWithStatus("Engine rejected end turn", StatusRejected);
        }
        else
            StopWithStatus("Turn complete; automatic end turn is disabled", StatusNoPlan);
        return;
    }

    if (bMove)
    {
        OwnedAbilityID = 0;
        OwnedSourceID = 0;
        bSuccess = PC.GameStateMoveUnitSingle(XGUnit(BestUnit.GetVisualizer()), BestPath);
        `log("Move unit" @ BestUnit.ObjectID @ "tiles" @ BestPath.Length, , 'AutoplayXCom2');
    }
    else
    {
        // Cache ownership before submitting; the action may create a hack UI.
        OwnedAbilityID = BestAction.AbilityObjectRef.ObjectID;
        OwnedSourceID = BestUnit.ObjectID;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(OwnedAbilityID));
        bSuccess = class'XComGameStateContext_Ability'.static.ActivateAbility(BestAction, BestTargetIndex);
        RecordAction(BestUnit, BestAction, BestTargetIndex);
        `log("Ability" @ Ability.GetMyTemplateName() @ "unit" @ BestUnit.ObjectID
            @ "target index" @ BestTargetIndex, , 'AutoplayXCom2');
    }
    if (!bSuccess)
    {
        StopWithStatus("Engine rejected planned action", StatusRejected);
        return;
    }
    ++ActionsThisTurn;
    if (BestScore > 2.0)
        ++MeaningfulActionsThisTurn;
}

function bool CanUseAction(XComGameState_Unit UnitState, AvailableAction Action, int TargetIndex)
{
    local int TargetID, Index;
    if (TargetIndex != INDEX_NONE)
    {
        if (TargetIndex < 0 || TargetIndex >= Action.AvailableTargets.Length)
            return false;
        TargetID = Action.AvailableTargets[TargetIndex].PrimaryTarget.ObjectID;
    }
    for (Index = 0; Index < ActionUses.Length; ++Index)
    {
        if (ActionUses[Index].UnitID == UnitState.ObjectID
            && ActionUses[Index].AbilityID == Action.AbilityObjectRef.ObjectID
            && ActionUses[Index].TargetID == TargetID)
            return ActionUses[Index].Count < Max(1, MaxSameActionPerTurn);
    }
    return true;
}

function RecordAction(XComGameState_Unit UnitState, AvailableAction Action, int TargetIndex)
{
    local ActionUse Entry;
    local int Index;
    Entry.UnitID = UnitState.ObjectID;
    Entry.AbilityID = Action.AbilityObjectRef.ObjectID;
    if (TargetIndex != INDEX_NONE)
        Entry.TargetID = Action.AvailableTargets[TargetIndex].PrimaryTarget.ObjectID;
    for (Index = 0; Index < ActionUses.Length; ++Index)
    {
        if (ActionUses[Index].UnitID == Entry.UnitID
            && ActionUses[Index].AbilityID == Entry.AbilityID
            && ActionUses[Index].TargetID == Entry.TargetID)
        {
            ++ActionUses[Index].Count;
            return;
        }
    }
    Entry.Count = 1;
    ActionUses.AddItem(Entry);
}

defaultproperties
{
    ToggleKey=F8
    DecisionInterval=0.75
    MaxActionsPerTurn=128
    MaxSameActionPerTurn=8
    AutoEndTurn=true
    AutoCompleteOwnedHacks=true
    bEnabled=false
    bAlwaysTick=true
    bHidden=true
    bCollideActors=false
    bBlockActors=false
    RemoteRole=ROLE_None
}
