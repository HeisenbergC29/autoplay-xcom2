# #77 — SabotageCC: po wyczyszczeniu mapy dojście do prawdziwego punktu X4

## Zaobserwowany brak samodzielności v32

Prywatna próba `SabotageCC`, sesja `2026-11-13_21-44-23-212_890`,
`mission-report-v32`, kończy się native WIN t22 **po ręcznej interwencji gracza**.

W całych 114 rekordach `chosen` nie ma `Interact_PlantBomb`.
Po neutralizacji przeciwników (t19) autoplay przesunął jednostkę
421 na (40,36,5), a 427 na (42,35,6), jednak ich
`Interact_PlantBomb` w natywnym cache było `AA_NoTargets`.
Ostatnie decyzje to `overwatch` i potem
`Stopped: No constructive action or understood mission goal`
(gra kończy się dopiero po `phase=manual` w decyzjach 115/116).
Gracz ręcznie przestawił jednostkę421 na (42,34,6);
nowe `Interact_PlantBomb` miało `AA_Success`, jeden cel.
Ręczne wykonanie X4 dało `objective_completed` i native WIN.

Wniosek: **autoplay SabotageCC nie zaliczyło kryterium
autonomous victory**, a szacowane ok. +100 punktów
w profilu `wotc_legacy_observed_v2` jest wynikiem
całej misji wraz z ręcznym X4, nie wynikiem samego AI.
Oficjalny native final mission score jest nadal UNKNOWN.
Powiązana [korekta raportu #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4#issuecomment-6866136891).

## Przyczyna i minimalna zmiana

`APX_MissionPlanner.FindGoal` dotąd używa
`APX_PlantInteractionKnowledge.FindInteractionGoal` tylko dla
`BerserkerMP/SabotageTransmitter`. W `SabotageCC`
wykorzystywał ogólny mission marker,
ale `Goal.bFound = TileDistance(...,marker)>3`
zamyka marsz po dotarciu w promień3 **nawet gdy brak
faktycznego `AA_Success`** i gdy wymagane pole
interakcji znajduje się na innym poziomie Z.

Dodano bardzo ograniczoną gałąź w `FindGoal`:
- misja musi być dokładnie `SabotageCC`;
- zero znanych żywych wrogów, zero bezpośrednich zagrożeń;
- żadnego rannego wykrwawiającego się członka do ratowania;
- aktywna jednostka musi rzeczywiście mieć własne
  `Interact_PlantBomb`;
- wyłącznie wtedy istniejący bounded **read-only**
  `FindInteractionGoal` szuka rzeczywistego obiektu,
  jego niezużytego punktu i potwierdzonego natywnego
  socketu, wraz z prawdziwą trasą `X2PathSolver`;
- cel zostaje zastąpiony dopiero gdy native discovery
  zwróci status>0. Dzięki temu nie zatrzymujemy drogi
  na progu trzech pól wokół przybliżonego markera.
  Nowy log `Native monument plant approach` pozwala
  zobaczyć faktyczne miejsce i powód wyboru.

Jeśli native discovery nie znajduje pola (status=0)
lub obiekt jest zużyty (status<0), nie przyznajemy
żadnego fałszywego `AA_Success`; przywracamy
dotychczasową politykę. Samo podłożenie pozostaje
wyłącznie `APX_MissionPlanner.ChooseInteraction` +
stock `GameRulesCache_Unit` z prawdziwą dostępną
zdolnością i oryginalnym AP.

Zachowano Blood Killer/SabotageTransmitter, ewakuację,
obronę, leczenie, ryzyko, native blue-path, hazard i
wsparcie i wzór scoringu v28. Integracja LEAD otrzymuje
`mission-report-v33` w rejestratorze i diagnostyce, aby odróżnić
nową politykę od przetestowanej v32.
To mały niezależny bugfix, nie narzuca AI sztucznej akcji.
Brak osobnego zwiększenia premii do trasy: już istniejąca
`ChooseRoutePrefix` daje użytecznej misji score>Overwatch
gdy jest rzeczywista droga i AP>=2.

## Kryterium odbioru

`tests/test_sabotagecc_plant_anchor.py` wykonuje realny
helper polityki UnrealScript i sprawdza kontrakty native
find/AA/źródła. Zwykłe CI NIE jest Windows make ani
testem misji.

Po LEAD review i kompilacji w Windows WOTC SDK:
1. uruchomić SabotageCC/diff3 bez ręcznego działania;
2. po `Neutralize all enemy targets` sprawdzić
   `Native plant approach|...` i
   `Native monument plant approach|...`;
3. native `chosen|ability=Interact_PlantBomb|accepted=True`
   MUSI poprzedzać native `result`, a w całym odcinku
   ukończenia NIE może wystąpić `phase=manual`;
4. upewnić się, że native WIN, znane oficjalne
   końcowe punkty albo rozdzielona wartość porównawcza,
   oraz brak regresji GasStation i Blood Killer X4.

Ryzyko: faktyczna geometria i dostępność obiektu
zależą od konkretnej mapy; native query może zwrócić
0 mimo ręcznie dostępnej pozycji z powodu limitów
i `CanInteractNormally`. Wtedy poprawić błąd
odkrywania na podstawie nowego logu; nie tworzyć
fikcyjnego interaction target.

**Integracja**: branch HELPER na main v32
`a4b0b1cd4a69adef3fe1cf38a59873d79ec32522`;
oczekujące #69 i stacked #70 wymagają uwzględnienia
nowego main i nadania kolejnych rewizji po tym bugfixie.
Nie należą do paczki v33. Nie scala HELPER.
