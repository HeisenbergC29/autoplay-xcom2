# HELPER #116 — Blood Killer: kontakt, zegar i ostatni AP

Baza `main d0f827edb5335360e69e32710437c9174038a6ee`. Osobna gałąź `helper/116-bloodkiller-timed-objective-v50`. Źródło: ostatni `Logs/Launch.log` v48 w prywatnym `AutoplayXCom2-20261122-105517-9277c808.zip`; kopii `Launch-backup-...` nie liczyłem jako nowych prób.

## Dowód

W `SabotageTransmitter` / Blood Killer zakończyło się `outcome=loss`; 58 przyjętych komend (42 ruchy, 16 akcji), w tym X4 podczas t8, przy porażce Sweep/Extract. Na końcach t1–t3 pozostało kolejno **3, 1, 5 AP** bez wykorzystania. Po decyzji D8 (`turn=1`) pojawiło się `recent_contacts count=1`; kolejne D9–D10 dotyczyły już t2; D19–D24 t3 z `recent_contacts count=2`. W `APX_Controller.MakeDecision` gałąź pamiętanego kontaktu przejmowała całą selekcję ruchu, pomijając `APX_MissionPlanner.ChooseMove`; `ChooseContactSearchMove` bezwzględnie wymaga min. 2 AP. To jest logiczna, udowodniona luka. Nie jest natomiast dowodem, że każdy brakujący AP można było wykorzystać bezpiecznie.

W D25/26/27/32/33/43 sześć natywnych uderzeń w przekaźnik przedłużało czas po 1 turze, więc **nie wolno** premiować ruchu X4 ponad każdy natywny atak. W t5 czterech przeciwnych kapłanów zastosowało Stasis na czterech berserkerach; ruch w t3 nie może ślepo otwierać kontaktu.

## Implementacja

- `APX_Controller.ShouldCompareTimedObjective` to testowalny bool: tylko `SabotageTransmitter`, natywnie nieukończony X4, BerserkerMP i odczytany timer 1–4. Teraz, zamiast wykluczać propozycję misji przy `recent_contacts`, kontroler dodaje ją jako **konkurującą** z bieżącym wyborem. Standardowy native attack/relay i bezpieczniejszy ruch nadal wygrywa przy wyższej punktacji.
- Przy co najmniej 1 AP na ruch `MissionPlanner.ChooseTimedBerserkerObjective` bierze cel X4 z `FindBerserkerSabotageGoal` i osiągalny natywny odcinek z `ChooseRoutePrefix`. To ten sam kandydat na 1 i 2 AP. W obu przypadkach wymaga postępu co najmniej o jedno pole, wsparcia drużyny i kontroli całej trasy. Dopuszczalny wzrost szacowanej ekspozycji to 8 jednostek modelu. Kontrola ukrycia, zagrożeń i wybuchowych osłon korzysta z budżetów wspólnych dla oddziału. Po użyciu 1 AP log oznacza taką propozycję jako `timed_last_ap_objective`.
- Marker `timed_objective_comparison` zawiera native timer, AP, pamiętany kontakt, powód odrzucenia, wynik kandydata i dotychczas najlepszą ocenę. Inny moduł nadal może wybrać end-turn, legalny relay lub native attack.
- Wersja źródłowa **nie** modyfikuje inicjatywy wrogów, aktywacji podów, kosztu umiejętności, dodatkowych AP ani zegara. Nie przewiduje skuteczności przyszłej reakcji; score to heurystyka ruchu. Zależny LEAD `ScoreHunkerDefense` w `APX_CombatPlanner` nie został dotknięty.

## Testy

`tests/test_berserker_last_ap_v50.py`: pięć scenariuszy bramki czasu/celu, źródłowe kontrole natywnej trasy, bezpieczeństwa i wspólnych budżetów, liczbowa ocena 1 AP, oraz syntetyczny ZIP→CLI dla trzech wariantów decyzji: legalny ruch na 1 AP, odrzucona ryzykowna trasa i legalny natywny atak wygrywający z ruchem. Ten E2E weryfikuje tylko raportowanie i spójność decyzji, **nie symuluje gry**.

## Późniejsza próba WOTC

- Przy tym samym ustawieniu co v48 odnotować t1–t3: liczbę przyjętych akcji, sumę niewykorzystanych AP (punkt odniesienia **3 / 1 / 5**), liczbę `timed_objective_comparison` z `reason=timed_x4_native_one_ap` i rzeczywiście wykonanych ruchów. Dążyć do poprawy, ale **nie uznawać każdego wykorzystania AP za sukces**.
- Zobaczyć, czy nowy ruch nie ujawnił oddziału przed potrzebnym kontaktem; jeśli `reason=unsafe_native_path` i pozostawiono AP, uznać to za prawidłową ostrożność do oceny w kontekście.
- Zliczyć rzeczywiste przedłużenia zegara po uderzeniach w przekaźniki; nie wolno zmniejszyć wyniku 6/6 bez pozytywnego substytutu.
- Potwierdzić samodzielne X4, Sweep, Extract, natywne zakończenie i końcowe punkty. W v48 końcowe +7100 przy porażce nie zalicza misji.
- Pod uwagę brać naturalną losowość i tury Stasis. Porównanie zmian oceny jest dowodem o polityce, nie przyczynowym eksperymentem A/B z identycznym seedem.

**Status:** kod i CI to weryfikacja źródłowa. Kompilacja Windows WOTC i natywne E2E pozostają do wykonania po recenzji i wspólnym buildzie LEAD.
