# #104 — wybór natywnego strzału, bezpiecznej flanki i Overwatch po ujawnieniu

Baza: zintegrowany `main 8716a3b478de16f19519086cd4dd6437e8553fac`
(`mission-report-v44`, PR #102), HELPER branch
`helper/104-ranged-shot-flank-overwatch-v45`, marker nowych diagnostyk
`mission-report-v45`. LEAD przejmuje niezależny przegląd i merge.
Natywny Windows WOTC make **v45 NOT RUN**; E2E w grze **NOT RUN**.
Zgodność syntetycznego CLI E2E nie oznacza legalnej flanki lub wygranej.

## Fakty z prywatnego raportu użytkownika

Analiza dostarczonego pliku
`AutoplayXCom2-20261115-014717-48d33941.zip`,
`Logs\\Launch.log`, aktualna sesja `2026-11-15_2-17-1-158_915`,
`ChallengeAbductionGasStation`, `mission-report-v43`.
Oryginalne logi i personalizowana ścieżka Windows nie są publikowane
w repozytorium. Sekwencja składa się ze zdarzeń APXREC, nie
z domniemanych ruchów/kandydatów.

| Decyzja (tura 1) | Wybrana akcja | Wykonany rezultat |
| --- | --- | --- |
| D1 | `StandardMove` medyka 63468 na (18,22,1), score80, ryzyko 77.5055→3.6907 | Native move accepted; `offensive_forecast=False` |
| D2 | Sniper 63480 `SniperStandardFire` do 63502, 82%, score55.08 | HIT, 10→5 HP |
| D3 | Żołnierz 63474 `StandardShot` do 63502, 71%, score88.0833 | MISS, 5→5 |
| D4 | Żołnierz 63486 `StandardShot` do 63502, 70%, score87.1667 | HIT, 5→0, eliminacja |
| D5 | Medyk 63468 `StandardShot` do 63501, 85%, score49.60 | HIT, 10→7 |

Po tych rozkazach Viper wykonał w turze 1 `PoisonSpit`.
Jedna akcja zatruła trzech żołnierzy; samo wystąpienie tej
konsekwencji **nie dowodzi**, że na decyzji D1 istniał natywny,
bezpieczny i lepiej punktowany strzał lub flanka. Native strzelby,
przepustowość dwóch AP, możliwość ruchu celu i obszarowy promień
trucizny wpływały na alternatywy, lecz ich kompletnej listy
w raporcie brak. Późniejsza strata żołnierza i nieprzytomność
Centrala nie pozwalają cofać skutku do arbitralnego pierwszego
decyzyjnego błędu. Dla D2–D5 akcje były rzeczywiście
dostępne i wynikają z natywnych rolowanych hit/miss.

W całej `GasStation` **12** rozkazów Overwatch aktywowało
**3** natywne `OverwatchShot` w turze 8:
63474→63506 **41% MISS**, 63486→63506 **61% HIT**,
63468→63504 **55% MISS**. Zatem 1/3 trafień
przy bardzo małej liczbie reakcji. Z uwagi na historyczny
trigger ruchu, stochastyczne trafienia i możliwe akcje
niezawierające ruchu, **nie** wyciągamy wniosku, że
każdy OW był błędny ani że OW miał 25% czy 100%
gwarantowanej szansy aktywacji. Stock native
`AddOverwatchAbility` rezerwuje AP, a
`OverwatchShot` jest odpalany przez silnik i
własne warunki triggera/LOS. Ręczna kontrola
celu native reakcji nie jest obecną cechą.

W `SabotageCC` w turze 26 natywna reakcja
416 zaatakowała jednostkę 422, która była
dawnym sojusznikiem pod obcą kontrolą. Kontekst
bieżącego statusu można analizować w momencie
**uzbrajania** Overwatch, ale nie można
zgadnąć, czy do przejęcia dojdzie dopiero
później ani zmienić przyszłego native
targetowania przez sam ranking. Nie
dodajemy fałszywego `reaction_target_id`
ani nie twierdzimy, że każde możliwe
przejęcie można wykryć z góry.

## Sprawdzona obecna taktyka i błąd

Istniejący `APX_CombatPlanner` bierze
wyłącznie `AA_Success` native
`AvailableActions`; `ScoreAttack` porównuje
szacowaną wartość obrażeń i eliminacji.
`ScoreOverwatchDefense` jest umiarkowany
(bez widocznego kontaktu score2,
przy kontakcie około17–22, zależnie od
concealment, HP i melee). Dla dobrego
natychmiastowego strzału (np. D2 55.08,
D3 88.08) Overwatch nie wypiera
legalnej akcji tylko ze względu na
oczekiwaną przyszłą reakcję.

`APX_RepositionPlanner` już przed #104
wymagał: ujawnionej jednostki, dwóch
rzeczywistych AP, current `StandardShot`
lub `PistolStandardShot` z legalnym
native target, `ActionPointsAfterBlueMove`
i natywnym `CanAttackWithActionPoints`,
braku zdolności zmieniających Aim po ruchu,
sprawdzalnego remote visibility/LOS/cover
oraz materialnego wzrostu chance ≥12 pkt
procentowych i attack score ≥8.
Nie przewiduje `SniperStandardFire`
ani zdolności posiadających powtórny
strzał z niezużytym AP; nie tworzy
natywnych targetów po ruchu.
Żaden zapis `offensive_forecast=True`
nie został wybrany w v43. Dotychczas
**brakowało statystyki WHY**: zero
kwalifikujących się strzałów, brak poprawy
celności, native path/cost, osłona,
ryzyko albo wyższa wartość innego
dostępnego działania.

**Konkretny błąd źródłowy** przed #104:
`ChooseMove` porównywał
`CandidateRisk<=CurrentRisk` tylko
na **końcowym** polu natywnej ścieżki;
pętla `PathIndex=1..` badała
hazard, FOW oraz wsparcie, ale
**nie** obliczała ekspozycji ani
wybuchowej osłony na **każdym** kaflu
pośrednim. Bezpieczny endpoint mógł
przykryć ryzyko na trasie.
To nie jest dowód konkretnej flanki
z sesji użytkownika, ale
rzeczywista luka bezpieczeństwa
dla wszystkich nowych projekcji.

## Zmiana v45

`APX_RepositionPlanner` ma dwie
małe niezależne funkcje polityki
i jeden wydzielony validator:

- `ForecastPathRiskAllowed`:
  czysta funkcja odrzucająca
  `StepRisk > OriginRisk`, niepełne
  lub ujemne wartości; testy
  sprawdzają również przypadek
  niebezpiecznego środka i
  bezpiecznego końca.
- `ForecastBluePathSafe`:
  wymaga pełnego, faktycznie
  zbudowanego native blue path,
  zgodności startu, max64 tile,
  znanego celu i native
  `IsSupportedCombatDestination`.
  Na **każdym** odcinku sprawdza
  `HasBlockingHazard`,
  `IsKnownCombatTile`,
  natywny FOW/Own squad visible
  (gdy FullIntel OFF),
  `IsSupportedAdvanceStep`,
  `ExposureRisk<=origin`.
  Na końcu weryfikuje **cały**
  odcinek przez istniejącą
  `APX_MissionPlanner.BlueRouteExplosiveSafe`,
  która korzysta z aktualnych
  `APX_ExplosiveCoverKnowledge.RiskAtTile`
  i *zużywa wspólny dla Controller
  budżet* `RemainingTempoCoverChecks`.
  Wystarczy brak jednego zapasu
  na kafel, aby odrzucić
  propozycję; nie ma resetu
  budżetu per soldier.
- `ForecastScanReason`:
  jednoznaczne, rozłączne
  powody w tej kolejności:
  `no_supported_current_shot`,
  `no_native_blue_endpoints`,
  `no_material_projected_shot`,
  `unsafe_or_unverified_blue_path`,
  `outscored_by_other_local_route`,
  `safe_move_and_shot_candidate`.
  Pierwszy powód oznacza
  **brak obsługiwanego wzorca**
  przez modele, a nie koniecznie
  brak amunicji w całej grze.

`ChooseMove` zwraca nadal
wyłącznie natywny blue path,
jego `Score` i flagę
czy zaproponowano plan;
dodatkowe `out` zwracają
`SupportedShots`,
`ImprovedShots`,
`SafeRoutes`, `ScanReason`.
`APX_Controller.MakeDecision`
zapisuje po jednym bounded markerze
`offensive_reposition_scan`
dla własnej ujawnionej
jednostki: `reason, score,
current_best, supported_native_shots,
material_previews, safe_native_paths,
cover_checks_left,
future_native_shot=unverified`.
Controller nadal porównuje
**wszystkie** propozycje jednostek
z obecnym `BestScore`,
zostawia wysoko ocenione natywne
strzały, medyka, ratunek,
interakcje i pilny timer,
a wykonaną trasę wysyła
wyłącznie przez stock
`GameStateMoveUnitSingle`.
Po zaakceptowanym ruchu
dopiero następna decyzja
pobiera nowy `UnitState`
i `AA_Success`; marker
nie sugeruje gwarantowanego
trafienia lub przyszłej
legalności.

### Obserwowany dawny sojusznik jako cel reakcji

Nowy mały `APX_CombatPlanner.GuardOverwatchForKnownAlly`
zwraca `−10000` jedynie dla **aktualnie
zweryfikowanego**, własnego przed
przejęciem i teraz wrogiego
`IsReclaimableControlledSquadmate`.
`HasVisibleReclaimableReactionTarget`
bada max64 bieżące
`GetAllVisibleEnemiesForPlayer`
i faktyczny stan z historii.
Brak danych albo nadmiar
kandydatów fail-closed,
nie jest pozwoleniem
na przypadkowy strzał
do byłego sojusznika.
`ScoreSelfAction` stosuje
taką ochronę **tylko**
przy rozważaniu
`OverwatchAbilities`,
nie zmienia legalnego
strzału bezpośredniego
ani native `OverwatchShot`
już uzbrojonego wcześniej.

Jeśli jednostka 422 została
przejęta **dopiero po**
uzbrojeniu reakcji 416,
dane dostępne w chwili
uzbrajania nie mogły
wskazać tego przypadku
i zmiana go nie eliminuje.
To ograniczenie pozostaje
do potwierdzenia w WOTC.
Prawdziwy wybór celu
reakcji należy do stock
silnika. Brak prognozy
przyszłego przejęcia
nie jest powodem, aby
czytać ukryte future
AI/cooldown/RNG.

Nie dodano nowego mnożnika
Overwatch, nie wybrano
liczby rezerwujących strzał
na podstawie sztucznego
`1 wspierający / 1 flankujący`;
kto strzela i kto ustawia
się w nadzorze wynika nadal
ze skorowania aktualnie
legalnych działań i zasobów.

## Pokrycie testami

**UC/pure unit tests**:
`ForecastPathRiskAllowed`
(bezpieczne origin/endpoint,
niebezpieczny środek, ujemne
dane), `ForecastScanReason`
(6 wariantów), istniejące
`MoveAndShotScore`,
`ProjectedHitChance`,
`ProjectedShotScore`,
`ScoreOverwatchDefense`,
`GuardOverwatchForKnownAlly`
(mocny strzał obecnie lepszy
niż OW, słaby strzał może
ustąpić legalnej flance,
zbyt mało AP, brak lepszego
hitu lub wzrost ryzyka,
native OW veto gdy obecnie
znany przeciwnik jest
odzyskiwalnym sojusznikiem).

**Source contracts**:
`ForecastBluePathSafe`
wywołuje wszystkie
native/map/hazard/cover
checks dla każdej pozycji,
z limitem i wspólnym
budżetem; `GatherForecasts`
rozróżnia realne
`AA_Success`,
`CanAttackWithActionPoints`,
realne hostiles i AP;
`ProjectAtTile` zachowuje
remote LOS i target condition;
`ChooseMove` wiąże pełną
ścieżkę z rankingiem;
`APX_CombatPlanner.ScoreSelfAction`
stosuje wąskie źródłowe
`HasVisibleReclaimableReactionTarget`
przed wystawieniem OW,
bez zakładania przyszłego
sterowania celami reakcji;
`Controller` rejestruje
odrzucenie i wciąż wymaga
`TraceCandidateMove` i
`CanUseMove`. Te
testy nie wykonują
native UnrealScript.

**CLI E2E offline**:
`tests/test_revealed_shooter_tactics_e2e_v45.py`
uruchamia rzeczywiste
`tools/analyze-mission-log.py`
przez `subprocess` na
odizolowanym ZIP z 3
syntetycznymi
APXREC sesjami:
mocny native shot/positive win,
blue move + odświeżone native
`AA_Success` + losowy MISS
+ LOSS oraz brak strzału/
niedopuszczona trasa + native
Overwatch z loss.
Weryfikowane są
sekwencja akceptacji
native action, marker
provenance, manual vs
autonomous, terminal
score known/unknown.
**To E2E publicznego
analizatora, nie native
E2E planera taktycznego.**

## Odbiór Windows WOTC / E2E wymagające gry

Po review/merge LEAD jednej
wspólnej paczki kodu:
1. Pobierz zaakceptowane
   źródła po SHA LEAD;
   uruchom to samo `UnrealEd.Make`
   Windows WOTC, zapisz
   `0 errors/0 warnings`
   albo log błędów.
2. Włącz autoplay i uruchom
   `ChallengeAbductionGasStation`
   bez ręcznych komend.
   Zapisz current revision,
   Native `AA_Success`,
   marker `offensive_reposition_scan`
   przy wrogach, oraz
   `candidate/chosen/result`.
3. Dla **dobrego strzału**
   sprawdź `current_best`
   kontra `no_material_projected_shot`
   lub niżej ocenioną legalną
   flankę. Dla **słabego**
   strzału potwierdź:
   native candidate
   `safe_native_paths>0`,
   `offensive_forecast=True`
   na rzeczywiście
   wybranym move,
   AP z 2→1,
   **świeży** legalny
   lub niedostępny native
   `StandardShot`
   dopiero po ruchu.
4. Osobno sprawdź
   niebezpieczne środkowe
   pole (eksplozja,
   krytyczny exposure)
   i budżet `cover_checks_left`;
   propozycja musi
   odpaść nawet gdy
   docelowe pole jest
   bezpieczne.
5. Zestaw natywne
   Overwatch triggers/miss
   z rzeczywistymi
   jednostkami i statusem
   `mind_controlled`
   **przed** uzbrojeniem,
   bez przypisywania
   niezaistniałego
   triggera. Sprawdź
   SabotageCC/416→422,
   tylko jeśli powtórka
   sytuacji wystąpi.
6. Zakończ misję.
   Zapewnij terminalne
   `native WIN`
   **oraz** znany final
   score `>0`; sama
   poprawa przeżycia lub
   liczba OW nie jest
   PASS całego projektu.
   Jeśli pojawią się
   ręczne interwencje,
   oznacz test
   `assisted`, nie
   `autonomous`.

Konkretny powód odrzucenia
w nowym raporcie
może wskazać następne
zadanie; nie deklarujemy
już teraz dostępności
bezpiecznej flanki z
archiwum v43.
