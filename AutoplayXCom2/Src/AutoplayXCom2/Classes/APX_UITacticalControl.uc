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

simulated function APX_UITacticalControl InitAutoplayControl()
{
    InitPanel('APX_AutoplayControl');
    SetAnchor(class'UIUtilities'.const.ANCHOR_MIDDLE_RIGHT);
    SetPosition(OffsetX, OffsetY - 31.0);
    SetSize(ButtonWidth + 20.0, 85.0);
    DisableNavigation();

    Controller = class'APX_Controller'.static.GetOrCreate();
    ScoreCounter = new(self) class'APX_MissionScore';

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

simulated function OnToggleClicked(UIButton Button)
{
    if (Controller != none)
    {
        Controller.Toggle();
        UpdateStatus();
    }
    Expand();
    ScheduleCollapse();
}

simulated function OnControlMouseEvent(UIPanel Panel, int Cmd)
{
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
    bPendingCollapse = true;
    CollapseRemaining = FMax(0.25, CollapseDelaySeconds);
}

simulated function Collapse()
{
    bExpanded = false;
    bPendingCollapse = false;
    // Only the slim indicator may intercept the battlefield while collapsed.
    ToggleButton.DisableMouseHit();
    ToggleButton.RemoveTweens();
    StatusLabel.RemoveTweens();
    ToggleButton.AddTween("_alpha", 0.0, FMax(0.01, FadeSeconds));
    StatusLabel.AddTween("_alpha", 0.0, FMax(0.01, FadeSeconds));
}

simulated function UpdateStatus()
{
    // UIText caches its HTML, so unchanged score/font values do not issue
    // another Flash update. Keep this independent of autoplay's run state.
    if (ScoreCounter != none && ScoreLabel != none && ToggleButton != none)
        ScoreLabel.SetCenteredText(class'UIUtilities_Text'.static.GetColoredText(
            ScoreCounter.GetText(), eUIState_Normal, ToggleButton.FontSize));

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

simulated event Tick(float DeltaTime)
{
    if (bIsRemoved)
        return;

    if (bPendingCollapse)
    {
        CollapseRemaining -= DeltaTime;
        if (CollapseRemaining <= 0.0)
            Collapse();
    }

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
    ScoreCounter = none;
    super.Removed();
}

defaultproperties
{
    bIsNavigable=false
    bAnimateOnInit=false
    bCascadeFocus=false
}
