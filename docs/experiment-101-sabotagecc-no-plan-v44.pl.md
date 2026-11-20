# #101 — SabotageCC v43 zatrzymuje autoplay mimo natywnych 2 AP

**Status:** nowa regresja z rzeczywistej próby użytkownika WOTC. Baza
`main c881a5265ab29adf9e17a4df52134ddab69ee18a` (zintegrowany
v43 + poprawki kompilacji #100). Gałąź HELPER
`helper/sabotagecc-no-plan-objective-recovery-v44`;
docelowy marker `mission-report-v44`.
Żaden źródłowy test CI nie jest natywną kompilacją Win64 ani potwierdzonym
zwycięstwem w grze. Bez samodzielnego scalenia przez HELPER.

## 1. Dane gry i fakty (nie przypuszczenia)

Dostarczone `mod-make(3).log`: `UnrealEd.MakeCommandlet`,
`Scripts successfully compiled`, `0 error(s), 0 warning(s)`,
czas 6.73 s. To dowód poprawnej kompilacji **v43 użytkownika**,
nie nowego v44.

Archiwum użytkownika `AutoplayXCom2-20261115-014717-48d33941.zip`
(oryginalne 4 logi z manifestem SHA-256; brak save).
Najświeższe `Logs/Launch.log`:
sesja `2026-11-15_2-5-23-751_888`,
`mission=SabotageCC`, `mission-report-v43`,
`full_intel_enabled=True`.

| Krok | Weryfikowalna obserwacja |
|---|---|
| Tura 21, decyzja 93 | Native `StandardMove` żołnierza 416 z (11,32,1) na (16,32,1); `route_tempo goal=(40,34,2)`. |
| Tura 21, decyzja 94 | Native `StandardMove` żołnierza 422 z (19,32,1) na (23,32,1); ten sam cel. |
| Decyzje 95, 96 | Natywne Overwatch za 2.0; następnie nowa tura. |
| Tura 22, decyzje **97–104** | **Osiem** `autoplay_stop`: `No constructive action or understood mission goal`. Tylko `overwatch score=2`; brak kandydatów ruchu. Przy starcie obaj żołnierze mają **2 AP**, nie zabrakło amunicji ani AP na legalny native move. |
| Ostatni cache przed problemem (decyzja 96) | `Interact_PlantBomb AA_NoTargets` dla obu. Natywny przycisk plant nie był gotowy — nie było obowiązkowej ręcznej akcji specjalnej, którą automat świadomie odrzucił. |
| Ręczne obejście | `StandardMove` przeniosło 416 na (25,37,1), a 422 na (30,35,1), po czym autoplay znowu wybierał legalne trasy (decyzje 105/106). Ręczny ruch jest dowodem istnienia dalszego ruchu w grze, **nie dowodem**, że konkretny wcześniej odrzucony tile/ścieżka był bezpieczny albo native-achievable. |
| Koniec sesji | Tura 26: `objective_failed Plant X4 charges on the monument` oraz `Neutralize all enemy targets`, `event=end outcome=loss`. Nie jest to sukces pomimo manualnego obejścia. |

Równoległe logi zawierają inne misje i stare rewizje, których
nie mieszamy z tą sesją; w archiwum są także starsze przypadki
`StatusNoPlan` w SabotageCC. Nie publikujemy surowych prywatnych
logów, save ani źródeł stock SDK w repo.

## 2. Hipoteza, której jeszcze nie udowodniono

`APX_Controller.MakeDecision` zatrzymuje autoplay przy
`BestScore<=2`, `MeaningfulActionsThisTurn==0`, bez rzeczywistego
widocznego kontaktu. To **dokładnie potwierdzony** mechanizm stopu
z opisanych rekordów. Nie ma natomiast w v43
per-kaflowego `why_rejected` dla `ChooseMove`:
nie umiemy z tych logów jednoznacznie przypisać winy
A*, dynamicznej osłonie, support-limit, scoringowi
ani budżetowi kontaktów.

Prawdopodobna kombinacja: `FindGoal` wraca do
`MapData.ObjectiveLocation` na **Z2**, które jest
markerem misji, nie udowodnionym natywnym polem
interakcji. `ChooseRoutePrefix` próbuje A*
**dokładnie do celu**, a lokalny `PositionScore`
pomniejsza pożyteczny postęp przez miękką
`SquadPositionScore`; sztywne zasady support
dodatkowo ograniczają kandydatów. Gdy prawdziwy
native waypoint wymaga obejścia albo cofnięcia
do przodu, standardowa funkcja może nie
zaproponować żadnej akcji. Logi nie wskazują
konkretnego kafla odrzuconego z takiego powodu,
więc to **hipoteza** — nie zgłaszamy jej jako faktu.

### Reprodukowalny konflikt progów na prostym odcinku (nie dowód geometrii mapy)

W `XComAutoplayXCom2.ini` są faktyczne wartości
`SquadSupportDistance=8`, `SquadSeparationTiles=2.5`,
`MinimumPositionGain=4`, `SquadAreaRiskRadiusTiles=3`
i `SquadAreaRiskWeight=6`. Dla FRONT jednostki 422 na
(23,32,1), partnera 416 na (16,32,1) oraz markera
(40,34,2), po idealnym poziomym kroku do (25,32,1):

- poprawa `-TileDistance*3`: około `+5.95`;
- miękka kara rozdzielenia z 7 do 9 pól względem
  `SquadSupportDistance=8`: `-4`;
- łączna poprawa **około +1.95**, poniżej
  twardego progu `MinimumPositionGain=4`.
- dalszy bezpośredni krok do X=26 zwiększa rozstaw
  do10; kara=8, poprawa odległości≈8.9, zysk≈0.9.
  Krok do X=27 daje rozstaw11, który jest już
  odrzucany przez zwykłe
  `IsSupportedAdvanceDestination(StartDistance=7,...)`.
  Zatem soft formacja + próg + hard support mogą
  utworzyć **matematyczną pułapkę punktacji**.
  Nie oznacza to, że właśnie te X25–X27 to realne
  native walkable tiles (nie mamy save ani
  dokładnej mapy).

Logi poprzednich decyzji93/94 pokazują
`Contact envelope status=0 reason=clear_current_snapshot_only`,
`tiles_left=121/123`; skan kontaktu nie był
wtedy globalnie wyczerpany. Trasa nadal może
być zablokowana przez inną ścieżkę/ocenę,
więc jest to **silnie wsparta hipoteza progowa**,
nie udawana znajomość dokładnej gałęzi
`continue` w decyzji97.

## 3. Wdrożony ograniczony wariant naprawczy

`APX_MissionPlanner.ChooseSabotageCCRecoveryMove`
jest aktywowany przez Controller **wyłącznie**, kiedy
zwykły skan ruchu i akcji nie dał konstruktywnego
wyniku (`BestScore<=2`), misja to dokładnie
`SabotageCC`, własna jednostka posiada natywne
`Interact_PlantBomb`, ma ≥2 standardowe AP,
natywne `StandardMove AA_Success`, nie ma
aktualnego widocznego kontaktu ani pilnego bleeding/evac.

Najpierw **czyta** rzeczywisty native
`APX_PlantInteractionKnowledge.FindInteractionGoal`
z weryfikacją actor/socket/query/pełnej
ścieżki. Gdy punkt istnieje, zastępuje
niezweryfikowany wysoki marker; gdy natywny
aktor już skonsumowano — nie ściga starego
celu. Jeśli `FindGoal` odrzucił stary marker
na dystansie ≤3 (mimo `AA_NoTargets`),
**weryfikowany socket nadal jest badany**:
to dodatkowy test regresyjny `2.5→1.2`
pola. Bez natywnego aktora bliski marker
bez rzeczywistego celu zostaje
**niezweryfikowany**, nie generujemy
przypadkowego chodu na już osiągnięty
znacznik. Jeśli native actor nadal jest
nieznany, ale marker jest daleki,
dopuszcza dotychczasowy cel misji jako
**wyłącznie cel ruchu**, nigdy potwierdzoną
akcję `PlantBomb`.

Po ocenie zwykłych akcji całego oddziału kontroler sprawdza kwalifikujących się żołnierzy. Dla każdego z nich planer skanuje maks. 48 rzeczywistych
natywnych endpointów z istniejącego blue-range
`m_kReachableTilesCache`, włącznie z
`GetClosestReachableDestination`.
Każdy wymaga `IsTileReachable`,
`GetPathCostToTile<=GetMobility`,
`BuildPathToTile`, prawidłowego dokładnego
początku/końca i max48 tile, **redukcji aktualnej
odległości do celu o co najmniej 1.0**.

Niezależnie sprawdza **każdy tile**
pod kątem znanych przeszkód i środowiskowego
`HasBlockingHazard`, `ExposureRisk<=start+3`,
`APX_ConcealmentPlanner.InspectPathRisk`,
`BlueRouteExplosiveSafe` i natywnego current
`APX_ContactEnvelope.AssessRoute`.
`Unknown (-1)` lub `Caution (1)` na
którymkolwiek odcinku => kandydat odpada.
Finalna `InspectRiskAtTile` korzysta z
dzielonego budżetu; nie ma resetu limitów
na osobę/ruch. Przyszłe AI/patrol,
nieobsługiwany footprint i bezwarunkowa
legitymizacja „pełnego” horyzontu nie są
udawane.

**Jedyny poluzowany warunek: miękka
formacja przy jasno potwierdzonej obecnej
drodze, bez bieżącego kontaktu.** Native
dystans wsparcia w takim wyjątkowym
ruchu może przejściowo wzrosnąć
do wartości `min(14, max(10, początkowy_dystans + 4))`. Przy początkowym dystansie 5 pól dopuszcza więc 10, a przy 9 dopuszcza 13.
`SquadPositionScore` pozostaje karą,
a nie globalnym zakazem. Niczego
nie zmienia w walkach, leczeniu, AoE,
patrol staging, ewakuacji, liczbie
punktów czy trybach innych misji.

Zmiany po stronie Controller wciąż
poddają kandydat dokładnie tym samym
`TraceCandidateMove` i `CanUseMove`,
a potem normalnemu native
`GameStateMoveUnitSingle`. Kolejny
cykl przelicza rzeczywisty UnitState
i AP. Nie ma sztucznego end-turn,
force-plant, fabrykowania native
targetu ani oszukiwania kosztu
odległości 2×Mobility.

**Diagnostyka:**
`APXREC marker kind=objective_recovery_scan`
z `found, reason, native_blue_only,
horizon_ai_turns=0`;
`objective_recovery_candidate` z
pozycją i score przy prawdziwym
wyborze; dodatkowy log
`SabotageCC objective recovery`
z `goal_xyz, native_plant_status,
native_plant_reason, native_samples,
clear_routes, rejected_routes`.
Jeżeli brak zweryfikowanej trasy,
oryginalny watchdog **nadal** zatrzymuje
automat, ale z konkretnym
`SabotageCC: no currently verified
native X4 route; see objective_recovery_scan`.
Nie podejmujemy niebezpiecznego
automatycznego `RequestEndTurn`
zamiast rozwiązania problemu.

## 4. Weryfikacja i warunek odbioru

`tests/test_sabotagecc_no_plan_recovery_v44.py`
wykonuje rzeczywiste czyste UC:
`CanAttemptSabotageRecovery`,
`IsRecoveryFormationAllowed`,
`ScoreSabotageRecovery`.
Punktowy fixture 416/422/(40,34,2)
sprawdza tylko kalkulację i warunki
bezpieczeństwa; **nie jest odtworzeniem
mapy ani dowodem dostępności x25**.
Testy kontraktów wymagają realnego
native cache, pełnej drogi, budżetów,
braku innych misji/wywołań X4 i
poprawnego ownera Controller.
Kompilacja Windows i ponowna rozgrywka
nie były wykonywane na v44.

W przeglądzie LEAD wydzielił sprawdzenie całego oddziału po zwykłych akcjach, eksploracji i przygotowaniu zasadzki. Wcześniej kandydat awaryjny o wartości 38 mógł wyprzedzić zwykłą akcję za 33 tylko dlatego, że jego żołnierz był sprawdzany pierwszy. Nowy warunek wymaga, żeby najlepsza zwykła akcja całej drużyny miała co najwyżej 2. Wśród legalnych sprawdzonych rozwiązań awaryjnych wybierane jest najlepsze.

Przy nieznanej geometrii X4 planer odczytuje publiczny znacznik misji. Pozwala to odróżnić cel X4 od dowolnego innego interaktywnego obiektu lub cywila. Brakujące dane, zużyty obiekt i odrzucona trasa zachowują zarejestrowany powód. Test CLI analizatora obejmuje przyjęty rozkaz oraz ręczną interakcję w dwóch syntetycznych sesjach. Dla samego planera przygotowano próbę w silniku. [Scenariusz E2E](e2e-sabotagecc-v44.pl.md)

Następną wspólną kompilację LEAD przekaże po odbiorze [pracy HELPERA #104](https://github.com/HeisenbergC29/autoplay-xcom2/issues/104).
