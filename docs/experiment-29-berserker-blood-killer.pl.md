# Blood Killer (SabotageTransmitter): pierwsza polityka BerserkerMP — v21

**Status:** wariant testowy HELPER z poprawkami integracyjnymi LEAD, nie potwierdzone
ukończenie misji ani usunięcie crasha.

Baza: `dc0ea3a3eecff3b85169128786bb5a51983ce76e` (v20).
Powiązanie: issue #29. Nowy rejestrator: `mission-report-v21`.

## Poprawka kompilacji #33

Próba użytkownika zakończyła się jednym błędem WOTC:
`No need to cast 'StrProperty' to itself` w APX_MissionPlanner.uc:640.
`MissionDefinition.sType` jest już typu string (SDK XGGameData.uc), więc
poprawka usuwa zbędne rzutowanie `string(...)`. Osiem ostrzeżeń logu
dotyczy SDK/DLC. Zachowano rewizję v21 i tę samą taktykę. Poprawiony
wariant wymaga ponownej kompilacji użytkownika; analiza zakończonej błędem
próby nie potwierdza kompilacji pozostałego kodu ani działania w grze.

## Obserwacje z raportu użytkownika

- Wyświetlana nazwa wyzwania: Blood Killer; nazwa silnika
  `SabotageTransmitter`, trudność 2.
- Kontrolowana drużyna pięciu `BerserkerMP` z około 20 HP na początku.
- 46 decyzji, 37 wybranych rozkazów, 35 ruchów,
  2 `DevastatingPunchMP`, **zero wybranych interakcji objective**.
- `Interact_PlantBomb` nie był dostępny jako legalna akcja w
  kontrolowanych punktach: `AA_NoTargets` lub
  `AA_CannotAfford_ActionPoints`.
- `Kismet: X : Used object was not the bomb emplacement` przy
  czasie gry 557.90. Komunikat nie ustala, kto użył obiektu
  ani czy obiekt wskazywany przez UI jest poprawny.
- `[0862.18] Crash Detected` podczas fazy obcych. Użytkownik
  potwierdził brak nowego folderu crasha i dumpa. Sam log nie dowodzi,
  że zapowiadany przez silnik zapis dumpa rzeczywiście powstał, więc
  nie ma podstaw przypisywać awarii tej poprawce, HUD, FOW
  ani konkretnemu atakowi.
- Osobny log z 30 października 2026 **nie jest**
  tożsamy z najnowszym `Logs\\Launch.log` z raportu i
  nie dokumentuje tej awarii.

## Model misji

Tylko gdy `PrioritizeBerserkerSabotage=true`, jednostka ma
szablon `BerserkerMP` i misja to `SabotageTransmitter`
z nieukończonym celem, planer próbuje dojść do celu strategicznego
**przed wyborem punktów prowadzących do wroga**.
Wyszukuje *nieukończone, aktywne obiekty* z
`GetRequiresObjectiveGlint` i wybiera ten najbliższy natywnemu
`MapData.ObjectiveLocation`. Nie pozwala odległemu, obcemu
znacznikowi glint zastąpić właściwego celu (odległość >6 pól).
Gdy nie ma odpowiedniego obiektu, używa wyłącznie mapowego
`ObjectiveLocation`, jeśli jest dostępny. Brak obu oznacza
fallback do dotychczasowej polityki — nie wymyślamy celu.

Podczas podejścia z co najmniej 2 AP normalny A* wskazuje
bezpieczną ścieżkę i natywna cache ruchu buduje jej legalny
odcinek. Nowa ocena nie pozwala, by zwykły ruch w celu
osłony do tyłu o wartości około 20–30 punktów zawsze
wygrywał z postępem zadania. Przy dużym nowym ryzyku
lub krytycznie niskim HP wraca do dawnej logiki.
Oba warianty poszukiwania trasy stosują ten sam limit wzrostu ryzyka;
lokalny fallback nie omija odrzucenia niebezpiecznego podejścia.
Przy ostatnim AP i lokalnych zagrożeniach nadal działają zwykłe kontrole
poprawy pozycji bojowej oraz kosztu utraconego ataku. Bez lokalnej walki
podejście wymaga co najmniej 2 AP, aby pozostał AP na podłożenie bomby.
Brak dodatkowych AP, przestawiania jednostek w historii,
wymuszonych interakcji ani podglądu przyszłego RNG.

Po dojściu do obiektu nadal musi istnieć **natywnie legalny**
`Interact_PlantBomb` lub inna obsługiwana akcja misji.
Kod nie uruchamia jej, jeżeli `AA_NoTargets`, brak AP,
niewłaściwy obiekt lub brak natywnego interaktywnego targetu.
Nadawanie większego priorytetu nie naprawia błędnych
definicji obiektu lub mechaniki wyzwania — wymaga to
osobnego badania SDK i próby.

Definicja gry `DefaultMissionDefs.ini`, sekcja SabotageTransmitter,
potwierdza strategiczny cel `PlantBomb` i osobny cel taktyczny `Sweep`.
SDK `AddPlantBombAbility` / `AddInteractAbility` wymaga co najmniej 1 AP,
choć interakcja go nie zużywa. `X2Condition_Interactive` sprawdza faktyczne
punkty interakcji oraz `InteractionAbilityTemplateName`; glint ani dystans
1,5 pola nie gwarantują spełnienia tych warunków. Obecny wybór obiektu jest
heurystyką podejścia, co należy sprawdzić w grze.

## Kontrole i odbiór

Testy Python sprawdzają policy scope, kontrakty wyboru
obiektu, rzeczywistą funkcję liczbową, native A* i
zachowanie zabezpieczeń; nie zastępują Windows WOTC.
Nowy log ma rozpoznawalną rewizję v21. Dodatkowo
zapisuje `Berserker sabotage route` z unit, celem,
proponowanym końcem i ryzykiem, aby w kolejnej próbie
sprawdzić faktyczny postęp i ewentualne cofnięcia.

Po przeglądzie LEAD i kompilacji użytkownika:
1. Powtórzyć dokładne wyzwanie Blood Killer z tym samym zapisem.
2. Potwierdzić, że `SabotageTransmitter` oraz
   `BerserkerMP` uruchamiają politykę i w logu widać
   marker podejścia do urządzenia (zamiast tylko ruchów do wrogów).
3. Sprawdzić malejący dystans/realną drogę A*, liczbę
   `Interact_PlantBomb` jako `AA_Success`, czy bomba
   została rzeczywiście założona, czy silnik zaliczył objective.
4. Sprawdzić również brak zacięcia na urządzeniu,
   bezpieczne ścieżki, legalne ataki, końce tur, moment
   wykonania sabotażu i rzeczywisty wynik > 0 wraz z victory.
5. Awarię oceniać osobno. Dla tej próby nie ma nowego folderu/dumpa;
   nie ponawiać prośby o nieistniejący plik. Jeżeli kolejna awaria pozostawi
   raport Windows lub dump, zachować go prywatnie do niezależnej diagnozy.

## Wycofanie

`[AutoplayXCom2.APX_MissionPlanner]`
`PrioritizeBerserkerSabotage=false` przywraca poprzednią
politykę dla tej jednostki i misji. Porównanie A/B tylko
na jednej zmianie, z tą samą konfiguracją FOW/intel.
