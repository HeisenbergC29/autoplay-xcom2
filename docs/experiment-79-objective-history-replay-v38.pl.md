# #79 etap C / v38 — odtwarzanie ukończonych celów po późnym włączeniu HUD

Baza: `main eb1a103689fcba81ebb08ba9a0272889a7847238` / `mission-report-v37`.
Gałąź HELPER: `helper/79-objective-history-replay-v38`. Wersja diagnostyczna:
`mission-report-v38`. Zmiana dotyczy **wyłącznie nieoficjalnego, częściowego
observed_v3** przy misjach bez natywnego providera; nie zmienia zasad/stawek,
starego observed_v2, native Ladder/Challenge, taktyki ani kryterium PASS.

## Problem i dowód z kompletnego SDK

V37 `APX_LegacyObservedV3.OnObjectiveCompleted` liczył ukończone cele tylko
w czasie, gdy działał listener `MissionObjectiveMarkedCompleted`.
Po uruchomieniu F8/HUD dopiero po wykonaniu celu lub odtworzeniu zapisu
event był utracony, mimo że historia taktyczna zawierała wcześniejszy
`XComGameState_ObjectivesList`. Wynik mógł być niepełny nawet dla
prawidłowo znanej stawki.

W stock `XComGame/Classes/SeqAct_DisplayMissionObjective.uc`:
`Activated()` pobiera poprzedni `ObjectiveDisplayInfo`, ustala
`bPreviouslySet = ShowCompleted || ShowFailed`, zapisuje nowy stan do
`XComGameState_ObjectivesList`, a następnie emituje
`MissionObjectiveMarkedCompleted` wyłącznie dla pierwszego ukończenia.
`XComGameState_ObjectivesList.uc` przechowuje całą tablicę
`ObjectiveDisplayInfos`; nie trzeba odtwarzać animacji ani wywoływać
natywnego kalkulatora punktów.

## Wdrożenie

`APX_LegacyObservedV3.ObserveObjectiveHistory` działa podczas istniejącego
przeglądu historii w `ObserveFrame`, najwyżej 256 historii na odczyt.
Przetwarza tylko zmienione w tej historii `XComGameState_ObjectivesList`,
porównuje je z wersją tego samego obiektu na indeksie poprzedniej historii.
Warunki uznania przejścia:
- ten sam typ misji, `ShowCompleted`, `ShowCheckBox` i nie `HideInTactical`;
- poprzedni wiersz wskazany przez publiczny stock `GetObjectiveDisplay`
  **nie był ukończony ani nie był failed** lub nie istniał; ten getter
  zachowuje natywne dopasowanie po MissionType + DisplayLabel albo po
  poprawnym pełnym kluczu, w kolejności wierszy listy;
- nie policzono tego pełnego klucza przez działający listener;
- rzeczywista tura odczytana z `XComGameState_Player` w momencie przejścia;
- 128 jako górna granica liczby list w jednej historii, długości każdej
  listy celów i liczby zarejestrowanych kluczy.

Ukończenie obecne jedynie w samym starcie misji nie jest dowodem nowego
zdarzenia — nie zostaje naliczone. Luka w przeglądanej historii, zbyt duża
lista lub brak tury oznaczają `partial_objective_history_gap`.
Naliczenie rzeczywiście odtworzonego przejścia tworzy marker w Launch.log:
`Legacy objective history replay|profile=...|history=...|recovered=...`.
Odtwarzanie i listener używają wspólnej tablicy kluczy, co chroni przed
podwójnym naliczeniem.

Przegląd LEAD wykrył, że samo porównanie numeric key nie odtwarzało
natywnej tożsamości celu. Ukończony lub failed wiersz z tym samym label,
ale zmienionym GroupID/pool/line mógł zostać błędnie uznany za nowe
ukończenie. Poprawka używa bezpośrednio publicznego, odczytowego
`GetObjectiveDisplay(MissionType, DisplayLabel, out Info,
TextPoolIndex, LineIndex, GroupID)`. Nie wywołuje prywatnego
`GetObjectiveDisplayInfoIndex` i nie kopiuje jego implementacji.
Identyfikator do deduplikacji przyznanej nagrody nadal zawiera pełny klucz.
Niepoprawne indeksy `-1` nie stają się automatycznie poprawnym fallbackiem;
label nadal może wskazać istniejący poprzedni wiersz, jak w stock.

Po późnym starcie pozostaje status `partial_civilian_listener_started_late`,
ponieważ ratowania cywilów nie da się równie bezpiecznie odtworzyć jedynie
z pola bieżącego stanu. Nie wdrożono również uzupełniania unknown origin,
reinforcement, disabled, restart, bonusów, exact decay/native C++ parity,
ani dowodu pełnego coverage. Zero-based/~partial nadal obowiązuje,
`native_parity_proven=false` i `event_coverage_proven=false`.
Na SabotageCC bez override rzeczywista stawka DefaultObjectiveScoring wynosi
0; marker replay może być dowodem wykonania rekonstrukcji, choć suma
punktów nie wzrośnie. **Nie wolno dopisywać sztucznego 5000.**

## Walidacja i ograniczenia

Dostępne testy `tests/test_legacy_objective_history_v38.py` sprawdzają
bounded traversal, poprzedni stan, pełny klucz, deduplikację, niepewność,
brak mutacji i zgodność ze stock UC, jeśli `APX_SDK_SOURCE_ROOT` istnieje.
Regresje LEAD wiążą replay z publicznym getterem i jego argumentami oraz
sprawdzają rzeczywiste klauzule dopasowania z prywatnego SDK na
przypadkach completed/failed ze zmienionym kluczem, indeksów `-1`
i pierwszego dopasowania w kolejności listy. Źródła SDK są wyłącznie
lokalnym wejściem testu, nie są kopiowane do repozytorium.
Testy kontraktu nie wykonują funkcji UnrealScript w silniku gry.

Przyszłe próby do Windows WOTC SDK: dopiero po zakończeniu całej kolejki
[#86](https://github.com/HeisenbergC29/autoplay-xcom2/issues/86), zgodnie
z poleceniem użytkownika z 14 XI. Nie jest to prośba o osobny build v38.

1. Zbudować jedną końcową paczkę zawierającą zmiany v38 i następne etapy
   #86; sprawdzić 0 błędów i marker końcowej rewizji wskazany przez LEAD.
2. W trybie diagnostycznym wykonać cel przed uruchomieniem HUD/F8,
   potem uruchomić autoplay. Sprawdzić, czy wcześniejsza **pierwsza**
   zmiana celu daje dokładnie jeden marker `Legacy objective history replay`,
   bez zakładania pełnej autonomii takiej próby.
3. Powtórzyć z wcześniej aktywnym listenerem — nie oczekiwać drugiego
   naliczenia tego samego celu. Sprawdzić późny load/catch-up 256 historii.
4. Sprawdzić SabotageCC i inne misje na realnych zainstalowanych tabelach:
   stawki i ewentualny brak override, source/provenance, final native outcome.
   Dodatni wynik przy ręcznym wykonaniu celu nadal FAIL benchmarku autoplaya.
5. Porównać `hud_score`, eventy objective i wynik po zakończeniu;
   osobno udokumentować ratunek cywilów i pozostałe luki, nie nadawać
   statusu official na podstawie samego replay.

**Windows SDK make v38: NOT RUN. Gra v38: NOT RUN.**
LEAD przegląda i scala; HELPER nie publikuje release ani nie edytuje main.
