# Stan przekazania projektu — 5 listopada 2026

To punkt startowy po pierwszym przeglądzie importu pomocnika. Bieżące issue i PR-y mogą zawierać nowsze
ustalenia; po integracji aktualizuj ten dokument, gdy zmienia się baza lub
poziom potwierdzenia działania.

## Baza kodu

- Bieżąca rewizja źródeł: `mission-report-v18`, izolowana poprawka
  wizualizacji MP z PR #16 oraz diagnostyka jej zastosowania.
  [Integracja PR #19](https://github.com/HeisenbergC29/autoplay-xcom2/pull/19).
- Baza porównawcza v17: `ba4550a8495c5c7d504eca681a6465b2c433ae37`.
  PR #16 scalono jako `42b36d4`; kolejne gałęzie zaczynaj od aktualnego
  `main`, uwzględniając integrację v18 z issue #18.
- Zachowany bazowy commit v16: `9458b185e6602a07d448010c45bc5aeb74fd8d80`.
- Opublikowany kod v15 do porównania:
  `9832d72d14b75adb110a1d5ac74a32e290306b0e`. Dokładną bazę swojego
  repozytorium pomocnik podaje w inwentaryzacji; nie zakładamy jej bez SHA.
- Przed integracją organizacji `main` pozostawał na `ed74176`; historię
  opublikowanych prac scalono przez PR #5 (`dfd9b27`). Historyczna gałąź
  `codex/legacy-v6-threat-estimates` nie jest osobnym projektem ani nową bazą
  dla kolejnych zmian. Po opublikowaniu organizacji zaczynaj od `main`.
- Przygotowanie współpracy i CI nie zmieniło rewizji v16; v17 identyfikuje
  późniejszą integrację zachowań z PR #7 i #9.

## Co już istnieje

Kontroler legalnych akcji, cele/interakcje i ewakuacja, eksploracja, zasadzka,
podglądy granatów z ochroną sojuszników/celów, ratowanie wykrwawiających się,
zbieranie łupu, HUD punktów i rejestrator misji. Nie wszystkie misje lub
zdolności są obsłużone do końca.

V13–v15 wprowadziły wiedzę o widocznych szablonach/broni, rozpoznane melee,
kontrolę kontry, status Marked, chmury trucizny, ograniczoną prognozę ruchu
przed strzałem oraz Aid Protocol/medyczną czynność przed zachowanym atakiem.
Prognozy pozostają heurystyką, a kontroler ponownie sprawdza stan po akcji.

V16 zachowuje kontrolę granatu przed aktywacją, lecz odrzucony podgląd
powoduje ograniczone ponowne planowanie zamiast globalnego OFF. Koniec tury
potwierdza historią/zmianą gracza, ponieważ stockowe API może zwracać false
także po wysłaniu żądania. Tych poprawek nie należy utracić przy imporcie.
[Szczegóły v16](tactics-v16.pl.md).

V17 dodaje do planera `DevastatingPunch` i `DevastatingPunchMP` Berserkera
sterowanego przez gracza, używając istniejących natywnych kontroli melee.
Chroni również odzyskiwalnego własnego żołnierza z rozpoznanym aktywnym
efektem kontroli umysłu przed atakiem i granatem. Poprawki v16 pozostają.
[Zakres, źródła i próby v17](tactics-v17.pl.md).

V18 dodaje tylko flagi ukrywania nieudanego wyniku wizualizacji obrażeń
w rozpoznanym szablonie `DevastatingPunchMP` oraz startupowe podsumowanie.
Nie zmienia rozgrywki, taktyki, HUD ani punktacji. Przyczyna późniejszej
awarii pozostaje niepotwierdzona.
[Zakres i próba A/B v18](experiment-15-berserker-mp-visualization.pl.md).

## Pierwszy przegląd importu

Źródło pomocnika:
[xcom2-autoplay-alternative](https://github.com/HeisenbergC29/xcom2-autoplay-alternative),
`main` na `c63d8d917be368dbee76b66ce3b7911b866f0f5e`.
Historie Git są niezależne; importowany stan początkowy odpowiadał zawartości
v15, co nie oznacza wspólnego przodka commitów.

| Temat | Decyzja prowadzącego |
| --- | --- |
| Ataki Berserkera, PR #7 | scalone; sprawdzony HEAD `5d485ad09616c224a7c7f1a2663c6dd576982bc6` |
| Ochrona kontrolowanego sojusznika, PR #9 | scalone; sprawdzony HEAD `89ebd569d546e3a695927aecab372a4aaa84b31d` |
| Pamięć marszu między turami, PR #11 | wymaga poprawek; nie wchodzi do v17 |
| Ukryta zasadzka, issue #12 | osobny temat do dalszej pracy |

## Potwierdzenie i ograniczenia

V18: **518 testów Python z prywatnym SDK/configami zaliczonych, bez
pominięć**; audyt **17 klas / 31 nazw zdolności PASS**. Końcowe publiczne
CI integracji jest śledzone w PR #19. Kompilacja Windows WOTC SDK i próba
v18 w grze: **NIEURUCHOMIONE**. Samo scalenie nie potwierdza naprawy awarii.

| Dowód | Historyczna baza v17 |
| --- | --- |
| Testy Python z prywatnym SDK i configami | 513 zaliczonych, bez pominięć |
| Audyt referencji | 17 klas moda, 31 skonfigurowanych nazw zdolności |
| Pomocnicy budowania, zbierania SDK i raportów | trzy zestawy PowerShell zaliczone lokalnie w PowerShell 7.6.9 |
| Publiczny zestaw bez prywatnych wejść | 455 zaliczonych, 58 pominiętych; [CI kodu v17](https://github.com/HeisenbergC29/autoplay-xcom2/actions/runs/42021235262) |
| Pomocnicy PowerShell na Windows | trzy zestawy zaliczone w tym samym CI; to nie kompilacja WOTC |
| Kompilacja v17 w Windows WOTC SDK | brak logu kompilacji i dokładnego SHA |
| Próby z rewizją v17 w grze | dwie porażki i awaria, bez odbioru wersji |

Nowy raport v17 opisano w [issue #15](https://github.com/HeisenbergC29/autoplay-xcom2/issues/15).
Rewizja logu potwierdza uruchomienie moda, ale nie dokładny commit
zbudowanych źródeł. Potwierdzone końce tury i przyjęte ciosy są dowodem
tych obserwacji, nie skuteczności całej misji ani usunięcia awarii.

Liczby historycznej bazy v16: 505 testów z prywatnymi wejściami bez pominięć,
17 klas i 29 nazw zdolności; publicznie 450 zaliczonych i 55 pominiętych.
Scalenie źródeł i zielone kontrole nie są potwierdzeniem kompilacji moda
ani zaliczenia misji. [Osobna próba użytkownika #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).

Ostatni [raport v15](report-2026-11-04-v15-stops.pl.md): SabotageCC,
trudność 3, porażka w turze 18, częściowa ocena −17500. Trzy zatrzymania
dotyczyły tego samego podglądu granatu; przyczyna konkretnej niezgodności
nie była rejestrowana wystarczająco dokładnie. V16 dodaje diagnostykę.
Jeden ruch v15 dał przewidziane 47→68%, potwierdzone kolejnym odczytem gry.
Ta próba nie weryfikowała chmur trucizny ani kombinacji medycznej/Aid Protocol.

Historycznie v8 wygrało pierwszą misję Legacy na Dowódcy i jedną próbę
SabotageCC. To pozostaje oficjalnym wynikiem dawnych prób, ale nie potwierdza
nowego kryterium ani wygranej całej drabinki czy wszystkich misji.

## Dane i punktacja

Aktualny katalog zawiera 253 rejestracje szablonów, w tym cywilów, aliasy
i żołnierzy — nie 253 wrogów. Konfiguracja uzupełnia 196 sekcji statystyk,
177 zestawów wyposażenia i 684 odwołania parametrów broni. Dwa symbole
obrażeń proxy Feral MEC M2/M3 pozostają nierozwiązane; nie znaleziono ich
wartości, nie kopiujemy danych M1 i nie żądamy z tego powodu kolejnych archiwów.
[Źródła katalogu DLC](dlc-config-knowledge.pl.md).

Próba jest zaliczona tylko przy zwycięstwie i pewnych punktach misji > 0.
Wynik natywny i porównawczy pozostają rozdzielone; porównanie v2 startuje od
zera i jest oznaczane jako częściowe, gdy brakuje obserwacji. Nie zmieniaj
tych zasad przy przenoszeniu taktyki z osobnego repozytorium.

Inwentaryzację i dalsze przekazania zapisujemy w
[issue #1](https://github.com/HeisenbergC29/autoplay-xcom2/issues/1), zgodnie z
[procedurą importu](TEAM.pl.md#import-z-osobnego-repozytorium).
