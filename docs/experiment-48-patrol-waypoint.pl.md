# Eksperyment #48 — bieżące punkty patroli wroga

Baza main \`defdcee43945a0755de6d069d7690cd215c83c63\` (v24).
Próba read-only oznaczona \`mission-report-v26\`. V25 jest osobnym
niezintegrowanym PR #47; LEAD musi połączyć markery i zaktualizować bazę
w odpowiedniej kolejności.

## Co można odczytać ze stock XCOM 2 WOTC

\`XComGameState_AIGroup\` w historii przechowuje:
\`EncounterID\`, \`m_arrMembers\`, \`CurrentTargetLocation\` i
\`TurnCountForLastDestination\`. \`IsEngaged()\` rozróżnia grupy
zaangażowane. Wybór następnego waypointu nie jest deterministyczną
gotową trasą — w normalnym patrolu nowy punkt wybiera się losowo z
aktualnych narożników obszaru encounter. Cel może też zmienić się,
gdy XCOM przekroczy bandę grupy, grupa zacznie przechwytywać XCOM,
wejdzie w walkę lub natywna misja wymusi intercept objective.

Nowa \`APX_PatrolKnowledge.GetCurrentPatrolWaypoint\` zwraca **jedynie**
istniejący obecny cel grupy, jeżeli grupa nie walczy,
nie wykonuje scamper, nie jest w roli stałego objective guard i nie
interceptuje celu misji; wymaga rzeczywistej grupy z członkami
i punktu w granicach mapy. **Nie wywołuje** procedury do wyboru
przyszłej trasy, nie czyta kolejnego losowania i nie wydaje rozkazów
wrogowi.

\`APX_MissionRecorder.RecordCurrentPatrolWaypoints\` raz na turę
lokalnego gracza skanuje maksymalnie 32 grupy, emituje
\`patrol_group\` z rzeczywistym \`group\`, \`encounter\`,
\`members\`, \`target_x/y/z\`, bieżącym midpoint i turą,
w której wrogie AI ustawiło cel. \`patrol_scan\` zawiera
\`groups_checked\`, \`current_waypoints\` i
\`future_route=unknown\`.

## Jak tę informację wykorzystać w następnej polityce

Z punktu patroli i ich statusu da się oszacować punkt kontaktu,
gdzie żołnierze z natywnie legalnym overwatch mają LOS, osłonę
i wystarczający dystans od innych grup. Nie należy jednak obiecywać
konkretnego wejścia patrolu w pole widzenia ani bezpłatnych
\`OverwatchShot\` podczas activation scamper. Patrol może zmienić
cel przed dotarciem do niego. Granatnik i melee-only BerserkerMP
nie są automatycznie strzelcami obsługującymi overwatch.

Pełna polityka ma działać **tylko na misjach bez pilnego czasu
i malejącego natywnego wyniku**, z ograniczoną liczbą prób
staging, opcją rezygnacji po zmianie waypointu i bez prowokowania
drugiej grupy. Wymaga osobnego planera sekwencji, a nie
zastępowania istniejącej walki stałym czekaniem. To nie jest
jeszcze wdrożone w niniejszym PR.

## A/B i kryterium odbioru

Kompilacja Windows WOTC SDK oraz test w grze wymagane.
GasStation: rejestrować dwie kolejne tury patrolu i porównać,
czy \`patrol_group.target\` naprawdę odpowiada ruchowi grupy
oraz jak często zmienia się pozycja docelowa/stan engaged.
Nie zakładać, że sam odczyt patrolu już poprawił taktykę.
Blood Killer: pilny objective oraz brak ranged overwatch,
ta polityka nie powinna go opóźniać.

Przy każdej misji zapisujemy obowiązkowe cele, natywny
outcome i **punkty** z oznaczeniem finalne/częściowe/brak.
Nie ma PASS bez wszystkich celów, \`win\` i potwierdzonego
końcowego wyniku > 0. Jeżeli wystąpi \`objective_failed\`,
zgodnie z decyzją użytkownika jest to krytyczne FAIL.

**Ostatni ZIP v24 z 11 XI 2026 odczytano po odzyskaniu narzędzia:**
SabotageCC native win, ostatni HUD ~+6800 (częściowy, brak final
mission_points), jedno ambush_setup i jedno ambush_opening;
GasStation native loss, **−10700 końcowe natywne**, zero
ambush_setup/ambush_opening; Blood Killer ręcznie przerwana
po D34 i `Mission timer expired` po wyłączeniu autoplaya,
0 objective, końcowe punkty nieznane (tylko początkowe 0).
W starym recorderze v24 nie było wpisów patrol_group,
więc nowy odczyt jest niezweryfikowany w grze.
Nie przenosić do GitHuba surowych logów, SDK ani zapisów.
