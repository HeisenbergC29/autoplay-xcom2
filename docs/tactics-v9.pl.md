# Ratunek, łup i punktacja każdej symulacji — v9

V9 kontynuuje wspólny autoplay dla wszystkich misji WOTC i oficjalnych DLC.
[Zwycięstwo pierwszej misji Legacy](report-2026-11-03-legacy-v8-win.pl.md)
pozostaje wynikiem v8. Nowe źródła wymagają kompilacji Windows i osobnej próby;
następny oczekiwany etap to `ChallengeAbductionCemetery`.

## Podejście do wykrwawiającego się żołnierza

Planer potrafił już stabilizować legalny cel, lecz nie miał osobnego celu ruchu
do rannego poza zasięgiem. W zwycięskim raporcie medyk miał gotową stabilizację,
ale jej lista celów była pusta i później oddalił się od wykrwawiającego się
snajpera. V9 dodaje propozycję podejścia ratownika do własnego pacjenta.

Ratownik musi mieć rzeczywistą gotową zdolność stabilizacji i wystarczające AP
po niebieskim ruchu. Planer sprawdza koszt, warunki i natywny zasięg zdolności;
nie tworzy apteczki, ładunku ani dodatkowej akcji. Droga musi być znana,
aktualnie widoczna i wolna od zagrożeń na każdym kroku. Pacjent stanowi cel
podejścia również wtedy, gdy został za resztą oddziału. Ryzyko ostrzału obniża
wartość ruchu, szczególnie dla rannego ratownika.

Podejście do zasięgu ma wyższy priorytet niż częściowe zbliżenie. Przy jednej
pozostałej turze wykrwawiania częściowe podejście jest odrzucane: efekt wygasa
na początku następnej tury właściciela. Sama stabilizacja nadal wymaga
natywnego legalnego celu po wykonaniu ruchu. Odległość z przyszłego pola nie
dowodzi pełnej dostępności przy przeszkodach; ten przypadek wymaga próby w grze.
Stabilizacja zatrzymuje wykrwawianie i pozostawia żołnierza nieprzytomnego.
V9 nie dodaje osobnego planera przywracania przytomności ani noszenia ciał.

## Zbieranie łupu

V9 rozpoznaje natywne darmowe `Loot` i korzysta z legalnego celu w aktualnej
liście akcji. Pobranie przedmiotów wykonuje gra. Planer nie przenosi łupu
bezpośrednio do ekwipunku i nie zamyka okna wyboru przedmiotów.

Krótki ruch po łup jest rozważany po walce, gdy oddział nie ma widocznych
zagrożeń ani niedawnych kontaktów. Wymaga dwóch standardowych AP przed ruchem
i dostępnego, widocznego, niewygasłego łupu. Cała trasa podlega kontroli
zagrożeń, widoczności, wsparcia i niebezpiecznych przejść. Końcowe pole musi
mieścić się w rzeczywistym zasięgu podniesienia i mieć LOS do łupu. Jeśli
istnieje znany cel misji, podejście nie może oddalać od niego żołnierza.

Wykrwawiający się członek oddziału, ewakuacja, gotowa interakcja z celem lub
aktywny widoczny licznik misji blokują wycieczkę po łup. Darmowe podniesienie
również ustępuje ratunkowi i ewakuacji. Automatyczne zbieranie po ruchu i
odświeżona natywna lista celów pozostają rozstrzygające. Te ograniczenia
celowo mogą pozostawić część przedmiotów na mapie.

## Reguły punktacji odczytane z gry

Wartości podane wcześniej ręcznie zostały zastąpione regułami z SDK i
rzeczywistych tabel `XCom_Challenge` w logu GasStation/Cemetery. SDK potwierdza,
że premia za brak ran jest tracona przy pierwszym zranieniu żołnierza;
kolejne trafienia nie naliczają tej samej kary ponownie, a leczenie jej nie
odwraca. Przeżycie ma osobną premię. Fabularne wyłączenie przez
`LadderUnkillable` może zostać zaliczone jako utrata żołnierza.

Rejestrator v9 odczytuje oficjalne `CumulativeScore` tylko dla tego samego etapu
Legacy. Zapisuje także rewizje natywnych zdarzeń punktowych. Różnica między
pierwszym a ostatnim odczytem (`recording_delta`) obejmuje okres od F8;
może pomijać wcześniejsze punkty albo późniejsze premie z zakończenia.
`added_points` i `ladder_bonus` są zachowywane jako obserwacje, bez ich
automatycznego sumowania w zastępstwie oficjalnego wyniku.

Odczyty `score_rule` pobierają parametry przez natywne funkcje
`GetSoldierScoring`, `GetTimeScoring`, `GetEnemyScoring` i `GetObjectiveScoring`.
Powstają tylko w Legacy, dla tej samej drabinki i etapu. Reguła przeciwnika
jest odczytywana przy jego widocznym podglądzie, a reguła celu przy zaliczeniu
jawnej pozycji listy. Te odczyty nie przyznają punktów i nie ujawniają
nieznanych przeciwników ani ukrytych celów.

## Wspólna ocena wszystkich misji

Analizator stosuje profil `wotc_legacy_observed_v1` do każdej sesji, również
Gatecrashera i innych misji bez punktacji w grze. Parametry i pochodzenie są
zapisane w [archiwalnym legacy-score-rules-v1.json](../tools/legacy-score-rules-v1.json).
Wspólny profil zachowuje stałą skalę między próbami; odczytane reguły konkretnej
misji są dodatkowo zachowywane w `native_rules_observed`.

| Składnik wspólnego profilu | Reguła |
| --- | --- |
| Jawnie zaliczony cel, także poboczny | 10000 na początku, spadek 1000 na turę po przesunięciu 1, minimum 5000 |
| Faceless, Viper, Sectoid, PsiZombieCivilian | 1500 na początku, spadek 100 na turę po przesunięciu 1, minimum 1000 |
| Muton | 3000 na początku, spadek 200 na turę po przesunięciu 1, minimum 2000 |
| Żołnierz kwalifikowany przez reguły gry | Premia 1000 za brak ran oraz 5000 za przeżycie; każda tracona najwyżej raz |
| Jawnie uratowany cywil | 1000 |
| Inny typ przeciwnika | Jawne domyślne parametry struktury SDK, oznaczone jako zastępstwo nieodczytanego nadpisania |

Konwencja spadku to
`max(min_points, starting_points - max(0, turn - turn_offset) * decrease_per_turn)`.
Odrębne wartości dotyczą przeciwników przywołanych i posiłków. Nieznane
pochodzenie jest oznaczane; zniknięcie z widoku i samo HP równe zero nie
potwierdzają zabicia. Znany własny żołnierz przejęty przez wroga nie staje się
punktowanym przeciwnikiem; znany przeciwnik nie traci swojej klasyfikacji
tylko przez tymczasowe przejęcie go przez gracza.

SDK udostępnia funkcje przyznawania punktów za zabicia, cele i zakończenie
misji jako natywne, bez pełnego algorytmu C++. Dlatego ten profil jest jawną
miarą porównawczą. Premie za wyłączenie wroga na koniec, restarty, dodatkowe
premie drabinki i czas rzeczywisty pozostają poza jego zakresem
(`excluded_native_components`). Nie jest to kopia oficjalnego wyniku.

Brak danych dla włączonych kategorii daje `status=partial`, listę
`missing_components` i sumę zaobserwowanych składników `observed_subtotal`.
`total` jest dostępny dopiero przy dowiedzionej kompletności porównania.
F8 nie potwierdza początku całej misji, więc aktualna rejestracja nie deklaruje
pełnego pokrycia. Wygrana nie dopisuje automatycznie celów pobocznych,
a starsze raporty nie otrzymują danych, których wcześniej nie zapisały.
Pole `score` w decyzjach planera i startowe `MaxScore` gry nadal oznaczają
odpowiednio ocenę rozkazu i maksymalną pulę, a nie zdobyte punkty.

[Kompilacja i następna próba Legacy](legacy-test.pl.md) ·
[Format rejestracji](mission-recording.pl.md) ·
[Zakres testów](TESTING.pl.md)
