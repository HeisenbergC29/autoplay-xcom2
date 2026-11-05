# Stan przekazania projektu — 5 listopada 2026

To punkt startowy dla pomocnika. Bieżące issue i PR-y mogą zawierać nowsze
ustalenia; po integracji aktualizuj ten dokument, gdy zmienia się baza lub
poziom potwierdzenia działania.

## Baza kodu

- Ostatnia opublikowana rewizja działającego kodu: `mission-report-v16`.
- Bazowy commit v16: `9458b185e6602a07d448010c45bc5aeb74fd8d80`.
- Opublikowany kod v15 do porównania:
  `9832d72d14b75adb110a1d5ac74a32e290306b0e`. Dokładną bazę swojego
  repozytorium pomocnik podaje w inwentaryzacji; nie zakładamy jej bez SHA.
- Przed integracją organizacji `main` pozostawał na `ed74176`; aktualna baza
  trafia do `main` przez PR zachowujący historię. Historyczna gałąź
  `codex/legacy-v6-threat-estimates` nie jest osobnym projektem ani nową bazą
  dla kolejnych zmian. Po opublikowaniu organizacji zaczynaj od `main`.
- Przygotowanie współpracy i CI nie zmienia mechaniki gry ani rewizji v16.

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

## Potwierdzenie i ograniczenia

| Dowód | Stan bazy v16 |
| --- | --- |
| Testy Python z prywatnym SDK i configami | 505 zaliczonych, bez pominięć |
| Audyt referencji | 17 klas moda, 29 skonfigurowanych nazw zdolności |
| Pomocnicy budowania i zbierania raportów | kontrole PowerShell zaliczone |
| Publiczny zestaw bez prywatnych wejść | 450 zaliczonych, 55 pominiętych; liczby dla tej bazy |
| Kompilacja v16 w Windows WOTC SDK | niepotwierdzona |
| Pełna próba v16 w grze | niepotwierdzona |

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

Pierwszy krok pomocnika: [inwentaryzacja i procedura importu](TEAM.pl.md#import-z-osobnego-repozytorium).
