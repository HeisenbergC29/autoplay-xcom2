# #130 — obowiązkowy Sweep przed ewakuacją zwykłego oddziału

Baza `411c8d4828be6315b750231967a959da884381ef`, gałąź
`helper/130-required-sweep-before-evac`. Jedna zmiana polityki ewakuacji,
bez przebudowy planera strzałów, punktacji, celu placement ani programu #120.

## Dowód z próby v50

Prywatny raport 27 XI, sesja NeutralizeFieldCommander
`2026-11-27_15-53-1-38_3889`, poziom difficulty=3. Kolejność obserwacji:

| Zdarzenie | Numer decyzji / historia / seq |
| --- | --- |
| KillCommander ukończony | t5, historia 2587, seq4402 |
| PlaceEvacZone zaakceptowane | D32, unit410, seq4624 |
| EVAC zaakceptowane | D34, unit428, seq4992 |
| EVAC zaakceptowane | D36, unit410, seq5293 |
| Sweep nieudane | t8, historia3354, seq6385 |
| Ekstrakcja ukończona | historia3357, seq6386 |
| Natywna porażka | historia3370, seq6394, history_pending=0 |

Druga sesja tej misji: dowódca ukończony t4/h2505, Sweep t8/h3340;
brak końcowego end. Nie uznajemy jej za wygraną ani porażkę. Surowe logi
pozostają prywatne. Pierwsza sekwencja dowodzi przedwczesnego wyboru Evac
przez AI, nie przesądza czy pozostanie na mapie wystarczyłoby do wygranej.

## Native provenance

Dostarczone źródła WOTC SDK `XGGameData.uc` definiują
`MissionObjectiveDefinition` z nazwą, flagami bIsTacticalObjective,
bIsStrategyObjective i bCompleted. Komentarz natywny przypisuje
tactical obowiązkowość przed automatycznym wyjściem oddziału i odzyskiem łupu.
`XComGameState_BattleData.AllStrategyObjectivesCompleted` pomija cele
wyłącznie taktyczne; pusty zbiór zwraca true. AllTacticalObjectivesCompleted
sprawdza ukończenie wszystkich taktycznych i wymaga istnienia przynajmniej
jednego. Nie stosujemy tego ostatniego wprost: trzeba rozróżnić ekstrakcję
i wykluczyć błędne koło. `CompleteObjective` ustawia natywne bCompleted
dla dokładnej nazwy. `SeqAct_CompleteMissionObjective` modyfikuje BattleData,
wywołuje CompleteObjective(ObjectiveName) i przesyła natywną zmianę;
`X2TacticalGameRuleset` używa ukończenia celów taktycznych w końcowej
obsłudze odzysku oddziału. Nie mamy pełnych grafów Kismet poziomów;
kolejność zdarzeń konkretnej misji wynika z raportu, nie z odtworzenia mapy.

Zainstalowany `Config/DefaultMissionDefs.ini`:
- NeutralizeFieldCommander: KillCommander strategiczny, Sweep taktyczny.
- CovertEscape: ExtractAll strategiczny (właściwa nazwa native definicji),
  EliminateAdventAgent opcjonalny.
- SabotageTransmitter: PlantBomb strategiczny, Sweep taktyczny.
- Ekstrakcja widoczna w UI NeutralizeFieldCommander nie oznacza osobnego
  wpisu ExtractAll w native MissionObjectives tej misji. Nie używamy tekstu UI.
Dodatkowe konfiguracje DLC/Legacy zawierają wymagane VIP-y. Zachowujemy
istniejący wyjątek kontrolowanego cywila oraz rzeczywistego nosiciela
jednostki oznaczonej ObjectiveInfo.

`X2Ability_AbortMission` ustawia bMissionAborted w natywnym stanie i
wyzwala zdarzenie MissionAborted. Po istniejącym native abort pozostaje
stara polityka strategiczna; mod nie inicjuje abortu i nie dodaje
przywileju ewakuacji nieznanego celu. Testujemy tę zgodność, nie
certyfikujemy przebiegu porzucania misji.

## Implementacja

- `ObjectiveEvacuationBlock`: bieżące bCompleted/flagowanie native.
  Ukończone i niewymagane cele nie blokują; nieukończony cel strategiczny
  lub taktyczny blokuje; wyjątek ExtractAll zapobiega czekaniu na zakończenie
  samego opuszczania mapy. Nierozpoznana nazwa celu wymaganego NIE jest
  automatycznie ukończona. Nazwy ekstrakcji innych modów bez potwierdzonego
  kontraktu nie są rozpoznawane jako wyjątek.
- `SquadEvacuationReason`: odczyt native definicji aktywnej misji, bez
  mutowania stanu. Brak danych, pusty zbiór oraz misja bez strategicznego
  lub potwierdzonego ekstrakcyjnego celu nie dają zwykłej zgody na Evac.
  Odczyt wskazuje pierwszy blokujący cel według kolejności definicji.
- `IsRescueEvacuation`: zachowanie dotychczasowej logiki kontrolowanego
  cywila XCOM albo nosiciela rzeczywistego celu; zgodność SourceStateObjectRef
  i ObjectiveInfo, nie każdy transportowany sojusznik.
- `ShouldEvacuate`: wspólny kontrakt ruchu FindGoal do strefy i wyboru
  ChooseInteraction. Nie blokuje ruchu bojowego tylko dlatego, że pole leży
  w strefie; blokuje **wybór marszu jako celu ekstrakcji** zwykłego oddziału.
  AA_Success/ownership/AP/route/hazards nadal obowiązują.
- Controller CanUseAction i MakeDecision ponownie sprawdzają tę politykę
  dla Evac przed native submit; nie blokują wyboru PlaceEvacZone.
- Recorder v51: raz na decyzję przy istniejącej strefie i stwierdzonym
  blokującym wymaganym celu taktycznym marker `evacuation_blocked`,
  scope=ordinary_squad reason=required_tactical_objective_pending.
  Dodatkowy marker przy odmowie revalidation na granicy wysłania.
  Scope oddziału nie wyklucza legalnego wyjątku VIP.

## Testy

`tests/test_required_sweep_evac_v51.py`: test-only adapter wykonuje
produkcyjne metody odczytu i warunków oraz rzeczywiste gałęzie Evac w
FindGoal/ChooseInteraction z podstawionymi API i obiektami. Pokrycie:
KillCommander → otwarty Sweep → ukończony Sweep; ExtractAll, optional,
unknown required, brak danych, pusty zbiór, obrona, cywil, właściwy/niewłaściwy
nosiciel celu, abort. Kontrakty źródła sprawdzają normalną selekcję,
native cache i ownership oraz kolejność ochrony przed dispatch.
Syntetyczny ZIP→CLI zachowuje marker, późniejsze Evac i odrębny historyczny
loss. To nie jest wykonanie gry ani dowód zwycięstwa. Dwa testy SDK sprawdzają
native flagi, Kismet completion i istniejący abort na prywatnych źródłach.

## Próba Windows po review LEAD

Jedna wspólna paczka wyznaczona przez LEAD, nie oddzielna publikacja PR.
NeutralizeFieldCommander: po KillCommander, przed Sweep, postawić strefę
jeśli native akcja legalna; zachować logi normalnych ruchów i wyborów,
sprawdzić marker oraz brak wyjścia zwykłego oddziału. Po rzeczywistym
native bCompleted Sweep oddział powinien móc legalnie skierować się do
strefy i wyjść. Dodatkowo misja ratunkowa: kontrolowany VIP / nosiciel
celu ma móc opuścić mapę, inni nie porzucają obowiązkowych celów.
Sprawdzić extraction-only, jeśli dostępne, oraz zachowanie po ręcznym
abort. Ocenić rzeczywiste AP i wynik, w tym odrębnie native win i
potwierdzone punkty misji >0.

Windows UnrealScript build i gameplay NOT RUN. Nie udowodniono, że AI
zawsze potrafi znaleźć i wykonać Sweep po tej poprawce.
