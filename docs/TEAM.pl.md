# Organizacja pracy i komunikacja na GitHub

Ustalenia właściciela projektu z 5 listopada 2026, po korekcie oznaczeń
„Ja/Ty” w tabeli. Repozytorium wspólne:
[HeisenbergC29/autoplay-xcom2](https://github.com/HeisenbergC29/autoplay-xcom2).

Punkt wejścia i inwentaryzacja importu: [issue #1](https://github.com/HeisenbergC29/autoplay-xcom2/issues/1).
Gotowe zadania niezależne: [diagnostyka raportów #2](https://github.com/HeisenbergC29/autoplay-xcom2/issues/2)
i [macierz misji #3](https://github.com/HeisenbergC29/autoplay-xcom2/issues/3).
Osobny dowód kompilacji/gry użytkownika: [próby bieżącej wersji #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).

## Podział odpowiedzialności

| Obszar | Odpowiedzialny |
| --- | --- |
| Kierunek techniczny, priorytety i przegląd integracji | prowadzący asystent — `LEAD` |
| Analiza SDK i mechanik, projektowanie AI, kod i testy automatyczne | `LEAD`, z samodzielną pracą pomocnika `HELPER` |
| Przenoszenie przydatnych rozwiązań z repozytorium pomocnika | `HELPER`, przegląd i scalenie przez `LEAD` |
| Publikowanie scalonych zmian i wydań na GitHub | `LEAD` |
| Kompilacja w Windows WOTC SDK | użytkownik |
| Pełne testy w grze i przekazywanie raportów | użytkownik |
| Sugestie i nowe pomysły | użytkownik opcjonalnie; agenci również mogą proponować rozwiązania |

## Oficjalność punktacji naliczanej przez mod

Użytkownik doprecyzował 13 listopada 2026: jeśli autoplay nalicza punkty
tak samo jak Legacy, wynik uznajemy za oficjalny. Samo źródło obliczenia
nie jest powodem odrzucenia wyniku. Zachowujemy informację, czy wartość
pochodzi z gry czy została obliczona przez mod według zgodnych reguł.
Do pewnego wyniku końcowego potrzebne są także kompletne zdarzenia misji.
Obecny observed_v2 ma konkretne różnice względem konfiguracji Legacy,
więc nie zostaje automatycznie przemianowany na oficjalny.
[Zakres zgodności i stwierdzone różnice](scoring-policy.pl.md), issue #79.

Pomocnik może pracować częściej niż prowadzący. Samodzielnie analizuje,
implementuje i testuje przydatne zmiany. Przegląd prowadzącego jest bramką
integracji, a nie wymogiem pytania o zgodę przed każdą odwracalną czynnością.
Właściciel projektu może zmienić priorytety i te zasady.

## Jedno miejsce integracji

`main` zawiera wspólne źródła. Nie oznacza to potwierdzonej kompilacji ani
wygranej próby najnowszej wersji. [Stan i ostatnia baza](PROJECT-STATE.pl.md)
oddzielają implementację, kontrole automatyczne, Windows i grę.

Jeden temat ma jedno issue, gałąź `helper/<numer>-opis` lub `lead/<numer>-opis`
i pull request. Przed edycją wykonawca podaje w issue rolę, SHA bazy i pliki,
których zamierza dotknąć. Roboczy PR wcześnie pokazuje postęp. Przed końcowym
przeglądem trzeba uwzględnić aktualny `main` i rozwiązać konflikty.

Nie równoleglimy bez uzgodnienia edycji tych samych kontrolerów/planerów.
Jeżeli drugi agent już tam pracuje, wybierz niezależne zadanie lub uzgodnij
konkretny podział w issue. Do trzech aktywnych PR-ów implementacyjnych pomocnika
wystarczy; resztę pomysłów zapisuj jako kolejne zadania.

## Import z osobnego repozytorium

Pierwszy handoff pomocnika zawiera URL repozytorium, gałąź, SHA końca prac,
znaną bazę v15 oraz porównanie z bieżącym `main` i bazą v16. Tabela powinna mieć:

| Rozwiązanie | Źródłowe commity | Stan względem wspólnej bazy | Decyzja i dowód |
| --- | --- | --- | --- |
| opis zachowania | URL/SHA | nowe / już obecne / sprzeczne / zastąpione / niezweryfikowane | przenieść / dostosować / pominąć, z uzasadnieniem |

Przenieś wszystkie rozwiązania ocenione jako przydatne, w osobnych PR-ach
obejmujących spójne tematy. Nie scalaj hurtowo starej gałęzi ani nie nadpisuj
aktualnych plików kopiami z v15. Zachowaj autorstwo i pochodzenie przez
`cherry-pick -x` albo odnośniki do źródłowych commitów. Nowe rozwiązanie może
zastąpić stare, jeżeli PR wyjaśnia korzyść, wpływ na zachowanie i weryfikację.

Szczególnie zachowaj poprawki v16 dotyczące odrzuconych granatów i końca tury,
reguły punktacji v2 od zera oraz kryterium zwycięstwa z wynikiem > 0.
Nie zmieniaj benchmarku, aby wynik wyglądał lepiej. Ryzykowne eksperymenty
mogą pozostać na roboczych gałęziach z opisanym wynikiem.

Pierwszy przegląd importu przyjął ataki Berserkera z PR #7 i ochronę
kontrolowanego sojusznika z PR #9 do rewizji v17. Stary PR #11 z twardym
filtrem pamięci marszu zamknięto bez scalenia; pomysł #10 wymaga przebudowy
na aktualnej bazie.
[Stan i źródła v17](tactics-v17.pl.md). Kolejne prace zaczynaj od aktualnego
`main`; oryginalna baza v16 pozostaje punktem porównania zachowanych zabezpieczeń.

PR #16 dodaje izolowaną poprawkę wizualizacji MP. Integracja v18 i diagnostyka
jej zastosowania są koordynowane przez LEAD w issue #18. Przyczyna awarii
z raportu v17 pozostaje nieustalona; próby użytkownika opisuje
[eksperyment #15](experiment-15-berserker-mp-visualization.pl.md).

PR #22 wprowadza osobny cache tekstu HUD; integracja v19 jest koordynowana
przez LEAD w issue #23. Baza porównania to dokładne v18, z zachowaną
poprawką MP. Zawieszenie z #21 pozostaje nieustalone, a zmiany taktyczne
#20 i poprawki PR #11 są poza tym eksperymentem.
[Próba v18/v19](experiment-17-hud-polling.pl.md).

6 listopada użytkownik potwierdził pełną wiedzę o mapie i pozycjach
aktywnych wrogów poza LOS. V20 z PR #26 wprowadza ten wąski wyjątek od
dawnego ograniczenia do widocznych kontaktów; pozostałe reguły legalności,
AP, RNG, ochrony sojuszników i punktacji pozostają. `EnableFullIntel=true`
jest domyślne; wariant `false` zachowuje normalną wiedzę opartą na widoczności.
Integrację prowadzi LEAD w #27. #20 i badanie pilnego podejścia/leczenia #28
są osobnymi tematami, poza tą zmianą.
[Zakres v20](experiment-25-full-intel.pl.md).

PR #30 / v21 dodaje ograniczony priorytet PlantBomb dla BerserkerMP
w SabotageTransmitter, z poprawkami bezpieczeństwa LEAD. Nie stanowi
deklarowanej naprawy awarii. #32 (ochrona concealment podczas marszu)
jest następnym osobnym tematem; skoordynować go z #31 i zmianami tras,
bez nadpisywania wspólnych plannerów.
[Zakres v21](experiment-29-berserker-blood-killer.pl.md).

PR #35/#36 porządkują analizator i macierz misji bez zmiany runtime.
V22 / #20 dodaje wyłącznie miękką ocenę skupienia pod wspólny obszar AoE.
HELPER kontynuuje #32 z nowej bazy, zachowując ten składnik w formacji;
#29 (legalny obiekt PlantBomb) i #28 (pilne leczenie) pozostają osobne.
[Zakres v22](experiment-20-area-formation.pl.md).

V23 / PR #39 przenosi ocenę concealment do wspólnego assessora z budżetem
pojedynczej decyzji i zachowaniem konstruktywnego legalnego fallbacku.
Nie jest poprawką potwierdzonego zawieszenia v22: obserwacyjny heartbeat
jest osobnym priorytetem #40, a właściwy obiekt PlantBomb nadal bada #29.
[Zakres v23](experiment-32-concealment-route.pl.md).

V24 / PR #44 obejmuje ekspozycję wczesnej trasy, gotowość zwykłego
otwarcia z ukrycia, wagi zdolności wrogów i ograniczone ryzyko wybuchowych
osłon. LEAD zachowuje legalne konstruktywne trasy awaryjne i jeden budżet
inspekcji na decyzję. PR #43 zamknięto bez scalenia: wyjątek ostatniego AP
omijał zabezpieczenia ruchu. PR #45 uzupełnia v24 o rzeczywistą geometrię
granatu przy pustym obrysie; kompilować dopiero końcowy SHA wskazany
w #4. Diagnostyka #40 pozostaje priorytetem niezależnym od tych zmian.
[Zakres v24](experiment-31-safe-opening.pl.md).

V25 łączy obserwacyjny heartbeat #40 / PR #50 i diagnostykę nieudanych
celów oraz przekaźników #46 / PR #47. LEAD poprawił błędy składni UC,
klasyfikację krytyczności, cykl obserwacji i granice skanów; kompilacja
Windows i gra pozostają osobnym dowodem. UI ShowFailed ani sam napis
timera nie oznaczają automatycznie porażki wymaganego celu. Użytkownik
11 XI zatwierdził także odczyt aktualnego celu patrolu. PR #49 dostarcza
ten punkt z ograniczoną walidacją aktywnych wrogów, tylko w pełnym
rozpoznaniu. Usunięto IsEngaged i pozostałe prywatne filtry AI. To dane
do oceny, jeszcze nie gotowa sekwencja zasadzki ani cała przyszła trasa.
Zgoda nie obejmuje AP, cooldownów, RNG i innych ukrytych zamiarów.
#29 pozostaje następną pracą
nad rzeczywistym obiektem i polem interakcji PlantBomb.

LEAD przygotowuje v26 z kontrolowaną obsługą potwierdzonego relaya #46
w PR #51 oraz rzeczywistym polem interakcji #29. Podejście używa native
punktów/footprint i zachowuje rozróżnienie przewidywanej geometrii od
AA_Success po faktycznym ruchu. Sam zużyty interaktor nie oznacza Sweep.
Raport v25 jest już odebrany:
GasStation −21200 finalne, Blood Killer bez zaliczonego X4 i bez native end.
Nie przypisywać czterech kar DeadSoldier czterem fizycznym zgonom.
Zmiany runtime muszą zachować ograniczenia ostatniego AP i ryzyka;
do jednej następnej kompilacji LEAD wskaże wspólny końcowy SHA.
[Wyciąg v25](report-2026-11-12-v25.pl.md).

Pierwsza kompilacja v26 zatrzymała się na walidacji DependsOn planera.
Ten mod-make.log użytkownik przekazał wyłącznie LEAD; poprawkę wykonuje
sam LEAD. PlantGoalResult pozostaje wewnątrz klasy wiedzy, a granica API
używa typów gry i statusu int, jak wcześniejsza poprawka AmbushPreparation.
Rewizja i taktyka v26 pozostają; ponowny Windows build i gra wymagają dowodu.
Nie przyjmować już dla całego v26 statusu „kompilacja NOT RUN”: pierwsza
próba była FAIL. Aktualny SHA poprawki i status ponownej próby są w #4.

## Przekazanie i decyzja o scaleniu

Po raporcie v28 z 12 XI 20:39 UTC HELPER przygotował #56 / PR #61 (v29).
Blood Killer doszła do native end bez crashu w tej próbie, lecz przegrała
po trzecim zgonie i ustawieniu heavy-loss flag przy dwóch żywych Berserkerach.
V29 dodaje wspólny kontakt, ograniczone timerem otwarcie przed X4 i wspólny
cel podczas Sweep. LEAD poprawił bramkę premii ataku poza aktywną fazą
oraz rzeczywisty limit przeglądanych unit states z fallback przy częściowym
centroidzie. Po review/CI LEAD scalił v29 jako
`189aa3d3aba054109f7ca1405770a2c90b0676e9`. Log użytkownika odebrany 13 XI
potwierdza Windows WOTC SDK **PASS: 0 błędów, 9 ostrzeżeń**, pakiet zapisany.
Użytkownik potwierdził, że kompilował wskazaną paczkę; log sam nie zawiera SHA.
Pierwotny zapis dowodu był dokumentacją; późniejsza poprawka #66 usunęła
tylko nieużywaną Distance. Nowy raport v29 potwierdza obie porażki:
GasStation −12900 final, Blood Killer +7100 final. W Blood wszystkie
55 chosen / 109 result są identyczne z v28; opening contact ani razu
nie spełnił obu progów. Dokładny SHA lokalnej kompilacji nie jest zapisany.
[Raport v29](report-2026-11-13-v29.pl.md).

LEAD integruje osobno przejrzane #63 (UIv30), #65 (etap1 strzelców v31)
i #68 (v32: początkowa własność Berserkerów oraz zapis wyników przejęć).
Nie wykluczać udanego MC na podstawie samych zapisanych MISS: rejestrator
mógł pomijać udaną zmianę właściciela. W v32 odczyt początku misji
i kwalifikacja przed/po akcji są poprawione; native targeting/score zachowane.
**Następna kolej użytkownika** po integracji i wskazaniu jednego końcowego
SHA/ZIP w #4: kompilacja v32 i GasStation/Blood Killer. Pierwszy Windows
make v32 był **FAIL: 1 błąd, 8 ostrzeżeń** (brak ')' w Controller:1303).
PR #72 naprawia nawias bez zmiany taktyki i rewizji; dodaje regresję
i skan delimiterów. **Make po poprawce PASS: 0 błędów, 12 ostrzeżeń**,
pakiet zapisany; gra v32 NOT RUN. Po pełnym SDK Steam siedem dawnych
ostrzeżeń zasobów zniknęło, doszło 11 duplikatów klas TLE w DLC_3,
pozostał Day0. Użytkownik potwierdził identyczną kopię przykładowej klasy
w czterech lokalizacjach Src/SrcOrig i DLC_3/TLE. #73 to odrębna odwracalna
naprawa środowiska SDK, bez nowych zmian runtime. Nowe dwa logi użytkownika
potwierdzają sukces bazy i moda po naprawie: każdy **0 błędów / 1 ostrzeżenie**,
duplikaty zniknęły. #73 zamknięto; Day0 z pustego pakietu kompilatora
i aktualna prywatna migawka źródeł SDK są w #75. **Następny test gry może
się odbyć na obecnej v32**; brak raportu gry nadal oznacza NOT RUN.
HELPER nie otrzymał nowych logów, więc LEAD przekazał ich wynik na GitHubie.
[Dowód](build-2026-11-13-v32.pl.md).
**HELPER równolegle:** #56 wykonalne otwarcie i przeżycie
Sweep, potem dalsze #31 OW; nowy claim/branch/PR i następna rewizja,
z zachowaniem tej bazy. V32 nie deklaruje naprawy 21 wczesnych ruchów.
[Dowód kompilacji](build-2026-11-13-v29.pl.md).
HELPER może kontynuować odrębne #31 dla nieukrytej drużyny strzelców na nowej
bazie. Jeden claim zakresu przed edycją wspólnego MissionPlanner; oddzielne
focused PR-y do przeglądu LEAD. Nie wymagamy powtórzenia samej wersji v28
po narzędziowej zmianie analizatora #59 / PR #60.

Native rollup z opróżnionym terminalnym końcem potwierdza finalne +7100;
porównawcze −7900 ma inne komponenty/coverage i nie jest równoważnym
wynikiem oficjalnym. Warunek pełnego parytetu nie jest tu spełniony.
Porażka nadal nie zalicza próby mimo dodatniej natywnej punktacji.
[Wyciąg v28](report-2026-11-12-v28.pl.md).

Analiza v27 z matching EXE i rzeczywistym unwind ustaliła callback crashu:
HUD licznika punktów wywoływał GetTotalScore, które wymusza przebudowę cache
historii. LEAD prowadzi #57 / PR #58 jako v28: odczyt natywnych zdarzeń
punktowych zamiast tego agregatora i guardy trwającej latent submission.
Wynik odroczony może pozostać na ekranie, ale nie jest nową obserwacją.
Zasady punktacji, maksimum/baseline i taktyka pozostają; Windows i ponowna
próba tej samej Blood Killer są osobnym dowodem. Nie wymuszać końca tury,
nie naprawiać ręcznie mapy silnika, nie utożsamiać starego HANG z nowym CRASH.
[Dowód i zakres v28](experiment-57-safe-score-read.pl.md).

Raport v26 z 12 XI 11:24 UTC otrzymał najpierw HELPER; LEAD sprawdził
manifest, identyczność Launch.log i istotne rekordy. Sześć relay oraz X4
działają w tej próbie; końcowego zwycięstwa/score brak, zgłoszony HANG
po potwierdzonym końcu tury pozostaje niewyjaśniony. Nie cofać działającej
obsługi X4/relay ani nie udawać naprawy przez ForceComplete.
PR #55 po poprawkach LEAD stanowi v27: tylko rozszerzenie miękkiej oceny
wybuchowej osłony o melee, z natywną konwersją Mobility i zachowanymi limitami.
Nowy marker odróżnia tę zmianę runtime; Windows/game v27 wymagają dowodu.
[Raport](report-2026-11-12-v26.pl.md),
[zewnętrzny materiał przy kolejnym zatrzymaniu](hang-evidence.pl.md).
Priorytet HELPER #31b nadal obejmuje pojedynczy potwierdzony kontakt,
legalny focus/OW po ujawnieniu i ograniczony fallback. Nie wymuszać
„wszystkie pody przed relay” ani nie przypisywać CurrentTargetLocation
gwarantowanej przyszłej trasy; presję czasu oceniać osobno per misja.

W PR napisz: konkretny problem i zachowanie po zmianie, źródła/commity,
testy rzeczywiście wykonane, pominięcia, ograniczenia oraz scenariusz do gry.
Oznacz gotowość do przeglądu, gdy wynik jest konkretny i odtwarzalny.

Prowadzący zapisuje `LEAD: reviewed <pełny SHA> — merge / changes requested`
w rozmowie PR. Pomocnik nie scala własnej pracy i nie publikuje wydań.
Zmiana SHA wymaga ponownego sprawdzenia zmienionej części przed scaleniem.
Jeżeli oba agenty używają konta `HeisenbergC29`, formalna recenzja własnego PR
nie rozróżnia ich ról: stosujemy podpisy `LEAD:`/`HELPER:` i decyzję z SHA.
Nie udajemy, że są to dwie niezależne tożsamości GitHub.

Reguła pracy przez PR obowiązuje organizacyjnie. Nie należy przedstawiać jej
jako technicznie włączonej ochrony gałęzi bez potwierdzenia ustawień GitHub.

## Status zadania i dowody

W treści issue stosuj jeden aktualny status: `READY`, `ACTIVE`, `REVIEW`,
`BLOCKED`, `WAITING_USER_TEST` lub `DONE`, z rolą wykonawcy i linkiem do PR.
Issue implementacji można zamknąć po scaleniu, ale pozostaw oddzielne otwarte
zadanie prób Windows/gry. `DONE` dla próby gry wymaga raportu.

Zielone CI oznacza przejście kontroli, które faktycznie uruchomiono.
Pominięte testy SDK/configów nie są zaliczone. Scalone źródła, udana kompilacja
i ukończona misja to trzy różne dowody. Oficjalne zwycięstwo z zerowym/ujemnym
wynikiem nie zalicza próby projektu; niepełne punkty pozostawiają ją niepotwierdzoną.

## Praca asynchroniczna

GitHub jest trwałą skrzynką zadań i przeglądów. Każdy agent na początku sesji
czyta aktualne issue, PR-y i ostatnie komentarze. Nikt nie zakłada całodobowego
monitorowania ani automatycznego przenoszenia wiadomości do tej rozmowy.
Przy zakończeniu sesji zostaw krótki handoff: SHA/gałąź, co działa, wyniki,
otwarte ryzyka i następny krok. Gdy prowadzący jest niedostępny, pomocnik może
kontynuować niezależne zadania i przygotowywać kolejne PR-y do przeglądu.

SDK, surowe INI, prywatne logi i zapisy nie trafiają do publicznego repozytorium.
W issue publikuj odpowiedni wyciąg lub podsumowanie z SHA, rewizją rejestratora,
misją, trudnością i punktacją. Dostęp do prywatnych wejść nie jest warunkiem
uruchomienia publicznych testów ani przygotowania inwentaryzacji importu.
