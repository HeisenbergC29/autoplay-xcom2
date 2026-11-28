class APX_UITacticalControl extends UIPanel config(AutoplayXCom2);

// Coordinates use the stock UI's scaled coordinate space. The origin is the
// centre of the right edge; users of other HUD mods can move this entire panel.
// OffsetY remains the button's position; the score occupies the row above it.
var config float OffsetX;
var config float OffsetY;
var config float ButtonWidth;
var config float FadeSeconds;
var config float CollapseDelaySeconds;
var config float IndicatorAlpha;
// Keep toggle/status/native score visible through the entire tactical HUD.
// Opt-out restores the original mouse-out auto-collapse behavior.
var config bool AlwaysExpanded;

var localized string EnableLabel;
var localized string DisableLabel;
var localized string IndicatorTooltip;

var APX_Controller Controller;
var APX_MissionScore ScoreCounter;
var UIButton ToggleButton;
var UIBGBox Indicator;
var UIText ScoreLabel;
var UIText StatusLabel;
var bool bExpanded;
var bool bPendingCollapse;
var float CollapseRemaining;
var float RefreshRemaining;
// Cache only HUD text; authoritative mission score reads stay uncached.
var float ScoreRefreshRemaining;
var bool bScoreTextValid;
var bool bScoreReadDeferred;
var string CachedScoreText;
var XComGameStateHistory CachedScoreHistory;
var int CachedScoreHistoryIndex;
var bool bSawTacticalInPlay;
var bool bPostMissionQuiesced;
/** Keeps the first full-intel reveal pending until a usable tactical world exists. */
var bool bMapRevealInitialized;

/** Build the tactical controls and reveal the map now if tactical play is ready. */
simulated function APX_UITacticalControl InitAutoplayControl()
{
    InitPanel('APX_AutoplayControl');
    SetAnchor(class'UIUtilities'.const.ANCHOR_MIDDLE_RIGHT);
    SetPosition(OffsetX, OffsetY - 31.0);
    SetSize(ButtonWidth + 20.0, 85.0);
    DisableNavigation();

    // The panel can be instantiated while tactical rule initialization is
    // still finishing; an initial !TacticalGameIsInPlay is not mission end.
    bSawTacticalInPlay = false;
    bPostMissionQuiesced = false;
    bMapRevealInitialized = false;
    Controller = class'APX_Controller'.static.GetOrCreate();
    // Reveal the map for the local squad without waiting for F8/autoplay.
    if (CanUpdateTacticalHUD() && class'APX_FullIntel'.static.RevealMapForPlayer())
    {
        bMapRevealInitialized = true;
        `log("Full intel|revision=mission-report-v55|enabled=True|map_revealed=True", true, 'AutoplayXCom2');
    }
    ScoreCounter = new(self) class'APX_MissionScore';
    bScoreTextValid = false;
    CachedScoreHistory = none;
    CachedScoreHistoryIndex = -1;
    ScoreRefreshRemaining = 0.0;
    `log("HUD score polling|revision=mission-report-v55|stable_interval_seconds=1.0|status_interval_seconds=0.25|history_invalidation=true", true, 'AutoplayXCom2');

    ToggleButton = Spawn(class'UIButton', self);
    ToggleButton.InitButton('APX_ToggleButton', EnableLabel, OnToggleClicked);
    ToggleButton.SetResizeToText(false);
    ToggleButton.SetSize(ButtonWidth, 30.0);
    ToggleButton.SetPosition(0.0, 31.0);
    ToggleButton.DisableNavigation();
    ToggleButton.ProcessMouseEvents(OnControlMouseEvent);

    ScoreLabel = Spawn(class'UIText', self);
    ScoreLabel.InitText('APX_Score');
    ScoreLabel.SetPosition(0.0, 0.0);
    ScoreLabel.SetSize(ButtonWidth, 30.0);
    ScoreLabel.DisableMouseHit();
    ScoreLabel.DisableNavigation();

    StatusLabel = Spawn(class'UIText', self);
    StatusLabel.InitText('APX_Status');
    StatusLabel.SetPosition(0.0, 62.0);
    StatusLabel.SetSize(ButtonWidth, 22.0);
    StatusLabel.DisableMouseHit();
    StatusLabel.DisableNavigation();

    // Keep a small hit target alive when collapsed. A zero-alpha or hidden
    // Flash control can stop receiving mouse events, hence a visible sliver.
    Indicator = Spawn(class'UIBGBox', self);
    Indicator.InitBG('APX_Indicator', ButtonWidth + 8.0, 31.0, 8.0, 30.0);
    Indicator.DisableNavigation();
    Indicator.ProcessMouseEvents(OnControlMouseEvent);
    Indicator.SetTooltipText(IndicatorTooltip);

    UpdateStatus();
    Expand();
    ScheduleCollapse();
    return self;
}

/** Honor input only while stock tactical play is active. */
simulated function OnToggleClicked(UIButton Button)
{
    if (!CanUpdateTacticalHUD())
        return;
    if (Controller != none)
    {
        Controller.Toggle();
        UpdateStatus();
    }
    Expand();
    ScheduleCollapse();
}

/** Ignore mouse callbacks delivered during startup or after tactical play ends. */
simulated function OnControlMouseEvent(UIPanel Panel, int Cmd)
{
    if (!CanUpdateTacticalHUD())
        return;
    switch (Cmd)
    {
    case class'UIUtilities_Input'.const.FXS_L_MOUSE_IN:
    case class'UIUtilities_Input'.const.FXS_L_MOUSE_OVER:
    case class'UIUtilities_Input'.const.FXS_L_MOUSE_DRAG_OVER:
        Expand();
        break;
    case class'UIUtilities_Input'.const.FXS_L_MOUSE_OUT:
    case class'UIUtilities_Input'.const.FXS_L_MOUSE_DRAG_OUT:
    case class'UIUtilities_Input'.const.FXS_L_MOUSE_RELEASE_OUTSIDE:
        ScheduleCollapse();
        break;
    case class'UIUtilities_Input'.const.FXS_L_MOUSE_UP:
        // Clicking the indicator reveals the button without issuing an order.
        if (Panel == Indicator)
        {
            Expand();
            ScheduleCollapse();
        }
        break;
    }
}

simulated function Expand()
{
    bPendingCollapse = false;
    if (bExpanded)
        return;

    bExpanded = true;
    ToggleButton.EnableMouseHit();
    ToggleButton.RemoveTweens();
    StatusLabel.RemoveTweens();
    ToggleButton.AddTween("_alpha", 100.0, FMax(0.01, FadeSeconds));
    StatusLabel.AddTween("_alpha", 100.0, FMax(0.01, FadeSeconds));
}

simulated function ScheduleCollapse()
{
    if (default.AlwaysExpanded)
    {
        bPendingCollapse = false;
        Expand();
        return;
    }
    bPendingCollapse = true;
    CollapseRemaining = FMax(0.25, CollapseDelaySeconds);
}

simulated function Collapse()
{
    if (default.AlwaysExpanded)
    {
        Expand();
        return;
    }
    bExpanded = false;
    bPendingCollapse = false;
    // Only the slim indicator may intercept the battlefield while collapsed.
    ToggleButton.DisableMouseHit();
    ToggleButton.RemoveTweens();
    StatusLabel.RemoveTweens();
    ToggleButton.AddTween("_alpha", 0.0, FMax(0.01, FadeSeconds));
    StatusLabel.AddTween("_alpha", 0.0, FMax(0.01, FadeSeconds));
}

// This is a display scheduling rule, not a rule about the true score.
// A fresh game-state index is new evidence even if the timer has not expired.
static function bool ShouldRefreshScoreForHUD(bool bValid, bool bHistoryChanged,
    float SecondsUntilRefresh)
{
    return !bValid || bHistoryChanged || SecondsUntilRefresh <= 0.0;
}

/** Return the mission score for a live tactical HUD, with its existing history cache. */
simulated function string GetDisplayedScoreText()
{
    local XComGameStateHistory History;
    local int HistoryIndex;

    bScoreReadDeferred = false;
    if (ScoreCounter == none || !CanUpdateTacticalHUD())
        return "";

    History = `XCOMHISTORY;
    if (!class'APX_MissionScore'.static.CanReadScoreNow())
    {
        bScoreReadDeferred = true;
        // Keep only already displayed text from this history. Do not query
        // its index, mark a new observation or reset the refresh deadline.
        if (!bScoreTextValid || History != CachedScoreHistory)
            return ScoreCounter.UnavailableText();
        return CachedScoreText;
    }
    HistoryIndex = -1;
    if (History != none)
        HistoryIndex = History.GetCurrentHistoryIndex();

    if (ShouldRefreshScoreForHUD(bScoreTextValid,
        History != CachedScoreHistory || HistoryIndex != CachedScoreHistoryIndex,
        ScoreRefreshRemaining))
    {
        // Refresh on this status update; a history delta bypasses the timer.
        // Periodic reads continue even while autoplay is OFF.
        CachedScoreText = ScoreCounter.GetText();
        bScoreTextValid = true;
        CachedScoreHistory = History;
        CachedScoreHistoryIndex = HistoryIndex;
        ScoreRefreshRemaining = 1.0;
    }
    return CachedScoreText;
}

/** Refresh the text and toggle only while the tactical HUD is usable. */
simulated function UpdateStatus()
{
    local string ScoreText;

    if (!CanUpdateTacticalHUD())
        return;
    // UIText caches its HTML, so unchanged score/font values do not issue
    // another Flash update. Keep this independent of autoplay's run state.
    if (ScoreCounter != none && ScoreLabel != none && ToggleButton != none)
    {
        ScoreText = GetDisplayedScoreText();
        ScoreLabel.SetCenteredText(class'UIUtilities_Text'.static.GetColoredText(
            ScoreText, eUIState_Normal, ToggleButton.FontSize));
        if (Controller != none && !bScoreReadDeferred)
            Controller.RecordDisplayedScore(ScoreText);
    }

    if (Controller == none)
        return;

    if (Controller.IsEnabled())
    {
        ToggleButton.SetText(DisableLabel);
        ToggleButton.SetGood(true);
        Indicator.SetColor("53B45E");
    }
    else
    {
        ToggleButton.SetText(EnableLabel);
        ToggleButton.SetGood(false);
        Indicator.SetColor("9ACBCB");
    }
    Indicator.SetAlpha(FClamp(IndicatorAlpha, 5.0, 100.0));
    StatusLabel.SetHTMLText(class'UIUtilities_Text'.static.GetColoredText(
        Controller.GetStatusText(), eUIState_Normal, 14));
}

/**
 * Distinguish first-frame tactical startup from a completed or unloaded match.
 * Returning true never changes gameplay state; it only stops HUD observers.
 * @param bEverInPlay True after a stock tactical InPlay state was observed.
 * @param bInPlay Current stock rules TacticalGameIsInPlay result.
 * @param bEnded Current stock rules HasTacticalGameEnded result.
 * @return True only after native end or loss of a previously active match.
 */
static function bool ShouldQuiesceHUD(bool bEverInPlay, bool bInPlay, bool bEnded)
{
    return bEnded || (bEverInPlay && !bInPlay);
}

/**
 * Stop this HUD's score/history/FOW polling while the stock end-state owns
 * tactical-to-strategy travel. Do not destroy Controller here: it must first
 * finish recording the native outcome and detach its mission event listeners.
 */
simulated function QuiescePostMissionHUD()
{
    if (bPostMissionQuiesced)
        return;
    bPostMissionQuiesced = true;
    if (ScoreCounter != none)
        ScoreCounter.ResetCache();
    CachedScoreHistory = none;
    CachedScoreHistoryIndex = -1;
    bScoreTextValid = false;
    bScoreReadDeferred = false;
    ScoreRefreshRemaining = 0.0;
    RefreshRemaining = 0.0;
    `log("HUD quiesced after native tactical end|revision=mission-report-v55"
        $ "|autoplay_controller_retained_for_final_record=True",
        true, 'AutoplayXCom2');
}

/**
 * Determine HUD readiness at each entry point, including a callback before
 * the first tick after mission end. Stock HasTacticalGameEnded reads both
 * replay state and tactical history. Validate their world and owners before
 * querying native state. Startup can be retried, while end and loss of
 * previously active play latch.
 */
simulated function bool CanUpdateTacticalHUD()
{
    local WorldInfo RulesWorld, ReplayWorld;
    local XComGameInfo TacticalGameInfo;
    local X2TacticalGameRuleset Rules;
    local XComTacticalGRI TacticalGRI;
    local bool bInPlay, bCanReadEnd, bEnded;

    if (bIsRemoved || bPostMissionQuiesced)
        return false;
    // The stock TACTICALRULES and REPLAY macros dereference their owners.
    // Resolve equivalent references with checks, including during travel.
    RulesWorld = class'Engine'.static.GetCurrentWorldInfo();
    if (RulesWorld != none && RulesWorld == WorldInfo)
        TacticalGameInfo = XComGameInfo(RulesWorld.Game);
    if (TacticalGameInfo != none)
        Rules = X2TacticalGameRuleset(TacticalGameInfo.GameRuleset);
    bInPlay = Rules != none && Rules.TacticalGameIsInPlay();
    if (bInPlay)
    {
        bSawTacticalInPlay = true;
        ReplayWorld = class'WorldInfo'.static.GetWorldInfo();
        if (ReplayWorld == RulesWorld)
            TacticalGRI = XComTacticalGRI(ReplayWorld.GRI);
        bCanReadEnd = TacticalGRI != none && TacticalGRI.ReplayMgr != none
            && `XCOMHISTORY != none
            && class'APX_MissionScore'.static.CanQueryScoreHistory(true,
                Rules.BuildingLatentGameState, Rules.IsDoingLatentSubmission());
        if (bCanReadEnd)
            bEnded = Rules.HasTacticalGameEnded();
    }
    if (ShouldQuiesceHUD(bSawTacticalInPlay, bInPlay, bEnded))
    {
        QuiescePostMissionHUD();
        return false;
    }
    return bInPlay && bCanReadEnd;
}

/** Restore deferred full intel and refresh the controls only during active tactical play. */
simulated event Tick(float DeltaTime)
{
    if (bIsRemoved || !CanUpdateTacticalHUD())
        return;

    // A tactical reload may reenable stock FOW; restore the user's choice.
    if (class'APX_FullIntel'.default.EnableFullIntel
        && `XWORLD != none && (!bMapRevealInitialized || `XWORLD.bEnableFOW)
        && class'APX_FullIntel'.static.RevealMapForPlayer())
    {
        if (!bMapRevealInitialized)
            `log("Full intel|revision=mission-report-v55|enabled=True|map_revealed=True", true, 'AutoplayXCom2');
        bMapRevealInitialized = true;
    }

    if (default.AlwaysExpanded && !bExpanded)
        Expand();
    if (bPendingCollapse && !default.AlwaysExpanded)
    {
        CollapseRemaining -= DeltaTime;
        if (CollapseRemaining <= 0.0)
            Collapse();
    }

    // With unchanged history, read on a status update after one elapsed second.
    // Status/frame scheduling can add delay; this timer also runs while OFF.
    ScoreRefreshRemaining -= DeltaTime;
    RefreshRemaining -= DeltaTime;
    if (RefreshRemaining <= 0.0)
    {
        RefreshRemaining = 0.25;
        UpdateStatus();
    }
}

simulated event Removed()
{
    // Timers and run state never survive a tactical screen/load transition.
    if (Controller != none)
    {
        Controller.StopAutoplay("HUD removed");
        Controller.Destroy();
        Controller = none;
    }
    if (ScoreCounter != none)
        ScoreCounter.Cleanup();
    ScoreCounter = none;
    bScoreTextValid = false;
    bScoreReadDeferred = false;
    CachedScoreText = "";
    CachedScoreHistory = none;
    CachedScoreHistoryIndex = -1;
    ScoreRefreshRemaining = 0.0;
    super.Removed();
}

defaultproperties
{
    bIsNavigable=false
    bAnimateOnInit=false
    bCascadeFocus=false
}
