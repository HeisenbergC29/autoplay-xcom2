# Pliki potrzebne do sprawdzenia i kompilacji

Nie wysyłaj całej gry, zapisów Steam, tokenów ani danych konta. Gra i SDK nie są instalowane w linuksowym środowisku projektu.

## Najpierw źródła SDK

Zainstaluj **XCOM 2 War of the Chosen Development Tools** ze Steam. Typowa lokalizacja:

```text
C:\Program Files (x86)\Steam\steamapps\common\XCOM 2 War of the Chosen SDK\
```

Jeśli bibliotekę Steam masz na innym dysku, zastąp początek ścieżki. Potrzebne są pliki `.uc` i `.uci` z:

```text
<SDK>\Development\SrcOrig\
```

Gdy nie ma `SrcOrig`, użyj `<SDK>\Development\Src\`. Najważniejsze nazwy i podkatalogi:

```text
Core\Globals.uci
Engine\Classes\Actor.uc
Engine\Classes\Input.uc
Engine\Classes\PlayerInput.uc
XComGame\Classes\X2GameRuleset.uc
XComGame\Classes\X2TacticalGameRuleset.uc
XComGame\Classes\X2TacticalGameRulesetDataStructures.uc
XComGame\Classes\XComGameStateContext_Ability.uc
XComGame\Classes\XComGameState_Ability.uc
XComGame\Classes\XComGameState_Unit.uc
XComGame\Classes\XComGameState_BattleData.uc
XComGame\Classes\XComGameState_InteractiveObject.uc
XComGame\Classes\XComGameState_EvacZone.uc
XComGame\Classes\XComTacticalController.uc
XComGame\Classes\X2ReachableTilesCache.uc
XComGame\Classes\X2PathSolver.uc
XComGame\Classes\UITacticalHUD.uc
XComGame\Classes\UIHackingScreen.uc
XComGame\Classes\UIPanel.uc
XComGame\Classes\UIButton.uc
XComGame\Classes\UIScreenListener.uc
```

Najłatwiej spakować całe źródła SDK — weryfikacja potrzebuje też typów bazowych i makr. Możesz użyć:

```powershell
.\tools\collect-sdk-sources.ps1 -SdkPath 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK'
```

Powstanie `sdk-for-review.zip` w katalogu repozytorium. **Załącz ten ZIP jako plik do tej rozmowy.** Nie dodawaj SDK do repozytorium GitHub.

## Kompilacja wymaga Twojego Windows i SDK

Przesłanie samych źródeł pozwala sprawdzić API, ale nie dostarcza kompilatora. Nie trzeba wysyłać plików wykonywalnych SDK. Uruchom skrypt budowania opisany w README na swoim Windows. Jeśli kompilacja zawiedzie, załącz:

```text
<repo>\.build\mod-make.log
<repo>\.build\base-make.log   (jeśli użyto -BuildBase)
```

Do diagnozy zachowania w grze przyda się log z ostatniej próby:

```text
<Dokumenty>\My Games\XCOM2 War of the Chosen\XComGame\Logs\Launch.log
```

„Dokumenty” mogą znajdować się w OneDrive. Przed załączeniem logów sprawdź, czy chcesz ujawnić występujące w nich nazwy użytkownika i lokalne ścieżki. W zgłoszeniu podaj rodzaj misji, etap, czy były aktywne inne mody i ostatni status autoplaya. Dla oceny przycisku wystarczy zrzut HUD z podaną rozdzielczością; nie jest potrzebny do samej kompilacji.
