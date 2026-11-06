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
kontrolowanego sojusznika z PR #9 do rewizji v17. PR #11 z twardym filtrem
pamięci marszu wymaga poprawek i pozostaje poza integracją.
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

## Przekazanie i decyzja o scaleniu

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
