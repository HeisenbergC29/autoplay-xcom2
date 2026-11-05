# Druga próba „Blast From the Past”: mission-report-v6

Nowy `Launch.log` z `AutoplayXCom2-20261102-193820-e2abbe35.zip` zawiera sesję
`2026-11-2_20-33-26-635_915`, rewizję `mission-report-v6`, misję
`ChallengeAbductionGasStation` i trudność `2` (Dowódca). Próba zakończyła się
porażką w turze 5. Poprawka oceny `AidProtocol` zmieniła zachowanie, lecz nie
uratowała oddziału. Audyt ujawnił dwie dalsze niespójności planowania: szarża
omija ograniczenia pozycji stosowane przy zwykłym ruchu, a wycena ruchu
snajpera nie uwzględnia utraty możliwości strzału z karabinu.

Numery linii odnoszą się do `Logs/Launch.log` w tym ZIP-ie. Początek sesji
znajduje się w linii 363, faza końcowa i wynik w liniach 3043–3051.
[Raport poprzedniej próby v5](report-2026-11-02-legacy.pl.md) opisuje wcześniejszą
porażkę i powód poprawki linii widzenia.

## Zawartość i integralność raportu

Sprawdzono rozmiar oraz SHA-256 każdego logu wymienionego w `manifest.json`:
wszystkie **4 z 4 wpisów** są zgodne. Tylko bieżący `Launch.log` jest nowy:
ma 612621 bajtów i SHA-256
`23a26145a8b481213352e41f1d464d50587c3c7a1647254d263f425279d21627`.

| Plik w nowym archiwum | Powtórzenie wcześniejszego logu |
| --- | --- |
| `Logs/Launch-backup-2026.11.02-20.32.16.log` | `Launch.log` z ZIP-a `190216`, poprzednia próba v5 |
| `Logs/Launch-backup-2026.11.02-17.31.00.log` | `Launch.log` z ZIP-a `162041`, Gatecrasher |
| `Logs/Launch-backup-2026.11.02-17.02.08.log` | backup o tej samej nazwie we wcześniejszych ZIP-ach, Gatecrasher |

Nowe archiwum zawiera cztery sesje, ale tylko jedna jest nową próbą.
Po usunięciu powtórzeń ze wszystkich trzech raportów pozostaje sześć sesji:
cztery starsze próby Gatecrashera oraz dwie próby Legacy Operations.
Nie należy traktować trzech backupów jako kolejnych testów v6.

## Działania, wynik i błędy wykonania

Zapisano 13 zaakceptowanych poleceń, bez odrzuceń:

- 2 ruchy;
- 3 `StandardShot`, 3 `SniperStandardFire`, 1 `PistolStandardShot`;
- 1 `SwordSlice`, 1 `AidProtocol`, 1 `Reload`, 1 `PistolOverwatch`;
- 0 granatów i 0 `HunkerDown`.

Odnotowano trzy pudła przyjaznych jednostek: strzały do Viper przy 79% i 40%
oraz reakcję pistoletem przy 36% (linie 2378, 2710 i 3049). Wrogie pazury
także raz chybiają żołnierza `63486`: `result_target.hit=3` (`eHit_Miss`),
bez zmiany jego HP (linia 1989). Główny `result` ataku obszarowego podaje
`eHit_Success`; licznik pudeł analizatora oparty na głównych wynikach nie
obejmuje tego osobnego celu. To opis zarejestrowanych wyników, a nie dowód,
że raport obejmuje każdy szczegół działań silnika.

Końcowo `63468` i `63486` są martwi. Central `63474` pozostaje żywy z 1/7 HP,
lecz niezdolny do działania. Snajper `63480` ma 1/5 HP, jest niezdolny do
działania i krwawi. Viper `63497` przeżywa z pełnymi 8 HP (linie 3044–3048).

Nie ma `ScriptWarning`, `Accessed None`, `Critical` ani `Fatal`; analizator
nie zgłasza ostrzeżeń. Występują ostrzeżenia silnika. Autoplay dochodzi do
zakończenia misji, więc zapis nie wskazuje zawieszenia na interfejsie.

## AidProtocol: potwierdzony efekt i pozostały problem decyzji

W decyzji 5 specjalista `63468` używa `AidProtocol` na Centralu `63474`,
z wynikiem `32.8`, przed własnym cofnięciem ocenionym na `26.0`
(linie 1308–1315). W poprzedniej próbie v5 wybierał siebie. Zmiana oceny
linii widzenia przesunęła zatem najlepszy cel wsparcia, lecz nie wystarczyła,
aby specjalista opuścił niebezpieczną pozycję. Po turze przeciwnika ginie
od `ScythingClaws` (linie 1470–1472).

Ochrona Centrala ma widoczny efekt: Viper wykonuje `GetOverHere` z szansą 70%
(linia 1457), podczas gdy w poprzednim raporcie ten atak na Centrala miał
90%. W obu przypadkach trafia. Porażka v6 nie obala poprawki `AidProtocol`:
niższa szansa trafienia nadal dopuszcza trafienie. Z drugiej strony samo
obniżenie szansy nie potwierdza, że wybrany rodzaj wsparcia i pozostawienie
specjalisty w miejscu były najlepszą decyzją dla całego oddziału.

## Decyzja 3: szarża poza wsparcie oddziału

Central wybiera `SwordSlice` z wynikiem `76.13`, przed strzałami dwóch innych
żołnierzy ocenionymi na `68.92` i `58.3` (linie 1008–1019). Zabija Faceless,
ale kończy na `(23,28,1)` bez AP (linia 1082). Następnie Viper ściąga go na
`(31,27,1)` i wiąże (linie 1408, 1457–1458).

Porównanie pozycji zapisanych w logu z regułami kodu pokazuje konkretną
niespójność. Central zaczynał jeden kafel od najbliższego sojusznika.
Po szarży najbliższy sojusznik znajduje się około `10.198` kafla od niego.
Przy takim początku zwykły ruch bojowy odrzuciłby tę pozycję jako wyjście poza
przyjęty dystans wsparcia 10 kafli. `HasRequiredMeleePath` w v6 sprawdzało
ścieżkę i zagrożenia, lecz pomijało część ograniczeń formacji oraz znanego
terenu, obowiązujących zwykły ruch.

Wniosek dotyczy spójności reguł, nie twierdzenia, że odległość `10.198`
gwarantuje porażkę. Odrzucenie tej szarży zmieni następne decyzje; silnik nie
rozegrał w raporcie alternatywnego ataku ani pozycji.

## Bind: legalna blokada zdolności

Po schwytaniu Central nie może normalnie działać mimo odświeżonych AP.
Log podaje m.in. `AA_UnitIsBound` dla zdolności oraz `AA_ValueCheckFailed`
dla ruchu (linie 1525–1532). To blokada wynikająca z efektu `Bind`, a nie
potwierdzony błąd sprawdzania `IsIncapacitated()`.

Viper podtrzymuje ucisk aż do wyłączenia Centrala (linie 1967, 2392–2393),
potem chwyta żołnierza `63486` i zabija go kolejnymi podtrzymaniami
(linie 2468–2469, 2727 i 3024). Ograniczenie szarży ma zapobiegać wejściu
w taką sytuację; nie daje prawa ignorowania legalności zdolności ani
wykonywania poleceń przez związaną jednostkę.

## Decyzja 6: koszt straconego strzału snajperskiego

Ruch snajpera ma wynik `39.6857` i wygrywa z dostępnym strzałem sojusznika
`39.656` różnicą około `0.0297` (linie 1689–1698). Zmiana pozycji snajpera
jest ceniona za spadek jego łącznego ryzyka z `38.1675` do `4.2113`.
Podgląd v6 rozdziela przeciwników:

- Faceless ma `melee_only=True`; dystans rośnie z `6.4031` do `11.7047`,
  a wkład ryzyka spada z `22.3875` do `1.1812` (linia 1695);
- Viper ma `melee_only=False`; przed ruchem nie ma linii widzenia i jego
  wkład wynosi `10.5` (linia 1696).

To potwierdza prawidłowe rozpoznawanie Faceless jako przeciwnika wręcz.
Spadek ryzyka nie wynika z błędnego zastosowania osłony przeciw jego pazurom.

Ruch zużywa jednak jeden z dwóch AP snajpera. Legalny wcześniej
`SniperStandardFire` wymaga obu AP, więc po ruchu pozostaje pistolet.
Sojusznik trafia Faceless za 5, pozostawiając 3 HP (linia 1853), a snajper
trafia pistoletem za 2, pozostawiając 1 HP (linia 1945). Faceless regeneruje
się i wymaga następnego ataku w kolejnej turze (linia 2288).

Przy trafieniach dwa dostępne karabiny dawały zakres obrażeń `4–6 + 4–6`,
a po ruchu pozostaje `4–6 + 2–3`. Wybrany ruch ma zatem koszt ofensywny,
którego dotychczasowa ocena nie uwzględniała. Nie oznacza to, że snajper
powinien zawsze strzelać: ryzyko pozostania, pudła, pozycja docelowa i stan
innych jednostek nadal mają znaczenie.

## Granaty

Wykonano 17 sprawdzeń dostępnej, obsługiwanej zdolności granatu i 60 ocen
punktów: 34 odrzucono przez zasięg, 1 przez trajektorię, a 25 przez
bezpieczeństwo wybuchu. Nie przyjęto żadnego kandydata. Licznik odrzuceń
wartości ataku wynosi 0.

Zapisane powody obejmują chronione jednostki, cele misji i niebezpieczną
scenerię. Powody szczegółowe są migawkami ostatniego odrzucenia w danym
skanie, a nie histogramem wszystkich punktów. Brak granatu nie uzasadnia
usuwania tych zabezpieczeń i nie dowodzi istnienia bezpiecznego rzutu.

## Zmiany w mission-report-v7

Wdrożono dwie poprawki wynikające z audytu:

1. `HasRequiredMeleePath` stosuje ograniczenia znanego terenu, wsparcia
   na trasie i formacji na końcu ruchu także do szarż. Zwykły ruch i ruch
   związany z atakiem mają dzięki temu podlegać tym samym właściwym regułom.
2. Wycena ruchu uwzględnia koszt utraty legalnych ataków po wydaniu AP
   na niebieski ruch. Obejmuje to przypadek karabinu snajperskiego wymagającego
   dwóch AP, gdy po ruchu pozostaje słabszy pistolet. To składnik punktacji,
   nie bezwarunkowy zakaz cofania się.

Porównanie ofensywy używa tych samych bieżących celów przy rzeczywistym
budżecie AP oraz lokalnej kopii AP pomniejszonej o koszt niebieskiego ruchu.
Stosuje natywne typy punktów, koszty broni i reguły darmowych akcji. Nie
przewiduje nowej widoczności ani szans trafienia na końcu trasy. Różnica
najlepszych ocen obniża wynik ruchu bojowego; pozostaje wyjątek wyraźnie
zmniejszającego ryzyko odwrotu rannego żołnierza. W raporcie wartości te
opisują `best_attack_now`, `best_attack_after_move_ap` i `potential_attack_loss`.
Nie należy podawać dokładnej nowej punktacji decyzji 6 na podstawie samego
strzału pistoletem już po ruchu, bo jego pozycja i warunki były wtedy inne.

Weryfikacja: **189 testów Python zaliczonych, bez pominięć**, z pełnymi
przesłanymi źródłami SDK. Audyt odwołań do SDK także zaliczony (11 klas moda,
29 skonfigurowanych nazw zdolności). Testy scenariuszy i kontraktów nie
zastępują kompilatora i gry. Przedstawione alternatywy nie zostały rozegrane
przez silnik gry. Nowa kompilacja Windows
i kolejny test misji są nadal potrzebne; analiza oraz zmiany nie gwarantują
zwycięstwa.

[Instrukcja kompilacji i następnej próby](legacy-test.pl.md).
