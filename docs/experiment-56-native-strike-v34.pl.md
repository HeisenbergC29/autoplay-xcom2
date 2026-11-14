# #56 — etap P1a: natywnie gotowy cios przed X4, bez gonienia dalekiej grupy (v34)

## Obserwacja z testu v29

Blood Killer / `SabotageTransmitter` / diff2, sesja
`2026-11-13_11-57-35-409_2`, natywna porażka w turze 14,
**oficjalny końcowy wynik +7100**. X4 i przekaźniki ukończono w
turze 8; trzy fizyczne zgony spowodowały scenariuszową przegraną.
55 chosen/109 result były identyczne z backupem v28,
w tym 21 ruchów bez ataku w turach1–3.
61 markerów fokusu: 51 objective, 10 sweep, **0 contact**.
Pierwszy wybrany cel miał dystans22.98 przy timer4; na późniejszych
decyzjach dystans schodził do18.42 (nadal >18), a potem timer spadał
do3. Nie wynika stąd, czy w tych chwilach istniał już **legalny cios
na wskazany target** — trzeba to zmierzyć w kolejnej próbie.

## Niewielkie rozszerzenie taktyki — jeden bezpośredni native strike

Nadal obowiązująca polityka `ShouldUseContactGoal` przy
`distance<=18`, `timer>=4`, tura1–2, >=3 własnych
BerserkerMP nie zmienia się: spekulacyjny marsz do grupy powyżej18
**nie jest dozwolony**. Zamiast tego nowy tylko-do-odczytu
`APX_BerserkerFocus.FindNativeOpeningStrike` szuka w stock
`GameRulesCache_Unit` **aktualnie gotowego**
`DevastatingPunchMP` tylko na wybranym istniejącym
żywym/aktywnym przeciwniku. Wymagane:
- jednostka rzeczywiście należy teraz do lokalnego XCOM,
  jest aktywna i żywa, `BerserkerMP`, ma >=55% HP;
- natywna akcja `AA_Success`, `bInputTriggered`,
  `bFreeAim=false`, rzeczywisty własny `AbilityObjectRef`,
  `AvailableTarget.PrimaryTarget` równy wskazanemu wrogowi;
- cel znajduje się na **aktualnej** liście
  `GetAllVisibleEnemiesForPlayer`, `IsVisibleHostile`,
  `AdditionalTargetsAreSafe`, `HasRequiredMeleePath`,
  `ScoreAttack - MeleePenalty >5`;
- maksymalnie128 skanowanych stanów jednostek (łącznie
  z odrzuconymi), 96 natywnych ofert na aktywną jednostkę,
  24 cele na ofertę i 64 kontakty gracza.
  Przekroczenie limitu zamyka wyjątek, nie uruchamia domyślnego ataku.

Jeżeli zwykłe otwarcie nie weszło i **natywnie gotowy atak**
jest prawdziwy, `CanPreferNativeOpeningStrike` dopuszcza
tylko jego miękkie preferowanie dla **jednej wskazanej
jednostki** w turach1–2, przy prawdziwym timerze>=4,
>=3 żywych i braku wykonanego PlantBomb. Nieznany
status PlantBomb nie wystarcza.
Po faktycznym przyjęciu takiego ciosu odnotowywany jest
limit **jednej bonusowanej próby na turę**.

Ważne: wyjątek NIE ustawia `bFocusedGoal` ani nie
przekazuje wybranego celu do `MissionPlanner.ChooseMove`;
inne własne jednostki zachowują swoje niezależne zadania.
NIE obniża `ContactRelayScore`, co byłoby ryzykowne
dla timera i X4. Zmienia jedynie premię tego konkretnego
natywnie gotowego działania w `APX_CombatPlanner`;
normalny score może nadal wybrać relay, ratunek lub PlantBomb.
Wszystkie istniejące rygory AA/AP, HP, native melee path,
hazards, support i końca tury pozostają.

Dodatkowa obserwacja `berserker_focus`:
`native_strike_ready=true/false`, `native_strikes_this_turn`.
Pozwala rozróżnić brak legalnej okazji od porażki selektora.
Dane są zbierane w ramach istniejącego pojedynczego
wywołania rejestratora na decyzję, bez dodatkowego ticka
punktacji HUD.

## Weryfikacja i ograniczenia

`tests/test_native_berserker_opening.py` wykonuje rzeczywisty
helper UC do limitowania otwarcia, bada granice timera,
brak przejęcia w fazie Sweep, jeden cios na turę,
gotowość natywnej akcji, oryginalne osłony i brak
nowej spekulacyjnej marszruty. Istniejące testy
`test_berserker_focus.py` zachowują rozróżnienie
bFocusedGoal od native-strike-only.

Zielone CI nie oznacza natywnej kompilacji Windows WOTC
ani faktycznie dokonanego ataku w grze. Kod nowej wersji
ma marker `mission-report-v34`. Nie zmienia w żaden
sposób `APX_MissionScore`, bezpiecznej arytmetyki
punktacji v28, struktury zwycięstwa, UI v32,
`APX_RevealedFocus` i ochrony początkowej własności
BerserkerMP z v32. Nie jest to pełne rozwiązanie
21 ruchów bez ataku: gdy żadna akcja nie jest
natywnie dostępna, zachowanie pozostaje jak v32,
bez ryzykownego zgadywania wyniku przyszłego ataku.

Po scaleniu LEAD i wykonaniu **oddzielnego builda**
porównać Blood Killer/diff2: marker
`native_strike_ready`, pierwszą legalną okazję,
czy cios został faktycznie wybrany, zrealizowane
przekaźniki i X4 do terminu, trzeci zgon i
scenariuszowy heavy-loss oraz **natywne zwycięstwo
i oficjalne końcowe punkty>0**.

Dalsze zadania #56 (wykonalne bezpieczne podejście,
spójność Sweep, realna ochrona przed kontrolą)
wymagają osobnych zmian i testów, najlepiej po
raporcie z v32/v34. Nie wolno deklarować sukcesu
misji tylko z wyniku +7100 po natywnej porażce.

Powiązane: [#56](https://github.com/HeisenbergC29/autoplay-xcom2/issues/56)
oraz [raport v29](report-2026-11-13-v29.pl.md).
