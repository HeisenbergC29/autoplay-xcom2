# #107 — raport: przejście po SabotageCC v45 i wyciszanie HUD v46

Baza `main 8bf70809abf9aff3f6425f7738fe15891944b2f9`, runtime
`mission-report-v45` w otrzymanym logu. HELPER gałąź
`helper/107-postmission-hud-quiesce-v46`, ostrożnościowa zmiana
`mission-report-v46`. Natywne Windows make/game **dla v46 NIE URUCHOMIONE**;
source CI nie dowodzi naprawienia zamknięcia gry.

## Materiał i poziom pewności

- Przesłano `AutoplayXCom2-20261121-002406-d1623db0.zip`, ten sam
  `Launch(2).log` (dokładnie identyczne bajty i SHA-256).
  Inne logi ZIP dotyczą wcześniejszych uruchomień, nie wolno ich
  mieszać z aktualną sesją.
- `XCom2.rar` zawiera `XCom2.exe` 32 006 600 B, poprawny
  x64 PE (Machine 0x8664; PE32+), data nagłówka 2022-02-22 UTC.
  To binarka gry, **nie zrzut procesu**, i nie daje instrukcji awarii
  ani stosu. Brak dowodu uszkadzania pamięci.
- Sesja `2026-11-21_1-6-37-221_890`, misja `SabotageCC`,
  start recorder `mission-report-v45`, 4 XCOM jednostki.
  Tura28 ukończono `Neutralize all enemy targets`; tura29
  `Plant X4 charges on the monument` (native
  `Interact_PlantBomb` w wynikach).
  962,17s APXREC `end reason=tactical_game_ended outcome=win
  history=3265 history_pending=0` i
  `Stopped: Mission ended or world changed`. **Brak następnych
  decyzji, ruchów ani prób `PerformEndTurn` wykonanych przez autoplay.**
  To przeczy hipotezie, że automat *na pewno* nadal wydawał rozkazy
  po zwycięstwie.
- 982,51s stock `X2TacticalGameRuleset.EndTacticalGame`.
  988,82s i 989,34s stock
  `NextSessionCommand` zapisuje
  `GetSingleGameStateObjectForClass FAILED: XComGameState_LadderProgress`.
  989,34s stock AIGroup/behavior kończy asynchroniczny `StandardMove`;
  ostrzeżenia `Game State Created but Never Added to History`
  i `Game State Added to History Without Known Creation`.
  Może to być niespójność podczas natywnego teardown; w logu
  nie ma dowodu, że jej autorem jest mod.
- 990,56s **stock `Avenger_Root` ładuje się pomyślnie**.
  Potem przez kilkadziesiąt sekund są zdarzenia UI Avengera.
  Dopiero 1093,98s `Failed; returning to Entry` i 1094,97s
  stock `XPACK_Shell_Intro` prawidłowo startuje.
  Ostatni zapis `Launch.log` 1095,62s; **brak**
  `Fatal error`, `Critical`, `Unhandled Exception`,
  minidumpu i systemowego Windows Event ID w tym materiale.
  Nie można na podstawie samego logu uznać, czy proces
  zakończył się przez crash, zamknięcie/wyjście do menu,
  czy błąd natywnej sesji strategicznej po wejściu do Avengera.
- Porównanie z pełnym prywatnym WOTC SDK:
  `X2TacticalGameRuleset.uc` około l.5165–5200 i 5311–5370:
  `EndTacticalGame::NextSessionCommand` oraz
  `LadderProgress.MaybeDoLadderProgressionChoice`
  są częścią oryginalnej implementacji Firaxis.
  Brak tego obiektu bywa obserwowany poza trybem Ladder;
  nie tworzyć go z moda ani nie modyfikować history w celu
  ukrycia ostrzeżenia.

## Zidentyfikowane ryzyko źródłowe, bez twierdzenia o przyczynie crashu

Dotychczasowy `APX_UITacticalControl.Tick` wykonywał
`APX_FullIntel.RevealMapForPlayer` oraz
`UpdateStatus -> GetDisplayedScoreText -> APX_MissionScore.GetText`
aż do stock `UIPanel.Removed`. HUD może jeszcze istnieć,
gdy `TACTICALRULES.HasTacticalGameEnded` jest już true.
`APX_Controller.Tick` osobno **prawidłowo** robi
`MissionRecorder.Finish`, wypisuje native WIN,
odpina swoich czterech listenerów oraz `StopAutoplay`.
Nie ma potrzeby niszczyć kontrolera wcześniej.

## Wprowadzony minimalny guard

- `ShouldQuiesceHUD(bEverInPlay,bInPlay,bEnded)`:
  czysta, wykonywalna funkcja UC. W pierwszym frame przy
  jeszcze nieaktywnym `TacticalGameIsInPlay` zwraca false;
  po zakończeniu natywnej sesji lub utracie wcześniej aktywnej
  sesji zwraca true. Alien/visualizer/hack waits nadal są
  w obrębie aktywnej gry.
- `QuiescePostMissionHUD`: idempotentnie zeruje WYŁĄCZNIE
  cache odczytów UI i `APX_MissionScore.ResetCache`, bez
  zapisu `XComGameState`, wywołania akcji, mutacji squad,
  modyfikacji FullIntel, zmiany punktacji lub
  `Controller.Destroy()`. Loguje jednokrotnie
  `HUD quiesced after native tactical end`.
- `Tick` testuje wyłącznie natywną fazę, po jej końcu
  nie wywołuje score history ani RevealMap.
  `UpdateStatus`, `GetDisplayedScoreText`,
  `OnToggleClicked`, `OnControlMouseEvent` są również
  wstrzymane, jeżeli asynchroniczny callback przyjdzie
  z nieusuniętego jeszcze HUD. Stock `Removed` nadal
  wykonuje rzeczywisty Cleanup/Destroy.
- Odrębny `Controller.Tick` nadal ma szansę wykonać
  końcowy `MissionRecorder.Finish` przed własnym
  `StopAutoplay`, więc nie zamieniamy WIN na
  UNKNOWN przez przedwczesne usuwanie rejestratora.

## Testy i kryterium próby Windows

`tests/test_postmission_hud_quiescence_v46.py` wykonuje
prawdziwy pure UC predykat dla wszystkich stanów cyklu oraz
kontroluje źródłowo pełny przepływ, kolejność guardów,
brak odczytów po end, callbacki, odpinanie listenerów
i prawidłowe zachowanie stock `Removed`.
Publiczne testy nie uruchamiają natywnego runtime.
Jedno E2E po scaleniu przez LEAD:
(1) kompilacja WOTC i log dokładnego commitu,
(2) przejście tej samej misji, potwierdzenie
`APXREC end=win`, jeden marker wyciszenia HUD,
brak późniejszych markerów decyzji ani score/map reveal,
(3) odczekanie >3 minut po powrocie do Avengera
bez dotykania menu; rozróżnienie pozostania w Avengerze,
przejścia do Shell i zakończenia procesu,
(4) gdy Windows zamknie grę, zebrać
**Windows Event Viewer → Windows Logs → Application**
(faulting module, exception code, timestamp)
oraz WER `CrashDumps\XCom2.exe.*.dmp` lub
`XCom2.exe.*.mdmp`, jeżeli system utworzył,
łącznie z datą/wersją i bez upubliczniania
pełnego dumpu/ścieżek. Test A/B z modem wyłączonym
tylko przy dalszej niejednoznaczności.
Nie próbować naprawiać `LadderProgress` przez
dodanie fałszywego stanu gry.

W tym eksperymencie brak obietnicy wyeliminowania crashu:
jest to bezpieczniejsze zachowanie observera
podczas przejścia między mapami, a faktyczne
źródło `Failed; returning to Entry` pozostaje nieustalone.
