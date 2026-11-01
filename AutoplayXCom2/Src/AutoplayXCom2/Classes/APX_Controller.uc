// One runtime-only actor per tactical HUD. Never serialized into a campaign.
class APX_Controller extends Actor config(AutoplayXCom2) dependson(X2GameRuleset);

var config name ToggleKey;
var config float DecisionInterval;
var config int MaxActionsPerTurn;
var config int MaxSameActionPerTurn;
var config bool AutoEndTurn;
var config bool AutoCompleteOwnedHacks;
var config bool ExploreUnseenMap;
var config bool AutoPlaceEvac;
var config bool UseExplosiveGrenades;

var localized string StatusOff;
var localized string StatusActive;
var localized string StatusWaiting;
var localized string StatusModal;
var localized string StatusGamePaused;
var localized string StatusHUDWaiting;
var localized string StatusInputBlocked;
var localized string StatusTargeting;
var localized string StatusDialog;
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

struct VisitedPosition
{
    var int UnitID;
    var TTile Tile;
};

var private bool bEnabled;
var private bool bToggleWasDown;
var private float UntilDecision;
var private int LastTurn;
var private int ActionsThisTurn;
var private int MeaningfulActionsThisTurn;
var private bool bEndTurnRequested;
var private array<ActionUse> ActionUses;
var private array<VisitedPosition> VisitedPositions;
var private string Status;
var private name LastWaitReason;
var private string LastWaitDetails;
var private int OwnedAbilityID;
var private int OwnedSourceID;
var private XComGameStateContext_Ability OwnedActionContext;
var private UIHackingScreen OwnedHackScreen;
var private float HackScreenAge;
var private APX_ExplorationPlanner ExplorationPlanner;
var private APX_AreaAttackPlanner AreaPlanner;

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

function StopAutoplay(string Reason, optional bool bPreservePendingHack = false)
{
    bEnabled = false;
    Status = StatusOff;
    UntilDecision = 0.0;
    LastWaitReason = '';
    LastWaitDetails = "";
    // A user pause may happen before the hack UI has even appeared. Keep only
    // the exact submitted context, so resuming cannot claim a later manual hack
    // that happens to reuse the same soldier and ability IDs.
    if (!bPreservePendingHack)
    {
        OwnedAbilityID = 0;
        OwnedSourceID = 0;
        OwnedActionContext = none;
    }
    OwnedHackScreen = none;
    if (AreaPlanner != none)
        AreaPlanner.Cleanup();
    `log("Stopped:" @ Reason, , 'AutoplayXCom2');
}

function StopWithStatus(string Reason, string DisplayStatus)
{
    StopAutoplay(Reason);
    Status = DisplayStatus;
}

function Toggle()
{
    if (bEnabled)
    {
        StopAutoplay("User toggle", true);
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
    LastWaitReason = '';
    LastWaitDetails = "";
    UntilDecision = FMax(0.25, DecisionInterval);
    Status = StatusActive;
    // Enabling midway through a turn should not count earlier player actions.
    LastTurn = INDEX_NONE;
    `log("Enabled", , 'AutoplayXCom2');
}

// Stock WOTC keeps these passive screens ABOVE UITacticalHUD in its stack.
// In particular, InitUIScreensComplete pushes UITurnOverlay and then
// UISpecialMissionHUD. The raw top screen therefore need not be the HUD.
// Never allow an arbitrary non-consuming screen: menus can evaluate input too.
function bool IsPassiveTacticalOverlay(UIScreen Screen)
{
    return UITurnOverlay(Screen) != none
        || UISpecialMissionHUD(Screen) != none
        || UIChallengeModeHUD(Screen) != none
        || UIUnitFlagManager(Screen) != none
        || UIEnemyArrowContainer(Screen) != none
        || UITooltipMgr(Screen) != none
        || UIEventNotices(Screen) != none;
}

function name GetUIBlockReason(XComTacticalController PC, out string Details)
{
    local XComPresentationLayer Pres;
    local UIScreenStack Stack;
    local UITacticalHUD HUD;
    local UIScreen Screen;
    local int Index;

    Details = "";
    Pres = XComPresentationLayer(PC.Pres);
    if (Pres == none || Pres.Get2DMovie() == none)
        return 'HUD';
    Stack = Pres.ScreenStack;
    HUD = Pres.GetTacticalHUD();
    if (Stack == none || HUD == none)
        return 'HUD';
    if (Stack.IsInputBlocked)
        return 'InputBlocked';
    // Dialogs live on the movie, not necessarily in ScreenStack. Wait for
    // non-modal confirmations as well as those already covered by IsBusy().
    if (Pres.Get2DMovie().DialogBox != none
        && Pres.Get2DMovie().DialogBox.ShowingDialog())
        return 'Dialog';
    if (PC.IsBusy())
        return 'UIBusy';
    if (!HUD.bIsInited || !HUD.bIsVisible || HUD.bIsRemoved
        || HUD.bIsPendingRemoval || HUD.m_kAbilityHUD == none)
        return 'HUD';

    // Inspect only the part of the stack above this actual HUD instance.
    // Unknown visible/opening screens block, even if they do not consume input.
    for (Index = 0; Index < Stack.Screens.Length; ++Index)
    {
        Screen = Stack.Screens[Index];
        if (Screen == HUD)
        {
            // Target selection is inside the HUD, not a separate screen.
            if (HUD.GetTargetingMethod() != none)
                return 'Targeting';
            return '';
        }
        if (Screen == none || Screen.bIsRemoved)
            continue;
        if (Screen.bIsInited && !Screen.bIsVisible)
            continue;
        if (IsPassiveTacticalOverlay(Screen))
        {
            // Match stock input readiness while an overlay is still loading.
            if (!Screen.bIsInited)
            {
                Details = string(Screen.Class.Name);
                return 'HUD';
            }
            if (!Screen.ConsumesInput())
                continue;
        }
        Details = string(Screen.Class.Name);
        return 'Menu';
    }
    // A detached HUD reference cannot authorize issuing an order.
    return 'HUD';
}

function string DescribeUIStack(XComTacticalController PC)
{
    local XComPresentationLayer Pres;
    local UIScreenStack Stack;
    local UIScreen Screen;
    local string Result;
    local int Index;

    if (PC == none || PC.Pres == none || PC.Pres.ScreenStack == none)
        return "no presentation / stack";
    Stack = PC.Pres.ScreenStack;
    Result = "InputBlocked=" $ string(Stack.IsInputBlocked);
    Pres = XComPresentationLayer(PC.Pres);
    if (Pres != none && Pres.Get2DMovie() != none)
    {
        Result @= "PCBusy=" $ string(PC.IsBusy())
            @ "movieInit=" $ string(Pres.Get2DMovie().bIsInited)
            @ "modalScreens=" $ string(Pres.Get2DMovie().NumModalScreens);
        if (Pres.Get2DMovie().DialogBox != none)
            Result @= "dialog=" $ string(Pres.Get2DMovie().DialogBox.ShowingDialog());
    }
    for (Index = 0; Index < Min(16, Stack.Screens.Length); ++Index)
    {
        Screen = Stack.Screens[Index];
        if (Screen == none)
            continue;
        Result $= " | " $ string(Index) $ ":" $ string(Screen.Class.Name)
            @ "visible=" $ string(Screen.bIsVisible)
            @ "init=" $ string(Screen.bIsInited)
            @ "removed=" $ string(Screen.bIsRemoved)
            @ "input=" $ string(Screen.InputState);
    }
    return Result;
}

function SetWaitStatus(name Reason, string DisplayStatus, optional string Details)
{
    local XComTacticalController PC;

    Status = DisplayStatus;
    // Log transitions rather than every Tick. Keep internal class names in
    // Launch.log; the player sees the localized, readable status above.
    if (Reason == LastWaitReason && Details == LastWaitDetails)
        return;
    LastWaitReason = Reason;
    LastWaitDetails = Details;
    `log("Waiting:" @ string(Reason) @ Details, , 'AutoplayXCom2');
    PC = XComTacticalController(WorldInfo.GetALocalPlayerController());
    `log("UI stack:" @ DescribeUIStack(PC), , 'AutoplayXCom2');
}

simulated event Tick(float DeltaTime)
{
    local XComTacticalController PC;
    local bool bToggleDown;
    local name UIBlockReason;
    local string UIBlockDetails;

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
        StopAutoplay("Escape", true);
    if (!bEnabled)
        return;

    if (`TACTICALRULES == none || !`TACTICALRULES.TacticalGameIsInPlay()
        || `TACTICALRULES.HasTacticalGameEnded())
    {
        StopAutoplay("Mission ended or world changed");
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
        SetWaitStatus('GamePaused', StatusGamePaused);
        return;
    }

    // A hack issued by us owns a blocking screen and visualization. Handle it
    // before the idle check; never dismiss unrelated dialogs or player hacks.
    if (HandleOwnedHack(DeltaTime))
        return;

    UIBlockReason = GetUIBlockReason(PC, UIBlockDetails);
    if (UIBlockReason != '')
    {
        switch (UIBlockReason)
        {
        case 'HUD':
            SetWaitStatus(UIBlockReason, StatusHUDWaiting, UIBlockDetails);
            break;
        case 'InputBlocked':
        case 'UIBusy':
            SetWaitStatus(UIBlockReason, StatusInputBlocked, UIBlockDetails);
            break;
        case 'Targeting':
            SetWaitStatus(UIBlockReason, StatusTargeting, UIBlockDetails);
            break;
        case 'Dialog':
            SetWaitStatus(UIBlockReason, StatusDialog, UIBlockDetails);
            break;
        default:
            SetWaitStatus(UIBlockReason, StatusModal, UIBlockDetails);
            break;
        }
        return;
    }
    if (!`TACTICALRULES.IsInState('TurnPhase_UnitActions')
        || `TACTICALRULES.GetUnitActionTeam() != eTeam_XCom
        || `TACTICALRULES.UnitActionPlayerIsAI()
        || !`TACTICALRULES.IsWaitingForNewStates()
        || !class'XComGameStateVisualizationMgr'.static.VisualizerIdleAndUpToDateWithHistory()
        || `TACTICALRULES.WaitingForVisualizer())
    {
        SetWaitStatus('GameRules', StatusWaiting,
            "state=" $ string(`TACTICALRULES.GetStateName())
            @ "team=" $ string(`TACTICALRULES.GetUnitActionTeam())
            @ "AI=" $ string(`TACTICALRULES.UnitActionPlayerIsAI())
            @ "waitingStates=" $ string(`TACTICALRULES.IsWaitingForNewStates())
            @ "visualizerIdle=" $ string(class'XComGameStateVisualizationMgr'.static.VisualizerIdleAndUpToDateWithHistory())
            @ "waitingVisualizer=" $ string(`TACTICALRULES.WaitingForVisualizer()));
        return;
    }

    if (LastWaitReason != '')
    {
        `log("Ready: tactical HUD and game rules allow orders", , 'AutoplayXCom2');
        LastWaitReason = '';
        LastWaitDetails = "";
    }
    Status = StatusActive;
    UntilDecision -= DeltaTime;
    if (UntilDecision > 0.0)
        return;
    UntilDecision = FMax(0.25, DecisionInterval);
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
    SetWaitStatus('Hacking', StatusModal, string(Hack.Class.Name));
    if (!AutoCompleteOwnedHacks || !Hack.bIsInited || Hack.OriginalContext == none
        || OwnedActionContext == none || Hack.OriginalContext != OwnedActionContext
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
        OwnedActionContext = none;
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
    local XComGameStateContext_Ability SubmittedContext;
    local StateObjectReference PlayerRef;
    local AvailableAction Candidate, BestAction;
    local array<TTile> CandidatePath, BestPath;
    local array<vector> CandidateLocations, BestLocations;
    local vector CandidateAim, BestAim;
    local int TargetIndex, BestTargetIndex, ChosenTargetID;
    local float Score, BestScore;
    local bool bMove, bArea, bHavePlan, bSuccess, bCanExplore, bCombatThreats;

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
        VisitedPositions.Length = 0;
        bEndTurnRequested = false;
    }
    if (bEndTurnRequested)
        return;
    if (ActionsThisTurn >= Max(1, MaxActionsPerTurn))
    {
        StopWithStatus("Per-turn action budget reached", StatusLimit);
        return;
    }
    if (ExploreUnseenMap && ExplorationPlanner == none)
        ExplorationPlanner = new(self) class'APX_ExplorationPlanner';
    if (UseExplosiveGrenades && AreaPlanner == none)
        AreaPlanner = new(self) class'APX_AreaAttackPlanner';

    BestScore = -10000.0;
    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', UnitState)
    {
        if (UnitState.GetAssociatedPlayerID() != PlayerRef.ObjectID
            || UnitState.GetTeam() != eTeam_XCom || !UnitState.IsAlive()
            || UnitState.GetMyTemplate().bIsCosmetic)
            continue;

        // Contacts remain relevant after the last soldier spends their AP.
        bCombatThreats = bCombatThreats
            || class'APX_MissionPlanner'.static.HasCombatThreats(UnitState);
        if (!UnitState.IsAbleToAct())
            continue;
        if (class'APX_CombatPlanner'.static.ChooseAction(UnitState, Candidate, TargetIndex, Score)
            && Score > BestScore && CanUseAction(UnitState, Candidate, TargetIndex))
        {
            BestAction = Candidate;
            BestTargetIndex = TargetIndex;
            BestScore = Score;
            BestUnit = UnitState;
            bMove = false;
            bArea = false;
            BestLocations.Length = 0;
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
            bArea = false;
            BestLocations.Length = 0;
            bHavePlan = true;
        }
        CandidateLocations.Length = 0;
        if (AutoPlaceEvac && class'APX_EvacPlanner'.static.ChoosePlacement(
            UnitState, Candidate, CandidateLocations, Score) && Score > BestScore)
        {
            TargetIndex = Candidate.AvailableTargets.Length == 0 ? INDEX_NONE : 0;
            if (CanUseAction(UnitState, Candidate, TargetIndex))
            {
                BestAction = Candidate;
                BestTargetIndex = TargetIndex;
                BestScore = Score;
                BestUnit = UnitState;
                BestLocations = CandidateLocations;
                bMove = false;
                bArea = false;
                bHavePlan = true;
            }
        }
        CandidateLocations.Length = 0;
        if (UseExplosiveGrenades && AreaPlanner != none
            && AreaPlanner.ChooseAction(UnitState, Candidate, TargetIndex,
                CandidateLocations, CandidateAim, Score)
            && Score > BestScore && CanUseAction(UnitState, Candidate, TargetIndex))
        {
            BestAction = Candidate;
            BestTargetIndex = TargetIndex;
            BestScore = Score;
            BestUnit = UnitState;
            BestLocations = CandidateLocations;
            BestAim = CandidateAim;
            bMove = false;
            bArea = true;
            bHavePlan = true;
        }
        CandidatePath.Length = 0;
        if (class'APX_MissionPlanner'.static.ChooseMove(UnitState, CandidatePath, Score)
            && Score > BestScore && CanUseMove(UnitState, CandidatePath))
        {
            BestPath = CandidatePath;
            BestScore = Score;
            BestUnit = UnitState;
            bMove = true;
            bArea = false;
            BestLocations.Length = 0;
            bHavePlan = true;
        }
    }

    // Explore only when the whole squad lacks an objective, attack or useful
    // mission move. Sampling the player's fog never queries hidden enemies.
    if (ExploreUnseenMap && ExplorationPlanner != none && !bCombatThreats
        && (!bHavePlan || BestScore < 15.0))
    {
        foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', UnitState)
        {
            if (UnitState.GetAssociatedPlayerID() != PlayerRef.ObjectID
                || UnitState.GetTeam() != eTeam_XCom || !UnitState.IsAbleToAct()
                || UnitState.IsCivilian() || UnitState.GetMyTemplate().bIsCosmetic
                || !class'APX_ExplorationPlanner'.static.CanExplore(UnitState))
                continue;
            bCanExplore = true;
            CandidatePath.Length = 0;
            if (ExplorationPlanner.ChooseMove(UnitState, CandidatePath, Score)
                && Score > BestScore && CanUseMove(UnitState, CandidatePath))
            {
                BestPath = CandidatePath;
                BestScore = Score;
                BestUnit = UnitState;
                BestLocations.Length = 0;
                bMove = true;
                bArea = false;
                bHavePlan = true;
            }
        }
        if (bCanExplore && (!bHavePlan || BestScore <= 2.0)
            && ExplorationPlanner.HasPendingSearch())
        {
            Status = StatusWaiting;
            return;
        }
    }

    // Avoid burning whole turns on overwatch forever when no objective, attack
    // or useful move can be found. An unknown scripted objective needs a human.
    if ((!bHavePlan || BestScore <= 2.0) && MeaningfulActionsThisTurn == 0
        && !bCombatThreats)
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
        OwnedActionContext = none;
        if (PC.m_kPathingPawn == none)
        {
            StopWithStatus("Movement visualizer is unavailable", StatusRejected);
            return;
        }
        // The stock helper copies the human cursor's waypoints. They must not
        // be applied to an independently planned route or a different soldier.
        PC.m_kPathingPawn.ClearAllWaypoints();
        bSuccess = PC.GameStateMoveUnitSingle(XGUnit(BestUnit.GetVisualizer()), BestPath);
        `log("Move unit" @ BestUnit.ObjectID @ "tiles" @ BestPath.Length
            @ "to" @ BestPath[BestPath.Length - 1].X @ BestPath[BestPath.Length - 1].Y
            @ BestPath[BestPath.Length - 1].Z @ "score" @ BestScore
            @ "AP before" @ BestUnit.NumActionPoints(), , 'AutoplayXCom2');
    }
    else
    {
        if (bArea && !AreaPlanner.PrepareForActivation(
            BestUnit, BestAction, BestAim, BestLocations))
        {
            StopWithStatus("Grenade landing or affected objects changed", StatusRejected);
            return;
        }
        // Cache ownership before submitting; the action may create a hack UI.
        OwnedAbilityID = BestAction.AbilityObjectRef.ObjectID;
        OwnedSourceID = BestUnit.ObjectID;
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(OwnedAbilityID));
        if (BestTargetIndex >= 0 && BestTargetIndex < BestAction.AvailableTargets.Length)
            ChosenTargetID = BestAction.AvailableTargets[BestTargetIndex].PrimaryTarget.ObjectID;
        SubmittedContext = class'XComGameStateContext_Ability'.static.ActivateAbility_ReturnContext(
            BestAction, BestTargetIndex, BestLocations);
        OwnedActionContext = SubmittedContext;
        bSuccess = SubmittedContext != none;
        RecordAction(BestUnit, BestAction, BestTargetIndex);
        `log("Ability" @ Ability.GetMyTemplateName() @ "unit" @ BestUnit.ObjectID
            @ "target" @ ChosenTargetID @ "target index" @ BestTargetIndex @ "score" @ BestScore
            @ "AP before" @ BestUnit.NumActionPoints(), , 'AutoplayXCom2');
    }
    if (!bSuccess)
    {
        StopWithStatus("Engine rejected planned action", StatusRejected);
        return;
    }
    if (bMove)
        RecordMove(BestUnit, BestPath);
    ++ActionsThisTurn;
    if (BestScore > 2.0)
        ++MeaningfulActionsThisTurn;
}

// Re-evaluation after every ally action can change support scores. Remember
// this turn's visited endpoints so those changes cannot produce A-B-A shuffles.
function bool CanUseMove(XComGameState_Unit UnitState, const out array<TTile> Path)
{
    local int Index;
    if (Path.Length < 2)
        return false;
    for (Index = 0; Index < VisitedPositions.Length; ++Index)
    {
        if (VisitedPositions[Index].UnitID == UnitState.ObjectID
            && VisitedPositions[Index].Tile == Path[Path.Length - 1])
            return false;
    }
    return true;
}

function RecordMove(XComGameState_Unit UnitState, const out array<TTile> Path)
{
    local VisitedPosition Entry;
    Entry.UnitID = UnitState.ObjectID;
    Entry.Tile = Path[0];
    VisitedPositions.AddItem(Entry);
    Entry.Tile = Path[Path.Length - 1];
    VisitedPositions.AddItem(Entry);
}

simulated event Destroyed()
{
    if (AreaPlanner != none)
        AreaPlanner.Cleanup();
    ExplorationPlanner = none;
    AreaPlanner = none;
    OwnedActionContext = none;
    OwnedHackScreen = none;
    super.Destroyed();
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
    bEnabled=false
    bAlwaysTick=true
    bHidden=true
    bCollideActors=false
    bBlockActors=false
    RemoteRole=ROLE_None
}
