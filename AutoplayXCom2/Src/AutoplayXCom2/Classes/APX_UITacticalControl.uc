class APX_UITacticalControl extends UIPanel config(AutoplayXCom2);

// Coordinates use the stock UI's scaled coordinate space. The origin is the
// centre of the right edge; users of other HUD mods can move this entire panel.
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
var UIButton ToggleButton;
var UIBGBox Indicator;
var UIText StatusLabel;
var bool bExpanded;
var bool bPendingCollapse;
var float CollapseRemaining;
var float RefreshRemaining;

simulated function APX_UITacticalControl InitAutoplayControl()
{
    InitPanel('APX_AutoplayControl');
    SetAnchor(class'UIUtilities'.const.ANCHOR_MIDDLE_RIGHT);
    SetPosition(OffsetX, OffsetY);
    SetSize(ButtonWidth + 20.0, 54.0);
    DisableNavigation();

    Controller = class'APX_Controller'.static.GetOrCreate();

    ToggleButton = Spawn(class'UIButton', self);
    ToggleButton.InitButton('APX_ToggleButton', EnableLabel, OnToggleClicked);
    ToggleButton.SetResizeToText(false);
    ToggleButton.SetSize(ButtonWidth, 30.0);
    ToggleButton.SetPosition(0.0, 0.0);
    ToggleButton.DisableNavigation();
    ToggleButton.ProcessMouseEvents(OnControlMouseEvent);

    StatusLabel = Spawn(class'UIText', self);
    StatusLabel.InitText('APX_Status');
    StatusLabel.SetPosition(0.0, 31.0);
    StatusLabel.SetSize(ButtonWidth, 22.0);
    StatusLabel.DisableMouseHit();
    StatusLabel.DisableNavigation();

    // Keep a small hit target alive when collapsed. A zero-alpha or hidden
    // Flash control can stop receiving mouse events, hence a visible sliver.
    Indicator = Spawn(class'UIBGBox', self);
    Indicator.InitBG('APX_Indicator', ButtonWidth + 8.0, 0.0, 8.0, 30.0);
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
    if (bIsRemoved || Controller == none)
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
        Controller.Stop("HUD removed");
        Controller.Destroy();
        Controller = none;
    }
    super.Removed();
}

defaultproperties
{
    OffsetX=-220.0
    OffsetY=-27.0
    ButtonWidth=184.0
    FadeSeconds=0.25
    CollapseDelaySeconds=2.0
    IndicatorAlpha=35.0
    bIsNavigable=false
    bAnimateOnInit=false
    bCascadeFocus=false
}
