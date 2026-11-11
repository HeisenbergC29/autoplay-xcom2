# Eksperyment #46 — obserwacja nieudanych celów i diagnostyka przekaźników

Pierwotna baza: v24 `defdcee43945a0755de6d069d7690cd215c83c63`.
Wariant integracji: `mission-report-v25`, razem z obserwacyjnym heartbeat
z PR #50. Kompilacja Windows WOTC SDK i gra v25: **NOT RUN**.
Dokładny końcowy SHA do kompilacji wskazuje LEAD w issue #4.

## Co jest dowodem krytycznej porażki

Natywne zwycięstwo i znany końcowy wynik >0 pozostają kryterium projektu.
Pewna porażka wymaganego celu uniemożliwia zaliczenie, także przy dodatnich
punktach albo brakującym końcowym rekordzie. Sam czerwony checkbox nie
identyfikuje jednak, czy cel był wymagany.

Po poprawkach LEAD recorder rozdziela dwa zdarzenia:

- `MissionObjectiveMarkedFailed`: zgodny z bieżącą misją, widoczny
  `ShowFailed` + `ShowCheckBox` zapisuje `objective_failed` z
  `critical=false|criticality=unknown`. UI nie dostarcza flagi
  wymagany/poboczny, więc tej obserwacji nie klasyfikujemy automatycznie
  jako krytycznej. Nie oznacza to udowodnionej opcjonalności celu.
- `ChallengeObjectiveFailed`: stockowy handler wywołuje `FailBattle`.
  Ten sygnał zapisujemy z `critical=true`. Obserwator działa natychmiast,
  z priorytetem 1000, ponieważ natywny handler przerywa późniejszych
  słuchaczy; zawsze zwraca `ELR_NoInterrupt` i nie wymaga niepustego
  GameState. Faktyczne dostarczenie eventu musi potwierdzić próba gry.

Obserwatorzy są związani z oryginalną historią, początkiem misji i battle
ID; nie przejmują zdarzeń po zmianie świata lub zaobserwowanym cofnięciu
historii. Deduplikują identyfikatory i wyrejestrowują się po zakończeniu.
Nie zmieniają Kismet, AP, timera, punktów ani natywnego wyniku.
Rejestracja zaczyna się przy F8: brak wcześniejszego eventu nie dowodzi,
że cel nie zawiódł.

Analizator rozdziela wszystkie zaobserwowane failed IDs i zweryfikowane
critical IDs. Wyłącznie jawne `critical=true` wymusza FAIL; pola brakujące,
nieznane lub false pozostają ostrzeżeniem. Sprzeczne rekordy nadal
uniemożliwiają pewny werdykt. Punkty i natywny wynik zachowują osobne pola
oraz oznaczenia pewności. Nie tworzymy końcowych punktów z częściowego HUD.

## Diagnostyka przekaźników czasu SabotageTransmitter

Oficjalny podręcznik opisuje przekaźniki przedłużające czas na X4.
Samo 2 HP albo flaga głównego celu nie identyfikują takiego urządzenia.
`RecordSabotageRelayCandidates` raz na turę zapisuje ograniczony wyciąg:

- do 256 przejrzanych destrukcyjnych stanów, najwyżej 20 opisanych;
- do 256 przejrzanych stanów jednostek i 8 kwalifikujących się własnych;
- do 128 akcji i 192 referencji celów z rzeczywistego cache silnika.

Usunięte obiekty/jednostki są pomijane. Dla zgodnego wizualizera
rejestrowane są klasa i rzeczywisty `ObjectArchetype`, a przy braku
wiarygodnego wizualizera dane pozostają unknown. Instancja aktora sama
nie zastępuje archetypu. `relay_action_target` zapisuje kod dostępności
oraz `native_available`; obecność w cache nie jest sama w sobie dowodem
`AA_Success`.

Wszystkie obiekty są `unverified_destructible`. Ten wariant **nie wybiera
przekaźników do ataku**, nie dodaje zdolności i nie zapewnia dodatkowych
tur. Następna implementacja wymaga identyfikacji archetypu, rzeczywistych
natywnych warunków ataku dla BerserkerMP i korzyści timera. Również
właściwe pole interakcji PlantBomb pozostaje zadaniem #29.

## Raport v24 i próba odbioru

[Wyciąg raportu v24](report-2026-11-11-v24.pl.md): SabotageCC wygrało,
lecz HUD +6800 i rekonstrukcja +11800 są częściowe. GasStation przegrało
z końcowymi natywnymi −10700. Blood Killer ma ręczny OFF przy D34, brak
PlantBomb i końcowego wyniku; `Mission timer expired` następuje 18,28 s
po OFF. Bez powiązania z krytycznym celem sam ten tekst nie potwierdza
fatalnego eventu ani natywnej porażki. Wcześniejszy wniosek HELPER-a
CRITICAL FAIL był zbyt mocny względem dostępnego dowodu.

Po kompilacji końcowego SHA zebrać rzeczywiste archetypy i kody akcji,
sprawdzić dostarczenie failed eventów, natywny wynik, końcowe punkty
z pewnością źródła i wykonanie celów. Nowa telemetria nie jest naprawą
PlantBomb, przekaźników ani zawieszenia. Testy Python i audyt SDK nie
zastępują kompilacji UnrealScript i próby gry. Surowe SDK/logi są prywatne.
