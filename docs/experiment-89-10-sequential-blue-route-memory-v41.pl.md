# #89 + #10 / v41 — sekwencyjny natywny marsz i miękka pamięć spokojnych tras

Baza `main e3d9c6af356286baf46f8fe357c4dbd4fa3947d1`, marker
`mission-report-v40`; wspólny PR HELPER na
`helper/89-safe-sequential-march-route-memory-v41`, marker `mission-report-v41`.
To wspólne źródłowe wykonanie [#89](https://github.com/HeisenbergC29/autoplay-xcom2/issues/89)
i [#10](https://github.com/HeisenbergC29/autoplay-xcom2/issues/10) z
ograniczonej kolejki [#86](PREBUILD-QUEUE.pl.md).
Windows WOTC SDK make/game: **NOT RUN**; #4 **BLOCKED** do końca kolejki.

## Rozstrzygnięcie na rzeczywistym WOTC SDK

Źródła prywatnego SDK wskazują faktyczną drogę księgowania AP:
- `XComTacticalController.uc:1194–1244` oblicza
  `PathData.CostIncreases` na podstawie **kolejnych kosztów
  `GetPathCostToTile`** i progów aktualnego `XGUnit.GetMobility`.
- `X2AbilityCost_ActionPoints.uc:97–134` liczy native
  `iPointsToTake` na podstawie faktycznie osiągniętej pozycji
  i tych `CostIncreases`, po czym zużywa dokładne dozwolone typy
  punktów. `GetPointCost` samego `StandardMove` nie opisuje
  ceny całej dowolnie długiej ścieżki.
- `XComGameState_Unit.uc:6490–6501` ma natywne
  `NumActionPointsForMoving`, a `X2ReachableTilesCache.uc:68–94`
  udostępnia `IsTileReachable`, `GetPathCostToTile`,
  `BuildPathToTile` i własny cache z prawdziwą ścieżką.

**Nie implementuję nieudowodnionego pojedynczego dasha.**
Sam `StandardMove AA_Success`, `2 × Mobility`, prosty wektor
do celu i odległość do endpointu nie są certyfikatem kosztu
każdego tile, przejścia, interakcji ani ryzyka aktywacji.
Pojedynczy natywny wieloprogowy ruch ze specjalnymi punktami
wymaga niezależnego dowodu i weryfikacji native cache dla
całego odcinka, a nie rekonstruowanego kosztu. W #89 wdrożono
wąską, obserwacyjną alternatywę: **dwa osobno zaakceptowane
natywne ruchy blue w tej samej własnej turze**, z pełnym
ponownym przeliczeniem świata i legalności przed drugim ruchem.
Nie zwiększają AP ani prędkości jednostki; tylko wykorzystują
drugie posiadane AP do pewniejszego postępu, zamiast automatycznie
rezerwować je na OW/bezcelowy koniec tury. Przy niepewności
pozostaje dotychczasowy blue+OW/interaction/wycofanie.

## Implementacja #89: właściwa sekwencja

1. `APX_RouteTempo` tworzy bilet wyłącznie **po rzeczywistym
   sukcesie `GameStateMoveUnitSingle`** w Controller, dla
   wybranego zwykłego `APX_MissionPlanner.ChooseMove`.
   Na początku pierwszego ruchu wymaga ≥2 standardowych AP
   **i** `NumActionPointsForMoving() >= 2`. Jednostki z jednym,
   wyłącznie specjalnymi czy rezerwowymi AP nie dostają tego biletu.
2. Pierwszy ruch jest rzeczywistą natywną ścieżką z blue-range
   cache (`IsTileReachable` + `GetPathCostToTile <= GetMobility` +
   `BuildPathToTile`). Cel i początek zgadzają się z bieżącą
   jednostką/Historią, a cała ścieżka przechodzi dotychczasowe
   native hazard/support, LOS, interactive/civilian,
   destructive traversal i concealment checks. Bilet ma
   `bFirstBlueClear` tylko jeśli nowy `APX_ContactEnvelope`
   zwrócił **current-horizon Clear**, `ExplosiveCoverRisk=0`,
   brak niepewnego concealment oraz **każdy tile** ma
   `ExposureRisk <= StartRisk+3`. Limit kontroli exposure: 64
   pola. `BlueRouteExplosiveSafe` dodatkowo sprawdza
   `APX_ExplosiveCoverKnowledge.RiskAtTile` dla **każdego**
   przebywanego pola z jednej, współdzielonej między żołnierzami
   i kandydatami puli `MaxTempoCoverChecks=48`.
   Jej wyczerpanie (lub wyczerpanie pozostałych budżetów)
   nie certyfikuje przyspieszenia: wynik tempo jest odrzucony.
   Dotychczasowa kara za eksplodującą osłonę w zwykłym
   ruchu pozostaje niezależna; nie ma mowy o zatrzymaniu
   wszystkich legalnych standardowych tras.
   To samo obejmuje nowy drugi odcinek; ryzykowny
   środkowy tile nie jest unieważniany przez spokojny endpoint.
   Sama historyczna `MemoryFallbackPath` z oceną Unknown nie
   nadaje prawa do drugiego ruchu. Unknown/stale/budget exhausted/unsupported footprint
   nigdy nie daje biletu, nawet gdy bezpieczny jest endpoint.
3. Po zakończeniu/zaakceptowaniu pierwszego ruchu nowa decyzja
   Controller pobiera aktualny native `UnitState` i reachable
   cache, tworzy nowy contact snapshot i sprawdza, czy ostatni
   zaakceptowany przejazd tej samej jednostki, celu i własnej
   tury kończy się dokładnie na obecnym polu. Drugi ruch wymaga
   `NumActionPoints()==1`, `NumActionPointsForMoving()>=1`,
   bieżącego legalnego `StandardMove` i pełnego bezpieczeństwa
   **nowej, już wybudowanej blue trasy**. Jeśli brak Clear,
   pojawił się wróg, patrol/LOS niepewny, hazard, osłona wybuchowa,
   nadmierna ekspozycja lub ograniczenie budżetu — drugi ruch
   zostaje odrzucony; **stary RiskyRoute i LocalFallback
   nie mogą go przywrócić**. Następny ruch nigdy nie jest
   przewidywany i wysłany przed potwierdzeniem pierwszego.
4. Bramka `APX_RouteTempo.IsRoutineTempoContext` rozdziela
   rzeczywistą pilność od ukrycia. Zarówno **ujawniony**, jak
   i ukryty żołnierz może otrzymać pierwsze/dozwolone drugie
   blue, jeżeli faktyczna obecna trasa pozostaje Clear po
   `APX_ContactEnvelope`, exposure, explosive cover i
   odpowiednich native sprawdzeniach. Stara flaga
   `ConcealmentIsUrgent` obejmuje samo `!IsConcealed()`;
   jej użycie jako tempo veto błędnie odcinało całe
   ujawnione jednostki — naprawione i sprawdzone testem.
5. Sekwencja ustępuje każdej już legalnej natywnej
   `ChooseInteraction`: nie wydaje AP potrzebnego na gotowe
   Interact/Hack/Plant. Jest wyłączona dla aktywnego/recent contact,
   rzeczywiście staged/armed zasadzki, wykrwawiania, ewakuacji,
   aktywnego timera, zatrucia wymagającego ucieczki, combat
   reposition i SabotageTransmitter/X4. `HasActiveStaging`
   rozróżnia przyjęte ruchy/reakcje od samotnej obserwacji
   odległego waypointu w fazie `approach`; obecność samego
   waypointu nie zamraża nawigacji. Każdy priorytetowy
   native attack/interaction/ratunek i tak konkuruje w normalnym
   `MakeDecision` przed dispatch.

**Ważne ograniczenie:** Clear na bieżącym horyzoncie nie
certyfikuje przyszłej tury wroga, scripted spawn lub gotowego
wrogiego reaction. WOTC Windows/game acceptance jest odroczony,
więc nie deklarujemy braku niespodziewanej aktywacji lub
realnego zysku w liczbie tur bez logów gry.

## Implementacja #10: pamięć bez blokowania jedynej drogi

`APX_RouteTempo` przechowuje maksymalnie 96 własnych
`RouteVisit` (UnitID, FromTile, ToTile, GoalTile, own Turn,
`bFirstBlueClear`). Wygasają po maksymalnie trzech własnych
turach; reset scope obejmuje `XCOMHISTORY`, start history,
BattleID, PlayerID i rewind, a każda zmiana celu oddzielnie
czyści stare wpisy danej jednostki. Manual OFF/Destroyed
wywołują `Reset`. Żadna pamięć nie jest zapisywana do save
ani nie kopiuje pozycji wroga.

`PenaltyFor` dodaje malejącą, ograniczoną **miękką**
karę za powrót na pole poprzedniego startu (A–B–A,
28/21/14/7 punktów w kolejnych 4 instancjach tury)
i mniejszą karę za ponowne odwiedziny punktu B
(`RevisitTilePenalty=12`). Nie ma `return false`
blokującego legalny tile. Kary rankingowe obejmują
native A* `ChooseRoutePrefix`, lokalne legalne alternatywy
w `ChooseMove` oraz spokojny `ExplorationPlanner`.
Bezpieczny powrót jest przechowywany jako
`MemoryFallbackPath`; jeśli nie ma dostatecznie
użytecznego legalnego alternatywnego ruchu, pozostaje
legalny backtrack. Stary hard filter pozostaje wyłącznie
w `VisitedPositions` bieżącej tury (bez wprowadzania
odrzuconego cross-turn hard ban PR #11). Dodatkowy, wąski
wyjątek od tego historycznego filtra dopuszcza rzeczywisty
powrót w sytuacji pilnej ewakuacji, wykrwawiania towarzysza,
aktywnego timera lub koniecznego wyjścia z trucizny, nadal
pod pełną kontrolą legalności natywnego ruchu.
Po ewakuacji, walce, ratunku lub wejściu w hazard pamięć
nie blokuje zachowania mechaniki; przy zmianie celu
wspólny kontekst przestaje obowiązywać.

## Odbiór źródłowy i odroczona macierz gry

`tests/test_route_tempo_v41.py` uruchamia rzeczywiste,
czyste funkcje UC (`CanUseSecondBlue`, `SoftVisitPenalty`,
`IsRoutineBlueExposureAllowed`) z kontrprzykładami.
Testy źródłowe weryfikują rzeczywisty dispatch, brak
dopuszczenia `out bool`, pełny native blue cache,
nielegalne Unknown/fallback, aktualną turę i cel,
realne `RecordAccepted`, pamięć w exploration,
reset i bramkę aktywnej zasadzki. Kontrakty prywatnego
SDK testuje opcjonalny test, który jest jawnie SKIP
w publicznym CI.

W jednej końcowej rundzie po #86 zbadać:
- zwykły 2AP XCOM move dwukrotnie blue do celu versus
  1AP/special-only, native cache z niedostępnym polem,
  przeszkoda/wall detour i koszt > Mobility;
- Clear obecny + pełny środek bez ryzyka kontra
  bezpieczny endpoint z niebezpiecznym środkiem,
  native LOS/civilian/detector, wyczerpany budżet,
  stale waypoint, FOW=false i multi-tile;
- aktywne staged OW versus zwykły odległy waypoint,
  świeży/recent kontakt, pilny timer/bleeding/evac,
  X4/interakcja i poison escape;
- A–B–A przez dwie/trzy własne tury, zmiana celu,
  rewind, OFF/ON, jedyna legalna droga powrotna,
  zero świeżych pól w exploration i brak StatusNoPlan
  w sytuacji, gdy rzeczywiście można wrócić;
- native accepted source, rzeczywiste zmiany AP i
  końcowy native mission score. Żadna liczba
  `observed_v3_partial` nie certyfikuje oficjalnego
  wyniku bez pełnej native parity.
