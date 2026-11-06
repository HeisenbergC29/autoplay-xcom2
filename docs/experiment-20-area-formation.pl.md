# V22: rozstawienie ograniczające wspólne trafienia AoE

Baza: `e81ae2969ed122549be3188ef5c7b2cc9149ac24`, runtime v21 po poprawce
kompilacji oraz integracji raportowania #35/#36. Nowa rewizja:
`mission-report-v22`. Issue #20; wykonawca LEAD.

## Zachowanie

SquadPositionScore dodaje ograniczoną karę za największą próbkowaną grupę
w obszarze zawierającym przemieszczaną jednostkę. Sprawdza pozycje jednostek,
środki par i środki trójek zawierających tę jednostkę. Uwzględnia również
żywych nieprzytomnych sojuszników jako możliwe ofiary, zachowując ich
wykluczenie z kotwic wsparcia. Daleka nieruchoma grupa nie daje stałej kary
niezwiązanym z nią ruchom.

Przy domyślnej wadze 6 para dostaje dodatkowe −6, trójka −18, czwórka −36,
a większa grupa najwyżej −48. To skończona preferencja punktowa, bez zakazu
pól, dodatkowego OFF ani nowej rezerwacji pozycji. Używa istniejących miejsc
oceny formacji w ruchu bojowym, trasie misji, eksploracji i przygotowaniu
zasadzki. Nie zmienia legalności trasy, AP, osłon, oceny ekspozycji,
ratowania, wyjścia z trucizny czy ewakuacji.

`SquadAreaRiskRadiusTiles=3.0` jest heurystyką formacji. Nie jest deklaracją
natywnego promienia wszystkich granatów/zdolności, dokładnego działania
na piętrach ani legalności ataku wroga. Z zachowaniem istniejącej skali
odległości Z*0,5 bada geometrię najwyżej 12 pobliskich sojuszników i jednej
jednostki ruchomej; nie dodaje natywnych preview ani zapytań o zamiary, AP
czy cooldown przeciwnika. Wyszukiwanie jest ograniczone i nie gwarantuje
matematycznego maksimum wszystkich możliwych obszarów.

Źródła SDK: XGAIBehavior.FindAoETarget/TestAoEHits, X2Ability_Viper.PoisonSpit,
X2Item_DefaultGrenades.PoisonSpitGlob. Natywny glob ma promień 4 metry,
około 2,67 poziomego pola; o trafieniu rozstrzygają natywne pola/efekty.
Wartość 3 w modzie nie zastępuje tych reguł. Kod SDK pozostaje prywatny.

## Próba użytkownika

1. Skompilować wskazany końcowy commit v22, zainstalować świeży wynik
   i ponownie uruchomić grę. Potwierdzić rewizję i startowe
   formation_area_radius_tiles=3 oraz formation_area_weight=6.
2. Powtórzyć tę samą GasStation: porównać ustawienie i liczbę własnych
   trafionych PoisonSpit, otrzymane obrażenia/statusy, wynik oraz punkty.
   Mniejsza liczba ofiar AoE nie wystarcza bez victory i pewnego wyniku >0.
3. Jeżeli możliwe, sprawdzić parę w granacie w SabotageCC, żywego
   wykrwawiającego się, ciasny korytarz, pojedynczego ocalałego i ewakuację.
   Legalny konieczny ruch nadal ma być dostępny, a rozproszenie nie może
   zastępować pilnego ratunku ani nadmiernie oddalać od wsparcia.
4. Dla porównania jednej zmiennej ustawić
   `[AutoplayXCom2.APX_MissionPlanner] SquadAreaRiskWeight=0.0` przy tych
   samych pozostałych ustawieniach. To wyłącza nową karę bez zmiany full intel.
5. Przekazać raport i SHA także przy porażce. Obserwować czas decyzji,
   pętle i końce tur; nie ogłaszać naprawy dawnych awarii po jednej próbie.

Testy arytmetyczne i kontrakty źródłowe sprawdzają pary/trójki z raportów,
środki między celami, limit kary, brak kosztu dla samotnej jednostki i ochronę
wykrwawiających się bez przypisywania im wsparcia. Nie kompilują UnrealScript
i nie potwierdzają rzeczywistej listy trafień ani zwycięstwa. Windows WOTC SDK
i gra v22 pozostają NIEURUCHOMIONE do raportu użytkownika.
