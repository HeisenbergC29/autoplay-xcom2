# Pliki potrzebne do sprawdzenia i kompilacji

Nie wysyłaj całej gry, zapisów Steam, tokenów ani danych konta. Gra i SDK nie są instalowane w linuksowym środowisku projektu.

**Źródła SDK oraz konfiguracje gry, SDK i pięciu dodatków z gry zostały już otrzymane.**
Nie trzeba ponownie wysyłać `SrcOrig.rar`, `Development.rar`, `Config.rar`
ani `Config sdk.rar`, ani archiwów `game dlc_1`, `game dlc_2`, `game dlc_3`,
`game tle` i `game XCom_DLC_Day0`. Wynik opisują [audyt SDK](SDK-AUDIT.pl.md),
[konfiguracje v14](config-knowledge-v14.pl.md) oraz
[uzupełnienie DLC](dlc-config-knowledge.pl.md). Następny potrzebny wynik to
rzeczywista kompilacja bieżących źródeł na Windows i raport z gry:
przy sukcesie `dist\AutoplayXCom2.zip`, przy błędzie logi z `.build`.
RAR jest poprawnym formatem załącznika.

## Otrzymane konfiguracje

`Config.rar` zawiera domyślne pliki gry, a `Config sdk.rar` pliki SDK.
Siedem istotnych plików `Default` jest identycznych; wygenerowane ustawienia
`XCom*.ini` z SDK nie są nakładane na konfigurację gry. Otrzymane pliki
wystarczają do obecnego audytu bazowych statystyk, loadoutów, broni i AI.

Otrzymane później archiwa `DLC_1`, `DLC_2`, `DLC_3`, `TLE`
i `XCom_DLC_Day0` zawierają łącznie 79 plików INI z gry. W tej instalacji
SDK nie ma katalogu konfiguracji DLC; nie jest on potrzebny do tego audytu.
Pliki `XCom*.ini` w katalogach dodatków gry są wejściem audytu DLC.
Nie należy utożsamiać ich z wygenerowanymi ustawieniami SDK tylko ze względu
na nazwę pliku.

Brak osobnej sekcji INI nie dowodzi braku statystyki lub przedmiotu.
Wartość może pochodzić z kodu lub dziedziczenia; część postaci nie potrzebuje
zestawu wyposażenia. Dwa nierozwiązane odwołania obrażeń proxy Feral MEC
pozostają opisane w [zakresie danych DLC](dlc-config-knowledge.pl.md).
Nie ma podstaw do proszenia o kolejne archiwa wyłącznie z ich powodu.

## Lokalizacja źródeł SDK

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
