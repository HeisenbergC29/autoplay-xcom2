# Patrole, wykrycie, zasadzka i tempo marszu

Pochodne ustalenia LEAD z 14 listopada 2026, na podstawie dostarczonego SDK
WOTC i konfiguracji gry. Ścieżki źródeł poniżej są względne wobec SDK;
nie publikujemy jego plików. Stan planistów sprawdzono na bazie v37.

Użytkownik zezwolił na wykorzystanie wszystkich dostępnych zapisanych danych
patrolu, w tym pełnej trasy, jeżeli rzeczywiście istnieje. To rozszerzenie
wcześniejszej zgody na bieżący cel patrolu. Odczyt pozostaje obserwacyjny;
nie uruchamiamy przyszłych decyzji AI ani losowań w celu ich przewidzenia.
`EnableFullIntel=false` zachowuje wiedzę opartą na natywnej widoczności.

**To analiza i zakres implementacji, nie opis gotowej nowej zasadzki.**
Kolejka [#86](https://github.com/HeisenbergC29/autoplay-xcom2/issues/86)
poprzedza jeden zbiorczy test. Windows make i próby nowych zachowań:
**NOT RUN**; [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4)
pozostaje wstrzymane do ukończenia bieżących prac LEAD i HELPERA.

## Jakie dane patrolu istnieją

Typowy patrol w sprawdzonych źródłach nie przechowuje stałej, kompletnej
trasy na wiele tur. `XComGame/Classes/XComGameState_AIGroup.uc:43–46`
zawiera jedynie zakomentowaną zapowiedź takich pól. Bieżący cel i czas
jego wyboru są zapisane w `CurrentTargetLocation` oraz
`TurnCountForLastDestination` (`:55–57`); strefa encounter określa możliwy
obszar, a nie kolejność przyszłych punktów (`:21–35`).

| Zapisane dane | Właściwe zastosowanie |
| --- | --- |
| Bieżący waypoint i jego wiek | Prawdopodobny kierunek podejścia, po walidacji aktualnej grupy i wieku. |
| Cele członków i cache odcinka lidera | Geometria konkretnego ruchu; trzeba ustalić, czy nie jest już przebyty. |
| Połączone węzły mapy | Możliwe korytarze, bez przypisywania grupie pewnej kolejności. |
| Brak, stare albo ucięte dane | Jawna niepewność; nie potwierdzają wolnej drogi. |

`XGAIPatrolGroup.uc:12–21,48–54,430–466` pokazuje ulotny cache pojedynczego
odcinka. W turze XCOM niepusta ścieżka może pochodzić z zakończonego ruchu
wroga. Koniec na obecnym polu lidera nie dowodzi przyszłej trasy. Konieczna
jest zgodność grupy, lidera, członków, bitwy i historii; brak znacznika czasu
lub cofnięcie historii wyklucza domyślne uznanie cache za świeży.

Wiek celu porównujemy z właściwym `AIPlayerData.StatsData.TurnCount`, nie
z licznikiem tur gracza XCOM. Nieznany zegar, wartość domyślna lub osiągnięty
cel wymagają ponownej oceny. Graf `XComAlienPathNode.LinkedNodes`
(`XComAlienPathNode.uc:51–54,74–75`) można czytać z ograniczonym przejściem.
Nie tworzymy z niego fikcyjnej, wybranej przez patrol trasy.

Nie wywołujemy dla prognozy `ShouldMoveToIntercept`, `ComputeGroupPath`
ani `GetGroupMovePaths`: wybierają cel lub zmieniają cache. Również
`XGAIPlayerNavigator.GetGroupInfo` może odświeżyć stan. Dostępne są odczyty
istniejących pól z własną walidacją. Do tych ustaleń nie potrzeba nowego SDK.

## Wykrywanie i osłona

Promień jest przydatny do wstępnej selekcji, lecz wynik zależy także od LOS,
efektów, relacji jednostek i kierunku ruchu. `XComWorldData.uc:50,56,71`
definiuje 64 jednostki świata na metr i 96 na poziome pole: przykładowe
27 m oznacza 18 pól, a 12 m — 8. Nie są to stałe zasięgi wszystkich jednostek.
W concealment stosujemy natywne `GetConcealmentDetectionDistance`,
`UnitBreaksConcealment` i wyjątki ignorujące dystans.

- Gdy porusza się **wykrywający wróg**, stock sprawdza także brak osłony
  celu z jego kierunku (`XComGameState_Unit.uc:9006–9028`). Osłona miejsca
  zasadzki musi więc odpowiadać spodziewanemu podejściu patrolu.
- Gdy porusza się **ukryty żołnierz**, ścieżka wykrycia nie ma tego samego
  warunku osłony (`:9039–9059`). Bezpieczne stanie i przejście przez dane
  pole wymagają odrębnej oceny.
- Po ujawnieniu potrzebne są widoczność rozgrywki, efekty i podglądy zza
  osłony (`:598–665,9062–9069`). Sam okrąg zasięgu wzroku nie rozstrzyga LOS.

Cywile, szyby, drzwi, niszczące przejścia i chmury zagrożeń pozostają częścią
oceny całej trasy. Pełna znajomość pozycji przeciwników ich nie pomija.

## Zasadzka i szybki marsz — kolejność prac

1. [#87: wspólna ocena kontaktu i wykrycia](https://github.com/HeisenbergC29/autoplay-xcom2/issues/87)
   ma połączyć dane patrolu, świeżość i całą ścieżkę. Wynik `Clear`, `Caution`
   lub `Unknown` podaje źródło i horyzont prognozy oraz wpływa na decyzję
   planera. Sam zapis nowej telemetrii nie realizuje tego etapu.
2. [#88: proaktywna zasadzka](https://github.com/HeisenbergC29/autoplay-xcom2/issues/88)
   oceni kierunkową osłonę, zasięg, wysokość, wsparcie, rozstawienie pod AoE,
   hazardy i inne grupy. Przygotowanie i oczekiwanie mają limit oraz warunki
   przerwania. Timer, wykrwawianie, ratunek i pilny cel wyprzedzają czekanie.
3. [#89: warunkowy szybki marsz](https://github.com/HeisenbergC29/autoplay-xcom2/issues/89)
   wykorzysta potwierdzony wolny korytarz dla zwykłego dojścia do celu.
   Zagrożony środek trasy dyskwalifikuje ruch mimo bezpiecznego końca.
   Niepewność zachowuje krótszy legalny wariant.

Overwatch wymaga własnych natywnych AP, broni i reakcji na rzeczywisty ruch.
`OverwatchShot` wymaga ujawnionego strzelca oraz właściwych warunków celu
(`X2Ability_DefaultAbilitySet.uc:648–685`); uzbrojenie reakcji w ukryciu
nie gwarantuje jej odpalenia. Przygotowanie kilku reakcji wymaga dostępnego
legalnego otwarcia i korzyści względem bezpośredniego ataku. Nie wymuszamy
ujawnienia ani rozbiegania przeciwników. Brak presji czasu pozwala lepiej
przygotować zasadzkę, lecz nie gwarantuje idealnej okazji dla każdego patrolu.

Długi ruch musi mieścić się w faktycznych kosztach natywnej osiągalnej
ścieżki i własnych dostępnych punktach. Ogólne `StandardMove AA_Success`
oraz `2 * Mobility` nie dowodzą opłacalności dowolnej trasy. Źródłem kosztów
są `X2ReachableTilesCache`, konstrukcja path data w `XComTacticalController`
i `X2AbilityCost_ActionPoints.ApplyCost`. Zachowujemy rezerwę na interakcję.

Każda decyzja korzysta ze wspólnego ograniczonego budżetu grup, członków,
detektorów, pól i LOS. Ucięty skan, stary cache, nieznany ruch specjalny albo
wyczerpany budżet oznaczają `Unknown`, nigdy domyślne `Clear`. Prognoza
następnej tury może używać wiedzy o szablonach i obserwowanych efektach;
nie czyta bieżących bojowych AP, amunicji, cooldownów ani RNG wroga.
Ocena jest odnawiana po rzeczywistej akcji. `Clear` dotyczy zadeklarowanego
horyzontu, nie nieznanych przyszłych skryptów misji.
