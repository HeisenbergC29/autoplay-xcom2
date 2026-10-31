class APX_ScreenListener extends UIScreenListener;

event OnInit(UIScreen Screen)
{
    AttachControl(Screen);
}

event OnReceiveFocus(UIScreen Screen)
{
    AttachControl(Screen);
}

function AttachControl(UIScreen Screen)
{
    local APX_UITacticalControl Control;

    if (UITacticalHUD(Screen) == none)
        return;

    Control = APX_UITacticalControl(Screen.GetChildByName('APX_AutoplayControl', false));
    if (Control == none)
    {
        Control = Screen.Spawn(class'APX_UITacticalControl', Screen);
        Control.InitAutoplayControl();
    }
}

event OnRemoved(UIScreen Screen)
{
    local APX_UITacticalControl Control;

    if (UITacticalHUD(Screen) == none)
        return;

    Control = APX_UITacticalControl(Screen.GetChildByName('APX_AutoplayControl', false));
    if (Control != none && !Control.bIsRemoved)
        Control.Remove();
}

defaultproperties
{
    ScreenClass=class'UITacticalHUD'
}
