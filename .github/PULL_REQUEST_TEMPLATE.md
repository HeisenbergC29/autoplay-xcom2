Rola wykonawcy: pomocnik GPT-6 / prowadzący

Zadanie: #numer

## Problem i zachowanie po zmianie

Opisz konkretny problem, jego wyzwalacz oraz wynik działania po tej zmianie.
Podaj wpływ na AP, legalność akcji, widoczność, punktację i istniejące mechaniki,
jeżeli zmiana ich dotyczy. Wskaż istotne ograniczenia.

## Pochodzenie i zakres

Dla importu podaj URL repozytorium źródłowego, pełne SHA przenoszonych commitów
i bazę porównania. Wyjaśnij, co przenosisz, co jest już w aktualnym `main`
oraz jakie inne zmiany są niezbędnymi zależnościami.

## Walidacja

Podaj polecenia, liczbę zaliczonych i pominiętych testów oraz sprawdzony commit.
Zmień statusy poniżej zgodnie z faktycznym wynikiem; zielone CI nie oznacza
kompilacji UnrealScript ani sukcesu w grze.

| Sprawdzenie | Wynik i dowód |
| --- | --- |
| Testy publiczne i statyczne | Do uzupełnienia, w tym pominięte testy |
| Kontrakty z prywatnym SDK/configami | NIEURUCHOMIONE — albo wynik i zakres danych |
| Kompilacja Windows WOTC SDK | NIEURUCHOMIONA — albo link do wyniku użytkownika dla tego commitu |
| Próba w grze | NIEURUCHOMIONA — albo raport z rewizją, wynikiem misji i punktacją |

Scenariusz następnej próby: podaj krótkie, odtwarzalne kroki i oczekiwane
zachowanie, jeżeli zmiana wymaga sprawdzenia w grze.

Potwierdź, że diff zawiera wyłącznie potrzebne pliki projektu, bez surowych
źródeł SDK, plików gry, zapisów, prywatnych logów i danych dostępowych.

Przegląd prowadzącego jest zapisywany w rozmowie PR wraz z pełnym SHA
sprawdzonego commitu. Pomocnik nie zatwierdza ani nie scala własnego PR.
