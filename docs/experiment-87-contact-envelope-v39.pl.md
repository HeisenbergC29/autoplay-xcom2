# #87 / v39 — wspólny snapshot kontaktu i uczciwy horyzont patrolu

Baza: `main c833dcc4189a84b90b169803a2531889e9c48fb4`,
runtime `mission-report-v38`. HELPER gałąź
`helper/87-contact-envelope-v39`, implementacja/marker `mission-report-v39`.
Zadanie źródłowe w skończonej kolejce [#86](PREBUILD-QUEUE.pl.md).
**Windows WOTC make/game v39: NOT RUN — #4 pozostaje BLOCKED.**
Nie zlecać testu po tym PR; jedna wspólna paczka dopiero po ukończeniu całej
kolejki i LEAD review/integracji.

## Ustalenia i dowód stock

`XComGameState_AIGroup.CurrentTargetLocation` i
`TurnCountForLastDestination` to rzeczywiście zapisany aktualny cel,
nie przyszła sekwencja ruchów. Zegar wybranego celu pochodzi z
`XComGameState_AIPlayerData.StatsData.TurnCount` (patrz
`XComGameState_AIGroup.uc:370–416`), **nie z tur własnej drużyny**.
`PatrolGroupList` i grupa z realnymi żywymi członkami są źródłami
przynależności; brak grupy/zegara, stare albo osiągnięte waypointy nie
potwierdzają bezpiecznego korytarza. Typowy patrol nie przechowuje
trwałej wybranej wieloturowej trasy. Nie wykonujemy `ComputeGroupPath`,
`ShouldMoveToIntercept`, `GetGroupMovePaths`, `GetGroupInfo`
ani przyszłego RNG/ukrytych bieżących AP/ammo/intent.

Dla ukrytego żołnierza `XComGameState_Unit` różnicuje
ruch detektora względem stojącego celu (osłona z kierunku wykrycia)
i przejście własnego ukrytego żołnierza (bez tej samej osłony).
`APX_ContactEnvelope.ConcealedContactPossible` odwzorowuje
oba logiczne warianty; rzeczywiste path traversal ocenia ten bardziej
ryzykowny: **porusza się własny żołnierz**, osłona na końcu trasy
nie legalizuje jej niebezpiecznego środka. GetConcealmentDetectionDistance
i UnitBreaksConcealment są natywnymi odczytami; ignorowanie zasięgu
to rzeczywista osobna gałąź. Po ujawnieniu sama odległość nie wystarcza —
sprawdzany jest także native geometry LOS; brak geometrycznej widoczności
w pobliżu wroga pozostaje Unknown, bo podgląd zza osłon/peeks może
odmienić rzeczywisty wynik.

## Wdrożone #87

1. `APX_Controller.MakeDecision` buduje **jeden** read-only snapshot
   na pierwszym aktualnie działającym własnym żołnierzu. Wszystkie
   późniejsze `APX_MissionPlanner.ChooseMove` w tej samej decyzji
   otrzymują te same referencje detektorów i interaktywnych obiektów
   oraz wspólny zmniejszający się budżet. Ustawienia:
   32 grupy / 128 member refs / 64 detektory / 128 pól trasy /
   512 zapytań native LOS. Zmiana mapy/battle/history przy następnej
   decyzji powoduje nowy snapshot; nie ma cache między decyzjami.
2. `APX_PatrolKnowledge.StoredPatrolEvidence` przegląda wyłącznie
   `AIPlayerData.PatrolGroupList` (limit 8 rekordów danych AI),
   weryfikuje hostile player team, świeżość waypointu na AI clock
   (aktualna, 1 albo 2 tury stara), rzeczywistą grupę/żywych członków,
   punkt w świecie i osiągnięcie waypointu. Stare/niepewne dane
   oznaczają snapshot incomplete, nigdy `Clear`. Brak wpisu na
   patrolowej liście nie oznacza wybranego waypointu.
3. Nowy `APX_ContactEnvelope.AssessRoute` ocenia **całą**
   natywnie zaproponowaną trasę, w tym środek, przeciwko aktualnym
   znanym jednostkom, widocznym cywilom i interaktywnym detektorom.
   Sprawdza rzeczywiste active/alive/team, natywne
   `UnitBreaksConcealment`, `GetConcealmentDetectionDistance`,
   LOS na tiles, podróż przez okno/ścianę/drzwi i wspólne budżety.
   Po przeglądzie dodano istotne ochrony: natywna ścieżka musi
   zaczynać się w `Soldier.TileLocation`, lecz ruch detekcyjny
   ocenia się od kroku 1 — własnego pola startowego nie traktujemy
   jako nowo przebytego. Efekt ignorujący *concealment detection
   distance* nadal podlega maksymalnemu **sight radius**;
   dystans po raycast LOS pochodzi z `Visibility.DefaultTargetDist`,
   a nie z dowolnej odległości środków kafelków. Bliski niepewny
   brzeg LOS daje Unknown. Usunięto zbędne obliczanie kierunkowej
   osłony własnego żołnierza podczas ruchu — native wyjątek
   direction-cover dotyczy stojącego żołnierza przy ruchu detektora.
   Zwraca `1 Caution` dla realnej aktualnej okazji wykrycia,
   `0 Clear` **tylko dla obecnej znanej geometrii**
   (`horizon_ai_turns=0`), `-1 Unknown` przy jakiejkolwiek
   luce, obcięciu próbkowania, FOW, możliwych peeks albo
   `horizon_ai_turns>0`. Nigdy nie przyjmuje przyszłego patrolu
   za nieruchomy w celu certyfikacji dalekiej trasy.
4. **Rzeczywisty konsument** `APX_MissionPlanner.ChooseMove`:
   normalny, niepilny route prefix oraz legalne lokalne ścieżki
   porównywane są z oceną kontaktu. `Caution` jest silniej
   penalizowany (24 utility), `Unknown` łagodniej (8 utility).
   Potwierdzony niebezpieczny prefix może zostać zastąpiony
   bezpieczniejszą legalną lokalną alternatywą, zachowując
   `RiskyRoute` jako ostatni fallback, gdy nic innego nie działa.
   Detektory nie dostają natywnego targetowania/strzału z ukrycia.
   Pilny timer/ratunek/X4, combat reposition i ewakuacja korzystają
   z dawnych reguł. Nie zmieniono native AP/AA/route/LOS/dispatch,
   pełnej trasy hazard/support, ochrony sojuszników, OFF,
   punktacji ani benchmarku.

## Granice i następne etapy

Przegląd LEAD zachowuje obliczone ryzyko wybuchowej osłony także wtedy,
gdy ten sam prefix ma ContactStatus=CAUTION. Niezależne koszty nie znikają
w legalnym fallbacku. Dodatkowo jednostki wielopolowe (własne lub detektory)
dają Unknown: pojedynczy anchor ray nie odtwarza całego natywnego footprint.
Weryfikacja wszystkich zajmowanych pól pozostaje warunkiem przyszłej
certyfikacji #88/#89, a nie domyślnym Clear.

`Clear` jest **wyłącznie current-state bound dla kontrolowanego
ruchu w bieżącej decyzji**; nie jest prognozą ruchu patrolu w następnej
turze, pewnością odległych scripted spawnów ani certyfikatem braku
cywilów/obiektów poza native visibility. Przy `EnableFullIntel=false`
nowy snapshot bezwzględnie pozostaje incomplete — nie odczytuje
ukrytych wrogów i nie twierdzi `Clear`. Obecny klasyczny
`APX_ConcealmentPlanner` i jego kontrola native traversal nadal
działają niezależnie; nowa ocena dodaje koszt dla rutynowego ruchu,
nie usuwa ochrony i nie zastępuje klasyfikacji live visibility.
Długiego dash nie włącza #87: wymaga osobnego udowodnienia kosztu
AP w [#89](https://github.com/HeisenbergC29/autoplay-xcom2/issues/89).
Wieloturowa zasadzka, optymalne OW i prawdopodobne korytarze
są osobnym [#88](https://github.com/HeisenbergC29/autoplay-xcom2/issues/88).
Ryzyko wyników `Unknown` przy licznej scenie lub stale patrolu
jest zamierzone; zachowany legalny fallback może być wolniejszy.
To obserwacyjny model źródłowy, nie dowód z silnika.

## Walidacja i późniejsza wspólna próba

`tests/test_contact_envelope_v39.py` uruchamia rzeczywiste
czyste helpery UnrealScript przez `uc_math` (AI clock,
concealment movement/stationary, pusty budżet), sprawdza jeden snapshot
i przekazanie budżetów Controller→MissionPlanner, native LOS/
detection, stale/unknown, FullIntel=false oraz realny wpływ
na `ChooseMove`. `APX_SDK_SOURCE_ROOT` uruchamia dodatkowe
kontrakty stock w prywatnym SDK. Brak Windows make/gry pozostaje jawny.

Przy zbiorczym teście po #86 trzeba zapisać:
- `contact_snapshot`, status i powód oraz pozostały globalny budżet;
  current Clear/Caution/Unknown z pełną trasą, a nie wyłącznie końcem;
- station/traversal przy realnym native contact i osłonie kierunkowej,
  civilian/interactive, FullIntel=false, skrócony budget i brak zegara AI;
- wartość rzeczywiście wybranego ruchu, odrzucony ryzykowny prefix i
  fallback, stratę AP, hazard, natywny target i rzeczywiste rozstrzygnięcie;
- osobno patrol waypoint vs faktycznie wykonany ruch w następnej turze.
Nie nazywać nieznanej przyszłej trasy „Clear”, ani kodu źródłowego
„skuteczną zasadzką” bez raportu gry.
