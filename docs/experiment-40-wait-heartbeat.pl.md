# Eksperyment #40 — heartbeat długich oczekiwań taktycznych

Baza źródeł: `main` v24, `defdcee43945a0755de6d069d7690cd215c83c63`.
Gałąź HELPER: `helper/40-observational-wait-heartbeat`.
Wariant integracji LEAD: `mission-report-v25`. Kompilacja Windows WOTC SDK
i rozgrywka tego wariantu: **NOT RUN**.
NIE jest to naprawa wcześniejszego zawieszenia Blood Killer.

## Problem z raportu v22

W `SabotageTransmitter` / Blood Killer (v22) użytkownik stwierdził
zawieszenie w fazie obcych. Rejestrator zakończył na oczekiwaniu HUD/
wizualizatora, bez natywnego końca misji i bez pliku crash dump.
Własny kontroler deduplikuje `SetWaitStatus`, dlatego z samej ostatniej
linii nie można rozpoznać, czy gra stoi, czy jej historia nadal postępuje.

W osobnym teście v24 z 11 listopada 2026 Blood Killer została przerwana
ręcznie po D34, a timer później wygasł. **Nie reprodukuje to zawieszenia
v22**; outcome i końcowa punktacja v24 są nieznane. Dla kompletności
bieżącego raportu: SabotageCC native win, ~+6800 HUD tylko częściowe;
GasStation native loss, −10700 końcowe. Szczegóły #4.

## Zakres zmiany

W `APX_Controller` podczas aktywnego autoplaya zbieramy wyłącznie
obserwacje po **15 s** utrzymującego się powodu czekania, następnie co
**30 s**. INI pozwala zmienić okresy, ale kod ogranicza je odpowiednio
do 10–120 s i 15–180 s; pojedyncza długa klatka nie emituje serii
zaległych wpisów. Dla każdego zdarzenia `marker|kind=wait_heartbeat`
oraz nielimitowanego licznikiem rejestratora wpisu kategorii
`AutoplayXCom2` zapisujemy:

- `age_s`, `reason`, `enabled`;
- `history`, `history_delta` od poprzedniej obserwacji,
  `start_history`;
- natywne `visualized_history` i `visualizer_frame`;
- `hud_visible`, `rules_state`, `team`,
  `waiting_states`, `waiting_visualizer`.

Pierwszy okres zaczyna się przy nowym rodzaju czekania, nie przy każdym
odświeżeniu szczegółów. Reset następuje po odzyskaniu sterowania,
wyłączeniu/włączeniu autoplaya, przejściu do nowej historii/nowej misji,
cofnięciu indeksu albo zmianie powodu czekania. Gdy gra jest ręcznie
spauzowana, czas nie jest naliczany; przy OFF nie ma emisji.

Odczyty wizualizatora odbywają się tylko po osiągnięciu progu; zwykła
klatka gry nie skanuje historii ani jednostek. SDK udostępnia
`XComGameStateVisualizationMgr.GetCurrenHistoryFrame()` (pisownia
`Curren` zgodna ze stock) i publiczne `LastStateHistoryVisualized`.
Kod wyłącznie czyta te pola i istniejące bramki tury. Nie wykonuje
`ForceComplete`, `DebugClearHangs`, `SetCurrentHistoryFrame`,
`SubmitGameState` ani żadnych akcji/rozkazów.

**Uwaga diagnostyczna:** heartbeat to dowód, że timer kontrolera
wykonuje się nadal; brak kolejnych heartbeatów sam w sobie nie dowodzi
konkretnej przyczyny — możliwe są również restart misji, OFF, pauza,
zamknięcie gry lub zatrzymanie wątku silnika. Zmiana historii przy
stojącym wskaźniku wizualizatora jest wskazówką, nie kompletnym
stack trace. `details` rejestratora sanitizuje znaki potoku,
więc do analizy nadaje się też wpis `Wait heartbeat|` w `Launch.log`.

## Testy i odbiór

Nowy `tests/test_wait_heartbeat.py` sprawdza wykonując prawdziwe
ciała prostych helperów UnrealScript: progi 15/30, brak serii nadmiarowych
wpisów, reset, kolejność wobec pauzy, końca tury, hackowania i bramek
HUD, brak mutacji oraz API stock WOTC SDK przy ustawionym
`APX_SDK_SOURCE_ROOT`. To **testy struktury i czystych funkcji**,
nie kompilacja UnrealScript ani test w grze.

Scenariusz odbioru dla LEAD/użytkownika: po decyzji o integracji i
ustaleniu końcowego markera rewizji, kompilacja Windows WOTC SDK,
uruchomienie Blood Killer, zachowanie wcześniejszych zabezpieczeń.
Podczas długiego oczekiwania >15 s w aktywnym autoplay szukać
`wait_heartbeat`; zestawiać `history_delta`, opóźnienie wizualizacji,
stan HUD i team. Nie ogłaszać naprawy hangs bez rzeczywistego porównania
A/B na tej samej misji. Zawartość prywatnych logów/SDK nie trafia
do repozytorium.

## Integracja

Pierwotna gałąź HELPER nie zmieniała `APX_MissionRecorder.uc`,
ponieważ PR #47 i #49 edytują go równolegle. Przy integracji LEAD ustalił
wspólny marker `mission-report-v25` w rejestratorze, HUD i podsumowaniu
wizualizacji MP oraz dopasował testy rewizji. Kod diagnostyki heartbeat
pozostaje bez zmian. PR #47 będzie następnie scalony z tego samego wariantu;
PR #49 następnie uzupełnia ten sam wariant o aktualny zapisany punkt
grupy, po potwierdzonej decyzji użytkownika z 11 XI. Nie zmienia mechaniki
heartbeat ani nie dodaje gotowego planu zasadzki.

Dokładny końcowy SHA do budowania wskazuje LEAD w issue #4.
Kompilacja Windows WOTC SDK oraz gra v25 pozostają **NOT RUN**.
