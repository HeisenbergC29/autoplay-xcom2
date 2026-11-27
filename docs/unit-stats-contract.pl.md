# #125 — kontrakt odczytu bieżących statystyk jednostek

Etap 1 programu [#120](https://github.com/HeisenbergC29/autoplay-xcom2/issues/120).
Baza: `bead4246c55b690d31e9609b5bdddf9a16d8e2c0` (v50).
To nowy, samodzielny moduł wiedzy, jeszcze **bez konsumenta rankingowego**.
Nie zmienia wyceny zagrożenia, wyboru akcji, ruchu, widoczności ani markerów v50.

## Kontrakt API

`APX_UnitStats.ReadUnitStats(History, HistoryIndex, ObserverID, SubjectID, Values, Status)`

Wejścia: aktualna instancja `XComGameStateHistory`, jej bieżący indeks, identyfikatory
lokalnej jednostki XCOM i jednostki odczytywanej. Oba obiekty rozwiązywane przez
`GetGameStateForObjectID(..., eReturnType_Reference, HistoryIndex)`.
Identyfikatory służą wyłącznie do odszukania i uprawnień, a nie do oceny.
Wyjścia: dwa równoległe wektory stock types `array<float>` i `array<int>`,
każdy zawsze o długości 7, bez zależności DependsOn od własnej struktury.

| Indeks / stała | Znaczenie | Jednostka i źródło WOTC |
| --- | --- | --- |
| 0 FactHP | Bieżące HP | punkty HP, GetCurrentStat(eStat_HP) |
| 1 FactMaxHP | Bieżące maks. HP | punkty HP, GetMaxStat(eStat_HP) |
| 2 FactShieldHP | Bieżąca pozostała tarcza | punkty HP tarczy, GetCurrentStat(eStat_ShieldHP) |
| 3 FactArmor | Bieżący pancerz po bonusach i shred | punkty redukcji obrażeń wg GetArmorMitigationForUnitFlag() |
| 4 FactOffense | Celność jako statystyka jednostki | punkty modyfikatora celności, GetCurrentStat(eStat_Offense) |
| 5 FactDefense | Obrona jako statystyka jednostki | punkty modyfikatora obrony, GetCurrentStat(eStat_Defense) |
| 6 FactMobility | Mobilność jako statystyka jednostki | natywna wartość statystyki ruchu (metry w przeliczeniu XGUnit.GetMaxPathDistance na akcję), GetCurrentStat(eStat_Mobility) |

`Status[i]=1`: znany odczyt, także **0**. `Status[i]=0`: nieznany;
wówczas `Values[i]=0` jest wyłącznie wypełnieniem, nie pomiarem.
Dla przykładu: rzeczywisty zerowy pancerz (0,1), niezweryfikowany pancerz (0,0).
Ujemna celność/obrona pozostają legalnymi statystykami; dla nieujemnych
statystyk ujemny odczyt oznacza brak wiarygodnej wartości. NaN jest nieznane.
Nie przycinamy wartości do przedziału 0–100 ani nie narzucamy wag.

Zwrócone true oznacza dozwolony, aktualny snapshot, a nie gwarancję pełności
każdego pola. False zeruje obie tablice i oznacza wszystkie pola jako unknown.
Brak szablonu, obiektu lub usług taktyki, obcy obserwator, brak uprawnień,
nieaktualny indeks/inna instancja historii => false. Po odczycie ponownie
sprawdzamy bieżący indeks i instancję: zmiana nie może opublikować mieszanych
danych. Metody składowe są prywatne. Nie zapisujemy cache na kolejne decyzje.
W stock SDK wszystkie standardowe statystyki są inicjalizowane przy tworzeniu
jednostki; API float nie wystawia oddzielnego bitu „brak wartości” dla
każdej z nich. Poprawne zero w istniejącym i dozwolonym obiekcie jest znane,
nie można natomiast rozpoznać uszkodzonej implementacji moda, która zwraca
zero zamiast prawidłowej wartości.

## Audyt SDK (prywatny pakiet, nie publikowany)

Źródło: dostarczony przez użytkownika `sdk-current-for-review(1).zip`,
klasy `XComGame/Classes`. Odwołania poniżej są nazwami metod w SDK, nie
kopią chronionych źródeł.

- `XComGameState_Unit.GetCurrentStat`, `GetMaxStat`, `GetStatModifiers`
  to native API. `OnCreation` inicjalizuje `CharacterStats`; definicja
  `CharacterStat` w `X2TacticalGameRulesetDataStructures` rozróżnia current,
  base oraz max z modyfikatorami. Stock `GetUISummary_UnitStats` odczytuje
  aktualne HP, aim, defense i mobility. Nie kopiujemy samych bazowych wartości
  szablonu, wliczonych już bonusów wyposażenia ani dodatkowych UI hooków.
- `UIUnitFlag` używa bieżącego `eStat_ShieldHP` i
  `GetArmorMitigationForUnitFlag`. Ten ostatni bierze aktualne
  `eStat_ArmorMitigation`, dolicza bonusy aktywnych efektów będących
  `X2Effect_BonusArmor` (w tym pochodne), odejmuje `Shredded`, ogranicza
  do minimum zero. `XComGameState_Unit.TakeDamage` aktualizuje shred
  przez `AddShreddedValue`. Nie odejmujemy go drugi raz.
- `GetArmorMitigation` korzysta ze ścieżki `RollArmorMitigation`; stock
  `RollArmorMitigation` mimo nazwy nie losuje już pancerza. Nie używamy jej:
  odczyt UnitFlag nie potrzebuje parametrów ataku ani żadnego losowania.
  Przed getterem sprawdzamy do 128 aktualnych referencji efektów i ich
  szablonów (stock getter zakłada ich istnienie). Brak/nierozwiązany/usunięty
  efekt lub przekroczenie limitu => nieznany pancerz, pozostałe poprawne
  statystyki nadal dostępne. Wartość jest zgodna z wyświetlanym pancerzem
  stock WOTC; efekty sytuacyjne spoza klasy BonusArmor, np. własne hooki
  rozstrzygnięcia obrażeń, nie są interpretowane w tej fazie.
- `X2AbilityToHitCalc_StandardAim` dolicza aktualne modyfikatory offense
  i defense, a dalej broń, zasięg, osłonę i inne warunki. Sam offense/defense
  nie jest prawdopodobieństwem trafienia. Nie uruchamiamy tej kalkulacji
  dla przyszłego/nielegalnego ataku.
- `XGUnit.GetMaxPathDistance` przelicza mobilność przez METERSTOUNITS
  i standardowe akcje na turę. Odczytujemy wyłącznie statystykę mobilności,
  bez sprawdzania dostępnych AP wroga i bez obietnicy osiągalnego pola.

Nieznany efekt modowany, który wpływa bezpośrednio na obrażenia lub strzał
poza odczytywanymi standardowymi statystykami, nie jest automatycznie
rozpoznaną cechą; potrzebny będzie kontrakt zdolności z #122. Natywne
API/stock efekty są traktowane jako odczyt; nie gwarantujemy poprawności
dowolnej zewnętrznej implementacji modyfikatora.

## Granice dostępu

Lokalny obserwator XCOM jest wymagany zawsze; własne jednostki muszą mieć
tego samego kontrolującego gracza i team. Odrzucamy usunięte obiekty,
cywili, kosmetyczne szablony. Żywego aktywnego wroga musi zwrócić istniejący
`APX_FullIntel.GetKnownEnemies` (tryb pełny albo native widoczność).
Nie dodajemy wyjątków od obecnej polityki. Odczyt nie obejmuje AP,
amunicji, ładunków, cooldownów, stanu gotowości ani zamiarów wroga.
Natywna dostępność akcji, LOS i celowanie pozostają niezależne.
Odczyt przeprowadzić raz na jednostkę na decyzję, nie raz na pole ruchu;
przy podpinaniu konsumentów można przekazać wynik w obrębie tej samej
ramki, bez cache przez turę. W tym etapie nie ma wywołań z pętli decyzji.

## Testy i ograniczenia

`tests/test_live_unit_stats.py` wykonuje rzeczywiste funkcje UC tej klasy
przez ograniczony translator instrukcji i kontrolowane test doubles dla
natywnego SDK. W przeciwieństwie do przepisania polityki do modelu testowego,
uruchamia produkcyjny przepływ ResetFacts → snapshot → autoryzacja →
PopulateFacts/ReadArmor → StoreFact/FactStatus → snapshot. Obejmuje wszystkie
metody, w tym: różne nazwy i ID przy tych samych statystykach; zmienione dane
tej samej jednostki; wartości pancerza 3→1→0 zwracane przez fixture native
getter; brak efektu i prawdziwe zero; ujemną obronę; wyczyszczenie starych
tablic; zmianę historii podczas odczytu; tylko indeks i referencje aktualne;
odmowę obcego/nieautoryzowanego dostępu. Warstwa SDK jest celowo stubowana,
więc 3→1→0 nie jest dowodem rzeczywistego strzału ani wykonania shred w grze.
Opcjonalne testy kontraktu SDK w tym samym pliku weryfikują rzeczywiste
deklaracje i semantykę stock getterów z APX_SDK_SOURCE_ROOT.

Dodanie klasy wymaga także jej wpisu na jawną listę klas opcjonalnych
w `tools/check-compiled-package.py`; test pełnej listy i test poprawnej
nadklasy zachowują zgodność starszych paczek i zakaz nieznanych klas.

## Późniejszy scenariusz WOTC

Po review i połączeniu następnego konsumenta z #123/#122/#126:
na jednej ramce odczytać znaną jednostkę własną i dozwolonego wroga,
porównać HP, shield i armor z native UI. Zmienić pancerz rzeczywistym
natywnym shred i odczytać nową ramkę; potwierdzić różnicę w profilu tej samej
jednostki. Porównać dwie jednostki z tą samą wartością statów i odmiennym
ID/nazwą, następnie efekt bonus armor/zmiana obrony/mobilności. Wyłączyć
FullIntel i sprawdzić, że nieujawniony wróg nie jest autoryzowany.
Nie trzeba modyfikować publicznego v50, aby przetestować te źródła.
Kompilacja Windows i wykonanie native scenariusza pozostają NOT RUN;
ten etap nie dokłada wywołania do produkcyjnego planera ani logowania
profilu. Scenariusz wymaga później debugowego wywołania API lub konsumenta,
a nie samego uruchomienia gry z nieużywaną klasą.
