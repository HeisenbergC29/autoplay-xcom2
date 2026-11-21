# #106 — SabotageCC v45: cel X4 rozpoznany, sześć zatrzymań planera

Baza `main 8bf70809abf9aff3f6425f7738fe15891944b2f9`,
runtime gry `mission-report-v45`. Kod HELPER:
`helper/106-verified-x4-native-detour-v46`.
Równolegle #107 / PR #108 (wyciszenie HUD po misji),
bez wspólnych plików z tym PR. Po integracji obu LEAD
synchronizuje wspólną rewizję recorder/panel/DLC;
nie twierdzić, że ten osobny PR sam był Windows-buildem.

## Źródłowy dowód z rzeczywistej próby (prywatne pliki)

Archiwum użytkownika z 21.11.2026 `AutoplayXCom2-20261121-002406-d1623db0.zip`
i identyczny `Launch(2).log`, SabotageCC
`session=2026-11-21_1-6-37-221_890`.

- Tura19, decyzje **115, 116, 117, 118, 119** i
  tura20, decyzja **120**: sześć
  `autoplay_stop: SabotageCC: no currently verified native X4 route`.
  Przejścia `phase=manual` potwierdzają grę wspomaganą
  ręcznie. W trakcie nastąpił m.in. stock
  `StandardMove` żołnierza415 (history2218),
  potem decyzje Overwatch i przejście do tury20.
- Kontrolny log `Native plant approach` dla każdej
  własnej jednostki wykrył `plant_actors=1,
  eligible_actors=1, ready_actors=1,
  goal_found=True, object=897,
  reason=native_plant_interaction_point`,
  geometry=(40,34,2). To **nie był**
  problem braku rozpoznania aktora czy celu.
- `SabotageCC objective recovery` w D115 i D116:
  każda jednostka 409/415/421/427 skanowała
  `native_samples=48`, a `clear_routes=0`.
  Łączne odrzuty dla czterech jednostek:
  5+14+1+17 w pierwszym skanie.
  Brak rozbicia `rejected` w v45,
  więc nie znamy dokładnej przyczyny
  odrzucenia danej ścieżki.
- Tura28: `Neutralize all enemy targets` ukończony,
  tura29: `Plant X4 charges on the monument`
  ukończony; natywny `Interact_PlantBomb`
  faktycznie wykonany; `APXREC end outcome=win`
  history3265 bez oczekujących historii.
  **Nie zalicza benchmarku**:
  ręczne interwencje i **brak**
  `APXREC game_score` z końcową
  potwierdzoną punktacją.
  Ostatni `hud_score=~7400`
  oznacza tylko porównawczy
  `wotc_legacy_config_observed_v3_partial`
  (nie finalną oficjalną punktację).

## Hipoteza kontra fakt

Sprawdzony kod v45
`APX_MissionPlanner.ChooseSabotageCCRecoveryMove`
próbował `GetClosestReachableDestination`
oraz maks48 *równomiernie indeksowanych*
kafli w `GetAllPathableTiles`,
a przed zbudowaniem jakiejkolwiek
realnej trasy odrzucał każdy
endpoint, gdy
`CurrentDistance - TileDistance(Tile, GoalTile) < 1.0`.
W ten sposób konieczny początkowy
objazd ściany — który może wymagać
**tymczasowego oddalenia** — nie ma
szansy przejść do dalszej inspekcji.
To dowiedziony **błąd algorytmicznego
zakresu kandydatów**, ale nie dowód
że każdy odrzucony w logu natywny
kafel należał do dostępnej i
bezpiecznej trasy objazdu.

## Wykorzystanie trasy A* do punktu interakcji

- Rozpoznawanie punktu X4 wywołuje natywne `X2PathSolver.BuildPath`. Planer otrzymuje tę samą trasę bez drugiego wywołania. `HasVerifiedX4AStarGeometry` wymaga poprawnego wyniku rozpoznawania aktora, 2–256 pól, zgodności początku z pozycją żołnierza i końca z punktem interakcji. Przy publicznym markerze planer nadal używa odległości geometrycznej.
- Spośród pierwszych 24 pól trasy planer ocenia najpierw najdalsze w kolejności przejścia. Potem sprawdza najbliższy punkt z natywnego cache i próbkę pozostałych osiągalnych pól. Próbkowanie ma łącznie do 48 pozycji na żołnierza. Powtórzone pola i pozycję początkową pomijamy. Pole odwiedzone wcześniej w tej samej turze odpada przed oceną, dzięki czemu kwalifikuje się kolejny kandydat.
- Przed oceną wybuchowej osłony i przed sprawdzaniem kontaktu planer porównuje długość odtworzonego ruchu z pozostałym budżetem. Pełna ocena kontaktów wymaga sprawdzenia każdego znanego detektora na każdym polu ruchu. Jeśli budżetu nie starczy, krótszy kandydat nadal może zostać zweryfikowany. Budżety pozostają wspólne dla drużyny.
- Dla takiego pojedynczego
  `GoalAStarPath[RouteIndex]` wolno
  dopuścić ujemny przyrost
  **euklidesowej** odległości
  do X4, ponieważ rzeczywiste
  pole należy do trasy A* do celu.
  Ścieżkę do tego pola odtwarza cache
  zasięgu dla bieżącej pozycji.
  `ScoreSabotageAStarDetour`:
  score 22+2×index (bonus max14)
  pomniejszony o obecne ryzyko
  i miękką formację, wyłącznie
  przy current-Clear i
  `risk<=origin+3`.
  Wariant bez stock A* nadal
  wymaga wcześniejszego
  geometrycznego przyrostu
  odległości ≥1 oraz
  `ScoreSabotageRecovery`.
  Brak przyszłego wróżenia RNG.
- **Każdy** wybrany kafel i cała
  obecna trasa muszą być
  zbudowane ponownie przez
  realny *native BLUE*
  `BuildSabotageRecoveryPath`:
  `IsTileReachable`,
  `GetPathCostToTile<=GetMobility`,
  dokładny początek/koniec,
  max48 tile,
  `InspectSabotageStep`
  na KAŻDYM kroku
  (znany tile, hazard,
  aktualne wsparcie,
  `ExposureRisk <= start+3`).
  Nie stosujemy nielegalnego
  `dash` ani nie omijamy
  żadnego kosztu AP.
- Pełny prefix przechodzi potem
  niezmienione
  `APX_ConcealmentPlanner.InspectPathRisk`
  i `BlueRouteExplosiveSafe`
  przy budżecie wspólnym
  Controller, `ContactEnvelope.AssessRoute`
  **Clear** (Unknown/Caution
  odrzucane) i końcową
  inspekcję wybuchowych osłon.
  `CanUseMove` Controller
  oraz stock `GameStateMoveUnitSingle`
  wciąż muszą zatwierdzić
  rzeczywiste wykonanie.
  Następna decyzja re-cachuje
  aktualny stan jednostki
  i `AA_Success` dla
  `Interact_PlantBomb`.
- Gdy A* jest niedostępne,
  niekompletne, zbyt długie
  albo native path nie przejdzie
  kontroli bezpieczeństwa,
  nadal wybierane są
  zachowawcze cele lub
  `StatusNoPlan`. Nie
  zastępujemy realnego
  problemu fałszywym
  natychmiastowym
  `RequestEndTurn`.
- Rozszerzenie logu
  `SabotageCC objective recovery`:
  `astar_solved`,
  `astar_verified`,
  `astar_length`,
  `astar_prefix_samples`,
  `sample_slots`, `native_samples`,
  `skipped_no_progress`, `skipped_visited`,
  `rejected_budget`, stan budżetów kontaktu i osłony na początku i końcu,
  `rejected_native_path`,
  `rejected_concealment`,
  `rejected_explosive`,
  `rejected_contact`,
  `native_detours_checked`,
  `clear_routes`. Dzięki
  temu kolejne zatrzymanie
  powinno mieć diagnozę
  konkretnej bramki.

## Pokrycie i Windows E2E

`tests/test_x4_astar_detour_v46.py`
wykonuje rzeczywiste czyste
funkcje UC (`ScoreSabotageAStarDetour`,
`HasVerifiedX4AStarGeometry`,
`SabotageAStarSampleIndex`,
`HasSabotageContactScanBudget`,
`ScoreSabotageRecovery`) i
kontroluje natywne kontrakty
od actor/socket przez A*,
realny blue path, komplet
hard-safety i Controller.
Utrzymano testy źródłowe
poprzedniej v44, w których
nowa liczba próbek
`Count=Min(48,Tiles.Length
+RouteSamples+1)` ma
wspólny limit.
E2E rzeczywistego native
planera **nie jest
możliwe offline** z samego
`Launch.log`, bo brak
stanu mapy/collision/cache
w danych raportu.

Po review/integracji LEAD:
(1) użytkownik kompiluje
w Windows WOTC SDK wskazany
końcowy commit i uruchamia
nową próbę `SabotageCC`;
(2) przy t19 porównuje
`astar_verified=true`
i ilość `clear_routes`,
wybrany stock blue
`objective_recovery_candidate`
oraz realny
`StandardMove` żołnierza;
(3) jeśli false, sprawdza
`astar_length`,
`rejected_native_path`,
`rejected_contact`,
`rejected_explosive` bez
ręcznego obchodzenia
wyniku; w takim przypadku
źródłowo bezpieczny stop
jest poprawny;
(4) tylko w razie natywnego
`Interact_PlantBomb`,
ukończenia obydwu celów
i `end=win` **bez
`phase=manual` lub
ręcznych akcji** można
zaliczyć autonomię;
(5) końcowy wynik
musi być potwierdzony
i dodatni, nie sam
`~7400` z partial
observed-v3.

Równoległa diagnoza
przejścia do Avengera
znajduje się w
`docs/experiment-107-postmission-transition-v46.pl.md`
na osobnym PR. Nie
przypisujemy natywnych
ostrzeżeń po wygranej
niezwiązanemu scorerowi
flanki bez crash dumpu.
