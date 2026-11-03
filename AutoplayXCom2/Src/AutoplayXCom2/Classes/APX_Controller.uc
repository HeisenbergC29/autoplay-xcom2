// One runtime-only actor per tactical HUD. Never serialized into a campaign.
class APX_Controller extends Actor config(AutoplayXCom2)
    dependson(X2GameRuleset, XComGameState, XComGameStateContext_Ability);

var config name ToggleKey;
var config float DecisionInterval;
var config int MaxActionsPerTurn;
var config int MaxSameActionPerTurn;
var config bool AutoEndTurn;
var config bool AutoCompleteOwnedHacks;
var config bool ExploreUnseenMap;
var config bool AutoPlaceEvac;
var config bool UseExplosiveGrenades;
var config bool EnableMissionRecording;
var config bool RecordCandidateScores;
var config float RecordingInterval;
var config int ContactMemoryTurns;
var config float ContactSearchDistance;
var config bool CoordinateConcealedAmbush;

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

// Positions are copied only while the contact is visible. Never refresh a
// lost contact from its live (hidden) unit state.
struct RecentContact
{
    var int UnitID;
    var TTile LastSeenTile;
    var int LastSeenTurn;
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
var private APX_MissionRecorder MissionRecorder;
var private float UntilObservation;
var private array<RecentContact> RecentContacts;
var private bool bContactHistoryInitialized;
var private int ContactHistoryCursor;
var private int AmbushPreparationActions;

static function bool IsContactFresh(int CurrentTurn, int SeenTurn, int MemoryTurns)
{
    return CurrentTurn >= SeenTurn && CurrentTurn - SeenTurn <= MemoryTurns;
}

function bool RefreshContacts(int PlayerID, int CurrentTurn)
{
    local XComGameState_Unit SourceUnit, Enemy;
    local array<StateObjectReference> VisibleEnemies;
    local StateObjectReference EnemyRef;
    local RecentContact Contact;
    local int Index;
    local bool bVisible, bFoundSource;

    foreach `XCOMHISTORY.IterateByClassType(class'XComGameState_Unit', SourceUnit)
    {
        if (SourceUnit.GetAssociatedPlayerID() == PlayerID && SourceUnit.IsAlive()
            && SourceUnit.GetTeam() == eTeam_XCom && !SourceUnit.GetMyTemplate().bIsCosmetic)
        {
            bFoundSource = true;
            break;
        }
    }
    if (!bFoundSource)
        return false;
    class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(PlayerID, VisibleEnemies);
    foreach VisibleEnemies(EnemyRef)
    {
        Enemy = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(EnemyRef.ObjectID));
        if (!class'APX_CombatPlanner'.static.IsVisibleHostile(SourceUnit, Enemy, VisibleEnemies))
            continue;
        bVisible = true;
        Index = RecentContacts.Find('UnitID', Enemy.ObjectID);
        if (Index == INDEX_NONE)
        {
            if (RecentContacts.Length >= 128)
                RecentContacts.Remove(0, 1);
            Contact.UnitID = Enemy.ObjectID;
            RecentContacts.AddItem(Contact);
            Index = RecentContacts.Length - 1;
        }
        RecentContacts[Index].LastSeenTile = Enemy.TileLocation;
        RecentContacts[Index].LastSeenTurn = CurrentTurn;
    }
    for (Index = RecentContacts.Length - 1; Index >= 0; --Index)
    {
        if (!IsContactFresh(CurrentTurn, RecentContacts[Index].LastSeenTurn,
            Clamp(ContactMemoryTurns, 0, 8)))
            RecentContacts.Remove(Index, 1);
    }
    return bVisible;
}

// Clear only deaths observed as the result of our own action against a known,
// visible target. Looking up lost enemies' CURRENT HP would reveal hidden state.
function PruneObservedDefeats(int PlayerID)
{
    local XComGameState HistoryFrame;
    local XComGameStateContext_Ability AbilityContext;
    local XComGameState_Unit SourceUnit, BeforeUnit, AfterUnit;
    local array<StateObjectReference> VisibleBefore, Targets;
    local StateObjectReference TargetRef;
    local int EndIndex, ContactIndex;

    if (!bContactHistoryInitialized || RecentContacts.Length == 0)
    {
        ContactHistoryCursor = `XCOMHISTORY.GetCurrentHistoryIndex();
        bContactHistoryInitialized = true;
        return;
    }
    EndIndex = Min(`XCOMHISTORY.GetCurrentHistoryIndex(), ContactHistoryCursor + 512);
    while (ContactHistoryCursor < EndIndex)
    {
        ++ContactHistoryCursor;
        HistoryFrame = `XCOMHISTORY.GetGameStateFromHistory(ContactHistoryCursor);
        if (HistoryFrame == none)
            continue;
        AbilityContext = XComGameStateContext_Ability(HistoryFrame.GetContext());
        if (AbilityContext == none
            || AbilityContext.InterruptionStatus == eInterruptionStatus_Interrupt)
            continue;
        SourceUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
            AbilityContext.InputContext.SourceObject.ObjectID, eReturnType_Reference, ContactHistoryCursor));
        if (SourceUnit == none || SourceUnit.GetAssociatedPlayerID() != PlayerID
            || SourceUnit.GetTeam() != eTeam_XCom)
            continue;
        VisibleBefore.Length = 0;
        class'X2TacticalVisibilityHelpers'.static.GetAllVisibleEnemiesForPlayer(
            PlayerID, VisibleBefore, ContactHistoryCursor - 1);
        Targets = AbilityContext.InputContext.MultiTargets;
        Targets.AddItem(AbilityContext.InputContext.PrimaryTarget);
        foreach Targets(TargetRef)
        {
            ContactIndex = RecentContacts.Find('UnitID', TargetRef.ObjectID);
            if (ContactIndex == INDEX_NONE
                || VisibleBefore.Find('ObjectID', TargetRef.ObjectID) == INDEX_NONE)
                continue;
            BeforeUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
                TargetRef.ObjectID, eReturnType_Reference, ContactHistoryCursor - 1));
            AfterUnit = XComGameState_Unit(`XCOMHISTORY.GetGameStateForObjectID(
                TargetRef.ObjectID, eReturnType_Reference, ContactHistoryCursor));
            if (BeforeUnit != none && AfterUnit != none
                && BeforeUnit.IsAlive() && !AfterUnit.IsAlive())
            {
                RecentContacts.Remove(ContactIndex, 1);
                if (MissionRecorder != none)
                    MissionRecorder.Marker("contact_resolved", "unit=" $ TargetRef.ObjectID
                        @ "history=" $ ContactHistoryCursor);
            }
        }
    }
}

function bool ChooseContactSearchMove(XComGameState_Unit UnitState,
    out array<TTile> Path, out float Score)
{
    local XGUnit Visualizer;
    local TTile GoalTile;
    local int Index, BestIndex, BestPathIndex;
    local float Distance, BestDistance, EndpointValue, BestEndpointValue;

    Path.Length = 0;
    Score = 0.0;
    if (UnitState.NumActionPoints() < 2 || UnitState.IsCivilian()
        || !class'APX_MissionPlanner'.static.HasLegalMove(UnitState))
        return false;
    BestIndex = INDEX_NONE;
    BestDistance = 100000.0;
    for (Index = 0; Index < RecentContacts.Length; ++Index)
    {
        Distance = class'APX_MissionPlanner'.static.TileDistance(
            UnitState.TileLocation, RecentContacts[Index].LastSeenTile);
        if (Distance > 2.0 && Distance < BestDistance)
        {
            BestDistance = Distance;
            BestIndex = Index;
        }
    }
    if (BestIndex == INDEX_NONE)
        return false;
    GoalTile = RecentContacts[BestIndex].LastSeenTile;
    Visualizer = XGUnit(UnitState.GetVisualizer());
    if (Visualizer == none || Visualizer.m_kReachableTilesCache == none)
        return false;
    Visualizer.m_kReachableTilesCache.UpdateTileCacheIfNeeded();
    if (!class'APX_MissionPlanner'.static.ChooseRoutePrefix(UnitState, Visualizer, GoalTile, Path))
        return false;
    // Investigate the last observed position in short steps, preserving a
    // response. A lost contact is not permission to make a blind rooftop push.
    for (Index = 1; Index < Path.Length; ++Index)
    {
        if (class'APX_MissionPlanner'.static.TileDistance(UnitState.TileLocation, Path[Index])
            > FClamp(ContactSearchDistance, 1.0, 6.0)
            || Path[Index].Z > UnitState.TileLocation.Z + 1)
        {
            Path.Remove(Index, Path.Length - Index);
            break;
        }
    }
    if (Path.Length < 2)
        return false;
    BestPathIndex = 1;
    BestEndpointValue = -100000.0;
    for (Index = 1; Index < Path.Length; ++Index)
    {
        EndpointValue = class'APX_MissionPlanner'.static.AdvanceEndpointScore(float(Index),
            class'APX_MissionPlanner'.static.AdvanceCoverLevel(UnitState, Path[Index], GoalTile));
        if (EndpointValue > BestEndpointValue)
        {
            BestEndpointValue = EndpointValue;
            BestPathIndex = Index;
        }
    }
    if (BestPathIndex < Path.Length - 1)
        Path.Remove(BestPathIndex + 1, Path.Length - BestPathIndex - 1);
    Score = 20.0;
    return true;
}

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

// The passive HUD may run while autoplay is off. Forward only to an already
// started recorder; observing text must never start recording or issue orders.
function RecordDisplayedScore(string DisplayText)
{
    if (MissionRecorder != none)
        MissionRecorder.RecordHUDScore(DisplayText);
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
    if (MissionRecorder != none)
        MissionRecorder.Marker("autoplay_stop", Reason);
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
    if (MissionRecorder != none)
        MissionRecorder.Marker("wait", string(Reason) @ Details);
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

    // Recording is observational and continues through alien turns and a user
    // stop, so incoming fire and the result of the last order are not lost.
    if (EnableMissionRecording && MissionRecorder == none && bEnabled
        && PC.m_XGPlayer != none)
    {
        MissionRecorder = new(self) class'APX_MissionRecorder';
        MissionRecorder.Start(PC.m_XGPlayer.ObjectID);
    }
    if (MissionRecorder != none)
    {
        if (`TACTICALRULES != none && `TACTICALRULES.HasTacticalGameEnded())
            MissionRecorder.Finish("tactical_game_ended");
        else
        {
            UntilObservation -= DeltaTime;
            if (UntilObservation <= 0.0)
            {
                UntilObservation = FMax(0.5, RecordingInterval);
                MissionRecorder.Observe(bEnabled ? "autoplay" : "manual");
            }
        }
    }
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
    local XComGameState_Unit UnitState, BestUnit, AmbushUnit;
    local XComGameState_Player PlayerState;
    local XComGameState_Ability Ability;
    local XComGameStateContext_Ability SubmittedContext;
    local StateObjectReference PlayerRef;
    local AvailableAction Candidate, BestAction, AmbushAction;
    local array<TTile> CandidatePath, BestPath, AmbushPath;
    local array<vector> CandidateLocations, BestLocations;
    local vector CandidateAim, BestAim;
    local int TargetIndex, BestTargetIndex, ChosenTargetID, AmbushTargetIndex, RescuePatientID;
    local float Score, BestScore, AmbushScore;
    local bool bMove, bArea, bHavePlan, bSuccess, bCanExplore, bCombatThreats;
    local bool bVisibleThreats, bContactSearch, bCandidateMove, bGrenadeCandidate;

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
        AmbushPreparationActions = 0;
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
    if (MissionRecorder != none)
        MissionRecorder.BeginDecision();
    bVisibleThreats = RefreshContacts(PlayerRef.ObjectID, PlayerState.PlayerTurnCount);
    PruneObservedDefeats(PlayerRef.ObjectID);
    bContactSearch = !bVisibleThreats && RecentContacts.Length > 0;
    bCombatThreats = bVisibleThreats || bContactSearch;
    if (bContactSearch && MissionRecorder != none)
        MissionRecorder.Marker("recent_contacts", "count=" $ RecentContacts.Length);

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
        if (class'APX_CombatPlanner'.static.ChooseAction(UnitState, Candidate, TargetIndex, Score, bContactSearch)
            && TraceCandidateAction(UnitState, "combat", Candidate, TargetIndex, Score)
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
            && TraceCandidateAction(UnitState, "interaction", Candidate, TargetIndex, Score)
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
        if (class'APX_MissionPlanner'.static.ChooseLootInteraction(UnitState, Candidate, TargetIndex, Score)
            && TraceCandidateAction(UnitState, "loot", Candidate, TargetIndex, Score)
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
            UnitState, Candidate, CandidateLocations, Score)
            && TraceCandidateAction(UnitState, "evac_placement", Candidate, INDEX_NONE, Score)
            && Score > BestScore)
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
        bGrenadeCandidate = false;
        if (UseExplosiveGrenades && AreaPlanner != none)
        {
            bGrenadeCandidate = AreaPlanner.ChooseAction(UnitState, Candidate, TargetIndex,
                CandidateLocations, CandidateAim, Score);
            if (MissionRecorder != none)
                MissionRecorder.Marker("grenade_scan", "unit=" $ UnitState.ObjectID
                    @ AreaPlanner.GetDiagnosticSummary());
        }
        if (bGrenadeCandidate
            && TraceCandidateAction(UnitState, "grenade", Candidate, TargetIndex, Score)
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
        if (bContactSearch && !class'APX_MissionPlanner'.static.ShouldEvacuate(UnitState))
            bCandidateMove = ChooseContactSearchMove(UnitState, CandidatePath, Score);
        else
            bCandidateMove = class'APX_MissionPlanner'.static.ChooseMove(UnitState, CandidatePath, Score);
        if (bCandidateMove
            && TraceCandidateMove(UnitState, CandidatePath, Score)
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
        CandidatePath.Length = 0;
        if (class'APX_MissionPlanner'.static.ChooseRescueMove(UnitState, CandidatePath, Score, RescuePatientID)
            && TraceCandidateMove(UnitState, CandidatePath, Score)
            && Score > BestScore && CanUseMove(UnitState, CandidatePath))
        {
            BestPath = CandidatePath;
            BestScore = Score;
            BestUnit = UnitState;
            bMove = true;
            bArea = false;
            BestLocations.Length = 0;
            bHavePlan = true;
            if (MissionRecorder != none)
                MissionRecorder.Marker("rescue_candidate", "unit=" $ UnitState.ObjectID
                    @ "patient=" $ RescuePatientID @ "score=" $ Score);
        }
        CandidatePath.Length = 0;
        if (!bCombatThreats
            && class'APX_MissionPlanner'.static.ChooseLootMove(UnitState, CandidatePath, Score)
            && TraceCandidateMove(UnitState, CandidatePath, Score)
            && Score > BestScore && CanUseMove(UnitState, CandidatePath))
        {
            BestPath = CandidatePath;
            BestScore = Score;
            BestUnit = UnitState;
            bMove = true;
            bArea = false;
            BestLocations.Length = 0;
            bHavePlan = true;
            if (MissionRecorder != none)
                MissionRecorder.Marker("loot_candidate", "unit=" $ UnitState.ObjectID @ "score=" $ Score);
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
                && TraceCandidateMove(UnitState, CandidatePath, Score)
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

    // Reserve the chosen opener. Other concealed soldiers can establish firing
    // lanes and legal reaction shots before an individual attack reveals them.
    if (CoordinateConcealedAmbush && bHavePlan && !bMove && BestUnit != none)
    {
        Ability = XComGameState_Ability(`XCOMHISTORY.GetGameStateForObjectID(BestAction.AbilityObjectRef.ObjectID));
        if (Ability != none && Ability.GetMyTemplate() != none
            && class'APX_SquadPlanner'.static.CanPrepare(
                class'APX_SquadPlanner'.static.SquadIsConcealed(PlayerRef.ObjectID),
                Ability.GetMyTemplate().Hostility == eHostility_Offensive,
                AmbushPreparationActions, Clamp(class'APX_SquadPlanner'.default.MaxPreparationActionsPerTurn, 0, 12)))
        {
            if (class'APX_SquadPlanner'.static.ChoosePreparation(PlayerRef.ObjectID, BestUnit,
                AmbushUnit, AmbushAction, AmbushTargetIndex, AmbushPath, AmbushScore)
                && ((AmbushPath.Length > 1 && CanUseMove(AmbushUnit, AmbushPath))
                    || (AmbushPath.Length == 0 && CanUseAction(AmbushUnit, AmbushAction, AmbushTargetIndex))))
            {
                if (MissionRecorder != none)
                    MissionRecorder.Marker("ambush_setup", "opener=" $ BestUnit.ObjectID
                        @ "unit=" $ AmbushUnit.ObjectID @ "move=" $ string(AmbushPath.Length > 1));
                BestUnit = AmbushUnit;
                BestAction = AmbushAction;
                BestTargetIndex = AmbushTargetIndex;
                BestPath = AmbushPath;
                BestScore = AmbushScore;
                BestLocations.Length = 0;
                bMove = AmbushPath.Length > 1;
                bArea = false;
                ++AmbushPreparationActions;
            }
            else if (MissionRecorder != none)
                MissionRecorder.Marker("ambush_opening", "unit=" $ BestUnit.ObjectID
                    @ "preparations=" $ AmbushPreparationActions);
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
            if (MissionRecorder != none)
                MissionRecorder.Marker("end_turn", "accepted=" $ string(bEndTurnRequested));
            if (!bEndTurnRequested)
                StopWithStatus("Engine rejected end turn", StatusRejected);
        }
        else
            StopWithStatus("Turn complete; automatic end turn is disabled", StatusNoPlan);
        return;
    }

    // Freeze diagnostic previews before submitting; the resulting history may
    // change hit chances and health before the accepted-result record is made.
    if (MissionRecorder != none)
    {
        if (bMove)
            MissionRecorder.PrepareChosenMove(BestUnit, BestPath, BestScore);
        else if (bArea)
            MissionRecorder.PrepareChosenArea(BestUnit, BestAction, BestTargetIndex, BestScore,
                BestAim, BestLocations);
        else
            MissionRecorder.PrepareChosenAction(BestUnit, BestAction, BestTargetIndex, BestScore);
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
    if (MissionRecorder != none)
    {
        if (bMove)
            MissionRecorder.ChosenMove(BestUnit, BestPath, BestScore, bSuccess);
        else
            MissionRecorder.ChosenAction(BestUnit, BestAction, BestTargetIndex, BestScore, bSuccess);
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

// Always return true: tracing must never change which legal action is chosen.
function bool TraceCandidateAction(XComGameState_Unit UnitState, string Kind,
    AvailableAction Action, int TargetIndex, float Score)
{
    if (MissionRecorder != none && RecordCandidateScores)
        MissionRecorder.CandidateAction(UnitState, Kind, Action, TargetIndex, Score);
    return true;
}

function bool TraceCandidateMove(XComGameState_Unit UnitState,
    const out array<TTile> Path, float Score)
{
    if (MissionRecorder != none && RecordCandidateScores)
        MissionRecorder.CandidateMove(UnitState, Path, Score);
    return true;
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
    if (MissionRecorder != none)
        MissionRecorder.Finish("controller_destroyed");
    if (AreaPlanner != none)
        AreaPlanner.Cleanup();
    ExplorationPlanner = none;
    AreaPlanner = none;
    OwnedActionContext = none;
    OwnedHackScreen = none;
    MissionRecorder = none;
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
