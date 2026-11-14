# #88 / v40 — ograniczona proaktywna zasadzka patrolowa

Baza: `main f4783eb169ae4138b0e5d76554abf968226252cb`, runtime
`mission-report-v39`. Gałąź HELPER: `helper/88-patrol-ambush-v40`.
Zmiana runtime wprowadza marker `mission-report-v40`.
Skończona kolejka przed wspólnym testem: [#86](PREBUILD-QUEUE.pl.md).
Windows WOTC SDK make/game: **NOT RUN**; [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4)
nadal **BLOCKED** na wyraźne polecenie użytkownika. Po PR nie wydawać
polecenia oddzielnej kompilacji.

## Kontrakt — rzeczywiste dane a hipotezy

`APX_ContactEnvelope.BuildSnapshot` przegląda raz na decyzję
aktualnych, natywnie zweryfikowanych członków grup i zapisane
waypointy (`APX_PatrolKnowledge.StoredPatrolEvidence`, AI clock).
Od v40 przekazuje z **tego samego skanu** ID jednej zweryfikowanej
grupy i jej rzeczywiście bieżący waypoint. Gdy kilka grup ma
takie dowody, wybiera najbliższy **zweryfikowany waypoint**
względem aktualnej pozycji własnego scouta, bez zależności
od kolejności indeksów `AIGroup`; budżet wspólny pozostaje
niezmieniony. Nie wywołuje
`ShouldMoveToIntercept`, `ComputeGroupPath`, `GetGroupMovePaths`,
`GetNextDestination` ani RNG. Te procedury gry mogą wybierać nowe
punkty przez native `BuildEncounterZone`, zależne od aktualnego
XCOM, override job/BT, losowany narożnik i osobne trasy członków.
Znany waypoint nie jest wieloturową wybraną trasą.

`APX_PatrolAmbushPlanner.CountVariantLanes` bada trzy ograniczone
punkty: bieżący waypoint i przesunięcia X+2/Y+2 jako **geometrie
alternatywnych korytarzy**, nie udowodnione cele patrolu.
Samo native `CanSeeTileToTile` i aktualny zasięg własnego żołnierza
dają wyłącznie potencjalne pokrycie geometryczne. Przyszły kontakt,
pełny footprint grupy, wyniki przyszłego concealment oraz faktyczny
movement trigger pozostają **Unknown**, nigdy Clear/pewny ambush.
Historyczne `GetCurrentPatrolWaypoint` zapewnia aktualny punkt
i rzeczywistych żywych członków, nie przewiduje ich przyszłego LOS.

## Zachowanie wdrożone

1. **Plan per epoch** w runtime-only obiekcie `APX_PatrolAmbushPlanner`.
   Przechowywane: `XCOMHISTORY`, start-history, BattleID, player ID,
   historia ostatniego przeglądu, aktualny native group ID/waypoint,
   tura początku, liczba wykonanych ruchów i OW, faza.
   Fazy `approach / setup / armed / open / abort`.
   Reset: manual OFF, inny battle/player/history/start-index, rewind
   historii albo zmiana celu/grupy. Zmiana realnego kontaktu/timera
   powoduje przerwanie, a nie twierdzenie, że poprzednia prognoza
   nadal obowiązuje. Gdy patrol wypada z listy green-alert po
   zaalarmowaniu, możliwe jest przejście do otwarcia **wyłącznie**
   gdy bieżący native `GetImmediateThreats` zawiera członka
   wcześniej zweryfikowanej grupy (skan max24 jednostki)
   i poprzedni limit tur nadal obowiązuje. Nie jest to
   odczyt przyszłej trasy.
2. **Wygasanie:** `MaxSetupTurns=2` liczy *własne* tury od rozpoczęcia;
   `MaxSetupActions=3` ogranicza liczbę własnych przygotowawczych
   ruchów, `MaxReactionSupport=3` liczbę aktywnie przygotowywanych
   OW. Po czasie i braku możliwości kontynuacji phase=abort.
   `bExpired` uniemożliwia restart tej samej grupy/waypointu aż do
   rzeczywistej zmiany kontekstu; nie ma nieskończonego stania
   i resetowania zegara przez kolejne decyzje. Po wykonaniu
   **rzeczywistego zaakceptowanego** niebieskiego podejścia możliwe
   jest jedno ograniczone oczekiwanie w kolejnej własnej turze
   poprzez zwykły `RequestEndTurn`, gdy brak konstruktywnego
   ruchu i nadal nie wystąpił timer/ratunek/evac/kontakt.
   Bez rzeczywistego podejścia lub po wyczerpaniu tego okna
   działa normalny `StatusNoPlan`/watchdog, nie sztuczne
   zawieszanie lub wymyślona akcja OW.
3. **Podejście** tylko dla aktywnego własnego żołnierza o min. 2 AP,
   native legal `StandardMove` i native legal affordable OW,
   w dystansie 4–15 pól od waypointu, poza bezpośrednim kontaktem,
   ewakuacją, timerem i ratowaniem krwawiących. Sampling max24
   z natywnych reachable tiles; koszt najwyżej native blue mobility,
   cały `BuildPathToTile` przechodzi `APX_SquadPlanner.PreparationPathIsSafe`
   (hazard, support, visibility, destructive traversal,
   concealment checks), a następnie wspólny read-only
   `APX_ContactEnvelope.AssessRoute` dla bieżącego horyzontu.
   Potwierdzony contact Caution odrzuca przygotowawczy ruch;
   Unknown pozostaje jawny i kosztowny, bez certyfikacji przyszłości.
   W punktacji użyto zysku dystansu, kierunku osłony od waypointu,
   geometrycznego pokrycia kilku wariantów, `SquadPositionScore`
   (w tym AoE separation), bieżącego ExposureRisk i kosztu.
   To jedynie kandydat konkurujący z normalnym ConstructiveMove;
   nie przymusowy marsz, nie usunięcie natywnej trasy awaryjnej.
   Normalny konstruktywny plan musi mieć wartość poniżej 80,
   wariant staging musi poprawiać ją o >6; Blood Killer
   `SabotageTransmitter` nie bierze udziału w tej zmianie trasy.
   Własny wielopolowy żołnierz bez pełnego footprint
   nigdy nie jest pozycjonowany przez anchor LOS v40.
4. **Faktyczny opener przed OW:** tylko gdy obecnie wybrany
   `AvailableAction` jest natywnie legalnym `StandardShot`,
   `PistolStandardShot` albo `SniperStandardFire` na realnie
   widocznego membera aktualnie wybranej grupy, a inny własny
   żołnierz ma natywny `FindOverwatch`, rzeczywistą linię LOS
   do TEGO celu i koszt affordable. Dla wielopolowego
   wroga lub jednostki wsparcia pojedynczy LOS do anchor
   nie wystarcza: zrezygnujemy z tego dodatkowego OW,
   pozostawiając normalny native legal direct shot.
   Co najmniej 2 aktywne
   potencjalne reaction lanes; max3 i budget LOS dzielony
   z resztą jednej decyzji. W revealed mode dobry bezpośredni
   strzał (score>60) nie jest wstrzymywany na rzecz OW.
   Po potwierdzonym own dispatch faza przechodzi w `armed`
   lub `open` — nic nie jest uznane za odpalone wyłącznie
   przez analizę kandydatów. Legacy
   `APX_SquadPlanner.ChoosePreparation` nadal wspiera inne
   przypadki concealed.
5. **Bezpieczeństwo:** inicjalizacja i kandydaci nie modyfikują
   native state, nie wywołują przyszłego AI ani RNG. Do dispatch
   nadal obowiązuje standardowy Controller:
   `CanUseMove`, `CanUseAction`,
   `GameStateMoveUnitSingle`,
   `ActivateAbility_ReturnContext`. Nie tworzy się fikcyjnych
   AP, ammo, hit chance ani target refs. `!FullIntel`, epoch
   invalid, stale patrol, unknown selected group powodują abort.
   Przede wszystkim: ratunek, aktywny timer, evacuation,
   realny combat i objective mają priorytet. Gdy nie ma legalnego
   opener, nie uzbrajamy ślepego Overwatch.

## Niezrealizowane i odkładane do gry

Nie przewidujemy dokładnego przyszłego patrolu, scamper,
`OverwatchShot` trigger, pewnego concealment po przyszłym
przesunięciu wroga ani natywnych przyszłych hitów. Zmienny
`BuildEncounterZone` nie ma dostępnego ciała C++; narożniki
X+2/Y+2 to hipotezy do rankingu, NIE rekonstrukcja dokładnego
natywnego wyboru. Multi-tile jednostki i nieznany przyszły
footprint pozostają Unknown zgodnie z #87; obecne
`AssessRoute` nadal jawnie zwraca Unknown dla nieobsługiwanych
footprintów. Możliwe, że model wybiera zbyt często trasę
alternatywną lub odrzuca przygotowanie przy budżecie/Unknown;
wolniejszy, bezpieczny fallback jest zamierzony. Brak silnika
Windows w CI i brak raportu nowej rozgrywki nie pozwalają
ogłosić scenariusza zwycięskiego.

## Testy i wspólna próba po zakończeniu #86

`tests/test_patrol_ambush_v40.py` uruchamia z prawdziwego
UnrealScript numeryczne polityki stage/native opener
i kontroluje źródłowo epoch/reset, fakt użycia jednego contact
snapshot, pełne legalne blue path, warianty, natywne legal OW,
aktualny native shot target, budżety, brak RNG/mutacji oraz
właściwą ścieżkę dispatch.

Przy pojedynczym końcowym Windows WOTC make po #86:
- raportowanie `patrol_ambush_state` / `patrol_ambush_approach`
  / `patrol_ambush_arm` i faktycznych native chosen/accepted;
- dwa konkurujące korytarze, cover direction, rozstawienie
  dwóch/trzech własnych OW i brak stanowiska przy niewystarczającym
  AP/ammo/native target;
- actual movement XCOM i wroga, zmiana waypointu, kontakt,
  OFF/ON, reset, rewind, akcja ostatniego AP, duży footprint;
- native timer/bleeding/evac/X4/Sweep wyprzedza ryzykowny setup,
  brak blokady jedynej legalnej ścieżki; max2 własne tury
  bez nieskończonego ponawiania;
- natywny wynik misji i faktyczne punkty >0 jako
  **odrębny** warunek projektu. Zielone source tests
  nie zastępują tych wyników.
