# HELPER #111 — zasadzka, trzy potwierdzone tury, wybór Overwatch (v48 source)

Baza: `main 1a4df7b74f3dcb3d2ebc400138069f64efd4cb32`, branch `helper/111-ambush-overwatch-v48`. Ten dokument rozróżnia **obserwację** z gry, **zmianę źródeł**, **test automatyczny** i **nieprzetestowane zachowanie natywne**.

## Odtworzone dowody v46

Użyto załącznika `AutoplayXCom2-20261121-124810-8a828ea5(1).zip`, bez publikowania jego prywatnych logów. `Logs/Launch.log` zawiera pięć sesji `mission-report-v46`:

| Misja | Logowane obserwacje `patrol_group` | Różne ID grup | Decyzje `patrol_ambush_state` | `patrol_evidence_unknown` | `urgent_mission_preempts` |
| --- | ---: | ---: | ---: | ---: | ---: |
| SabotageCC | 42 | 4 | 86 | 73 | 13 |
| GasStation | 21 | 3 | 62 | 62 | 0 |
| Cemetery | 63 | 5 | 153 | 153 | 0 |
| TerrorBar | 28 | 5 | 91 | 91 | 0 |
| Blood Killer / SabotageTransmitter | 45 | 3 | 64 | 0 | 64 |
| Razem | 199 | — | **456** | **379** | **77** |

We wszystkich 456 stanach planera pole `group=0`. Zdarzenia `patrol_group` to obserwacje istniejących `XComGameState_AIGroup` z `CurrentTargetLocation`, **bez poświadczenia**, że dany ID należy do `AIPlayerData.PatrolGroupList`, ma świeży zegar, przesuwający się waypoint i aktualnie dostępnych członków. Samo wystąpienie `patrol_group` nie dowodzi błędu selektora. W v46 nie ma wystarczających danych, aby udowodnić, który z warunków odrzucił konkretny potencjalny patrol. W v48 `contact_snapshot` i `patrol_ambush_state` dopisują `patrol_selection`/`selection`: brak na liście z liczbą przeskanowanych grup, poprawnie zweryfikowana grupa lub konkretna przyczyna niepełnych danych. Nie rozluźniono warunków bezpieczeństwa.

Według raportu LEAD we wszystkich misjach było 124 zaakceptowanych rozkazów Overwatch AI, 130 natywnych uzbrojeń drużyny i 37 rozstrzygniętych strzałów reakcyjnych. Udane reakcje 4/4 GasStation t9, 4/4 Cemetery t3, 5/5 TerrorBar t1 nie są strzałami potwierdzonymi **do wybranego patrolu**: brak jakiegokolwiek wyboru takiego patrolu. Nie należy wyliczać `full_patrol_salvo` z tych sum.

## Poprawka A — liczenie rzeczywistych tur oczekiwania

Przed zmianą `CanWaitWindow` wymagało `LastTurn-StartTurn > 0`, a `Refresh` blokowało epizod według tur od pierwszego wykrycia. Zmiana waypointu tej samej grupy resetowała `StartTurn`, `PreparedMoves` i `OrderedReactions`, pozwalając przypadkowo odnowić limit. Domyślne `MaxSetupTurns=2`.

Po zmianie `ConfirmedWaits` jest licznikiem **jednego epizodu jednej potwierdzonej grupy**, a nie licznikiem decyzji czy żołnierzy. `NoteWaitRequested` rejestruje intencję dopiero po rzeczywiście zaakceptowanym ruchu stagingowym lub zbrojeniu reakcji. Po wywołaniu `PerformEndTurn` sam zwrócony bool nie wystarcza do zaliczenia; jedynie istniejąca ścieżka `ConfirmEndTurnRequest` po `SkipTurn` w historii lub realnej zmianie gracza/tury wywołuje `NoteWaitConfirmed`. Zduplikowane potwierdzenie, obce żądanie, odrzucony bilet i OFF nie zwiększają liczby. Domyślny limit to **3 potwierdzone pełne tury**. W pierwszej chwili po złożeniu setupu licznik wynosi 0: można zakończyć turę, a po trzecim potwierdzeniu kolejne oczekiwanie jest niedozwolone.

Zmiana waypointu **tej samej grupy** aktualizuje punkt docelowy, ale nie resetuje liczby wykonanych oczekiwań ani zaakceptowanych akcji. Nowy, faktycznie zweryfikowany identyfikator grupy zaczyna inny epizod. Brak bieżącej wiarygodnej informacji, kontakt, pilny cel, śmierć/krwawienie, przejście misji i wyłączenie nadal mogą zakończyć przygotowanie wcześniej. W v48 `patrol_ambush_wait` zapisuje `completed`, a potwierdzenie `patrol_ambush_wait_confirmed` zapisuje także numer native turn. Przed realnym wyborem patrolu żadna próba v46 nie demonstruje tego mechanizmu end-to-end w grze.

## Poprawka B — Overwatch a osobista okazja

W TerrorBar t7 trzy decyzje z Overwatch ocenionym na 17 nie zakończyły się strzałem. Ostatnie zaobserwowane podstawowe akcje tych żołnierzy miały `AA_NoTargets`. Widoczność Shieldbearera **dla drużyny** nie dowodzi dostępności sensownej linii dla poszczególnego strzelca; z v46 nie wynika pewność, że ruch byłby bezpieczny lub dawał lepszy strzał.

W poprzedniej funkcji `ScoreSelfAction` warunek `VisibleEnemies.Length > 0 || bRecentContact` przyznawał 17 każdemu żołnierzowi nawet przy kontakcie wyłącznie pamiętanym lub widzianym przez kolegę. Teraz ograniczony (maks. 64 referencje) odczyt osobistego obecnego geometrycznego LOS do wroga obecnego w natywnej widoczności drużyny ustala, czy można zastosować istniejącą wysoką wycenę. W razie jedynie drużynowego/pamiętanego kontaktu Overwatch dostaje **5**; bez kontaktu **2**. Osobista obecna linia zachowuje **17** (lub **22** przy ukryciu). Są to heurystyki, nie prognozy wrogiego ruchu, nie natywny target ani gwarancja reakcji. Aktualny legalny strzał, niebieski ruch, wsparcie i cele dalej konkurują zwykłą punktacją. Zakaz ryzykowania odzyskiwalnego kontrolowanego sojusznika pozostaje bez zmian.

## Powrót na wcześniej odwiedzone pole

W v46 cztery z 168 zaakceptowanych ruchów wracały na wcześniejszy endpoint tego samego żołnierza, wszystkie w późniejszej turze. Cemetery D76: szacowana ekspozycja spadła z 83,60 do 8,26, potem żołnierz wykonał strzał. Nie ma podstaw do bezwzględnego blokowania takich powrotów. `APX_RouteTempo.SoftVisitPenalty` pozostaje miękkim kosztem, a istniejący emergency/necessary fallback pozwala wybrać potrzebne pole. Dodano regresję korzystnego powrotu. Nie znaleziono w obecnym logu dowodu szkodliwego cyklu powrotów w **tej samej turze** wymagającego nowej blokady; ten scenariusz należy obserwować w kolejnej próbie.

## Testy i kryterium odbioru

Automatyczne Python: `tests/test_ambush_overwatch_v48.py` wykonuje prawdziwe pomocnicze funkcje UC dla 0/1/2/3 potwierdzeń, niepowiązanego biletu, ponownego wywołania, braku setupu, wyboru OW 2/5/17/22; kontrakty źródłowe gwarantują brak resetu przy waypointach, native-confirmed ticket, budżet skanu i zachowanie guard sojusznika. Syntetyczny ZIP→CLI weryfikuje, że logowanie `group=0` nie zmienia się w fałszywą pełną salwę, a uzbrojenie nie jest liczone jako oddany strzał. Stare testy v40 dostosowano do odrębnego licznika i konfiguracji 3 tur.

Dalszy **Windows SDK make i natywne WOTC E2E** po scaIeniu przez LEAD:
1. Uruchomić wspólną paczkę źródłową i sprawdzić 0 błędów kompilacji, stan HUD, OFF/ON i brak nielegalnych akcji.
2. W misji z rzeczywistym patrole-m zobaczyć `selection=verified_stored_patrol`, etap stagingowy po legalnym native blue/OW, a następnie `patrol_ambush_wait_confirmed completed=1,2,3`. Czwarte żądanie czekania **na ten sam patrol** nie może się pojawić; aktualizacja waypointu nie może wyzerować licznika.
3. Sprawdzić przerwanie przez presję celu, brak ruchu patrolu i utratę okazji. Jeśli żaden patrol nie jest zweryfikowany, zebrać `selection` zamiast wymuszać sztuczną grupę.
4. W TerrorBar t7, GasStation i Cemetery porównać wybrany Overwatch (score/źródło osobistego LOS) z rzeczywistymi dostępnymi strzałami, bezpiecznym ruchem, wsparciem i ratowaniem. Oddzielnie ocenić trafienie, pudło, brak wyzwolenia, wcześniejsze zabicie celu, ręczne uzbrojenie i ucięcie historii. **Pełna salwa do konkretnego patrolu nie jest potwierdzona**, dopóki rejestracja nie dowiedzie zarówno jego członkostwa, jak i rzeczywistych source/target reakcji.
5. Powtórzyć uzasadniony powrót na pole oraz poszukać niepotrzebnego oscylowania w jednej turze; zachować natywne koszty AP i pełną kontrolę bezpieczeństwa ścieżki.

**Granica dowodu:** CI, test źródłowy i syntetyczny log nie potwierdzają kompilacji UnrealScript pod Windows ani sukcesu nowego planu w grze. Nie zmieniono kryterium natywnego zwycięstwa i dodatnich punktów.
