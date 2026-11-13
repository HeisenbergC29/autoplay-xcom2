# #56 — Blood Killer: wspólny kontakt BerserkerMP i ochrona native X4 (v29)

## Powód i dowód

Baza `main` `2d8d255986bd277e8cd706ff3753eb5ed4b8ae42` (v28 runtime,
po PR #60 zmienił się tylko analizator). Prywatny raport v28 12 XI 2026:
`SabotageTransmitter`, trudność 2, sesja `2026-11-12_21-20-43-148_2`,
native LOSS, lecz **+7100 oficjalnych końcowych punktów** potwierdzonych
natywnym rollupem i końcowym zapisem. X4 i cele przekaźników skończone
w turze 8. W turach 1–3: 21 ruchów, 0 wybranych ataków. Po X4:
3 ciosy, 5 ruchów; duże rozdzielenie oddziału (jednostki 24/26
około 33 pola). Po trzeciej fizycznej śmierci Kismet uruchomił flagę
heavy loss, kończąc misję porażką mimo dwóch żywych Berserkerów.
Nie wpisujemy na sztywno limitu trzech zgonów do innych misji.
[Zweryfikowany raport v28](report-2026-11-12-v28.pl.md).

## Zmiana ograniczona do SabotageTransmitter/BerserkerMP

- Nowy `APX_BerserkerFocus` wybiera tylko z prawdziwych
  `XComGameState_AIGroup.m_arrMembers`, aktualnych aktywnych wrogów
  i aktualnych pól świata. Centroid pięciu (lub mniej) żywych Berserkerów
  jest wspólny: wszyscy otrzymują **jeden kontakt**, nie osobno najbliższy
  cel. Poprzedni ID grupy ma miękką przewagę 12, ale bliższa nowa grupa
  może go zastąpić. Po zniszczeniu grupy następuje ponowny wybór.
- Jeden bounded odczyt na decyzję: max 24 AIGroup, 128 referencji
  członków, 12 własnych Berserkerów i 128 sprawdzonych stanów jednostek
  łącznie z odrzuconymi wrogami/cywilami/martwymi. Przekroczenie limitu
  skanu drużyny wyłącza nowy fokus w tej decyzji, zamiast używać częściowego
  centroidu. Tylko `EnableFullIntel=true`;
  nie odczytujemy `IsEngaged`, prywatnego AP/amunicji/cooldownów,
  RNG/AI future intent ani nie traktujemy `CurrentTargetLocation` jako
  pełnej trasy patroli. Przy FullIntel=false obowiązuje stary planer.
- Kontroler zapamiętuje tylko grupę w granicach tej samej historii,
  początku misji, BattleData i gracza. Reset przy rewind, zmianie
  misji/historii, ręcznym OFF albo braku aktywnych wrogów w grupach.
  Co decyzję zapisuje `berserker_focus`: fazę, group, target, members,
  living, dystans i *native* `UITimer.TimerValue`. W żadnej iteracji
  nie modyfikuje XComGameState.
- Przed X4 dopuszczamy krótki kontakt ofensywny **tylko w 1. i 2. turze**,
  gdy rzeczywisty widoczny aktywny licznik ma **co najmniej 4 tury**,
  wybrany pod jest w odległości do 18 pól od środka oddziału,
  żyje co najmniej trzech własnych Berserkerów i `Enable...=true`.
  Nieznany, zawieszony lub krytyczny timer → dotychczasowa droga do X4/relay,
  nie wymyślony slack. To ogranicza ryzyko, że walka zużyje termin.
- W fazie kontaktu wspólny cel staje się bojowym destination przez
  *dotychczasowe* `FindGoal/ChooseMove` z rodzimym A*, ryzykiem,
  wsparciem i zabezpieczeniem ostatniego AP. Dopiero natywny
  `AA_Success` i bezpieczna ścieżka melee dopuszczają cios. Żywy
  żołnierz z HP poniżej 55% nie dostaje **żadnej** premii za pogoń
  w melee; wysoka zdolność dobicia ma miękką premię tylko dla aktualnego
  celu. Realny przekaźnik może zostać legalnie uderzony okazjonalnie;
  jego score podczas wczesnego kontaktu jest ograniczony do 26
  (poza tą fazą dotychczasowa wartość i priorytety bez zmian).
- Poza aktywnym wczesnym kontaktem i natywnym Sweep kontroler przekazuje
  do oceny ataków ID celu 0. Zapamiętana grupa i diagnostyka nie nadają
  premii Sweep podczas powrotu do pilnego celu X4/relay.
- Po **natywnym** `PlantBomb.bCompleted` (a nie po glincie) włączamy
  wspólny kontakt na całym etapie Sweep, niezależnie od zakończonego
  timera. Nadal obowiązują HP/risk, native melee targeting i replan
  po śmierci/zmianie grupy. Ewakuacja, rescue, path/hazards, AP
  pozostają osobnymi istniejącymi bramkami. **Nie ma nowego
  automatycznego warunku zwycięstwa ani kary/bonusu punktowego**.

## Zakres testów i ograniczenia

Nowe `tests/test_berserker_focus.py`: prawdziwe helpery numeryczne UC
uruchamiane przez `uc_math` (timer/turn/odległość, limit 2 tur,
przełączenie Sweep, sticky group i przełączenie przy bliższym kontakcie,
niski HP blokujący premię, legalny relay) oraz source contracts.
Regresje LEAD sprawdzają również bramkę fazy na rzeczywistym wywołaniu
CombatPlanner oraz zliczanie odrzuconych wpisów i odrzucenie częściowego
centroidu przed oceną grup.
`tests/test_safe_contact_opening.py` zachowuje kontrolę wspólnego
budżetu wybuchowych osłon przy rozszerzonej *opcjonalnej* sygnaturze
`ChooseMove`. Kontrole LEAD: **710 testów PASS bez pominięć** z prywatnym
SDK/configami, w tym 13 testów fokusu, oraz audyt **23 klas / 31 nazw PASS**.
Zmiany integracji obejmują kontroler, planery ruchu/ataku, konfigurację
i znaczniki rewizji v29. Provider punktacji i zabezpieczenia HUD v28
pozostają bez zmian.

Bez samodzielnej kompilacji Windows WOTC SDK i bez wykonania gry. Zielone
CI z pominiętymi prywatnymi SDK checks nie dowodzi legalności kompilatora
UnrealScript ani wygranej. Na realnej misji porównać A/B: pierwsza legalna
oferta i **wybrany** atak na pod, ruchy bez ciosu w turn1–3, licznik
przed/po relay, X4 w czasie, rzeczywistą aktywację Sweep, liczebność
odziału, flagę heavy-loss, natywne zwycięstwo i **znane końcowe punkty >0**.
Nie zakładać, że sam wspólny cel gwarantuje przeżycie albo trafienie.

## Celowo poza tym PR

`#31` revealed-ranged pod focus i OW dla GasStation oraz stała widoczność
panelu moda to osobne zadania (bez konfliktu z planowaniem Berserkerów).
`#57` bezpieczny odczyt natywnej punktacji v28 pozostaje **nietknięty**.
Surowe logi, archiwa, SDK/EXE/dumpy i pliki konta nie trafiają do repozytorium.
