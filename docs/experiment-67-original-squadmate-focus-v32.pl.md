# #67 — nie wybieraj pierwotnie własnych BerserkerMP jako wrogiego kontaktu fokusu

## Potwierdzony problem v29 (13 XI 2026)

Źródło: prywatne archiwum logów użytkownika v29, `Launch.log`
(`mission-report-v29`), obejmujące `SabotageTransmitter` / Blood Killer /
diff2, sesję `2026-11-13_11-57-35-409_2`.

Wynik gry: native **LOSS t14**, **+7100 oficjalnych końcowych** z
`CMPT_TotalScore` (history3924) i terminalnym `end` (history3927),
X4 i relay completion w t8, 3 zgony do t14.
W archiwum leży również log bazowy v28 (`2026-11-12_21-20-43-148_2`):
porównanie **55 `chosen` i 109 `result`** po wszystkich polach
z pominięciem zmiennych sesji/seq/decision jest identyczne. Nowa taktyka
v29 nie zmieniła w tej próbie działań: 21 ruchów/0 attacks w t1–3,
13 punches i 41 moves łącznie; **brak `phase=contact`**:
pierwsza grupa22.98 kafli przy timerze4 nie przeszła warunku <=18,
po przejściu dystansu timer spadł do3.

Dodatkowa luka: marker fokusu `target=24` w D49 i `target=23`
w D54 odnosi się do identyfikatorów **pierwotnie własnych**
`BerserkerMP` w stanie początkowym; później były widoczne
w `scope=visible_enemy`. W t13 pierwotny unit26 wykonał wrogie
`DevastatingPunchMP` na pierwotnym unit25. Zarejestrowane
`PriestPsiMindControl` skierowane w24 są MISS — nie ma dowodu,
że te przejścia na stronę przeciwnika są normalnym
`X2Effect_MindControl`. Nie opierać bezpieczeństwa wyłącznie
na `IsReclaimableControlledSquadmate`, który chroni konkretny,
odwracalny aktywny efekt. Szczegóły [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4#issuecomment-6851447903).

## Zmiana źródeł v32

Tylko `APX_BerserkerFocus.uc`: dla aktualnie wrogiej
jednostki `BerserkerMP` rozważanej jako członek `AIGroup`
sprawdzamy read-only
`XCOMHISTORY.GetOriginalGameStateRevision(UnitState.ObjectID)`.
Jeżeli pierwotny stan jest XCOM i należy do tego samego
`PlayerID`, **nie nadajemy bonusowego wspólnego celu** na tej
jednostce. Jeżeli oryginału nie można bezpiecznie odczytać,
również pomijamy wyłącznie bonus/goal dla niezweryfikowanego
BerserkerMP — fail closed, nigdy nie zmieniamy natywnej
listy akcji ani legalności przeciwnika.

Własny squad i tak zawsze oceniamy osobno z aktualnego
`XComGameState_Unit`. Pierwotnie wrodzy BerserkerMP pozostają
dozwolonymi kandydatami, jeżeli oryginalny stan pozwala potwierdzić,
że nie należeli do gracza. Dla innych szablonów jednostek
nie wykonujemy dodatkowego odczytu historii. Zliczanie
`MaxUnitStatesPerDecision`, `MaxMemberRefsPerDecision`,
`MaxGroupsPerDecision` i reszta filtrowania bez zmian.
To tylko wybór celu; nie naprawia źródła berserk/possession,
nie decyduje, czy wolno legalnie zabić dawną jednostkę,
nie przejmuje/odwołuje kontroli.

Żadnych zmian w `APX_Controller`, `APX_MissionPlanner`,
`APX_CombatPlanner`, X4/relay/plant, timerze, scoringu
lub już bezpiecznym HUD v28. V32 rejestratora/diagnostyki
pozwala odróżnić zachowanie od v31 w nowym teście.
`tests/test_berserker_focus.py` wykonuje czystą regułę UC
`ExcludeFormerLocalBerserker` i kontroluje strukturalnie
historyczne ownership/scope/fail-closed; sama kontrola
źródłowa nie zastępuje kompilacji SDK.

## Kolejność integracji i ograniczenia

**Stacked PR #68**, base `helper/31-revealed-squad-focus` (PR #65/v31)
nad `helper/62-persistent-tactical-panel` (PR #63/v30).
Przed review/merge LEAD powinien ustalić kolejność,
uwzględnić zmiany main v29 (PR #64/#66) i rozstrzygnąć
rebase. Nic nie modyfikuje już przetestowanej przez użytkownika
paczki v29; nadal native LOSS i +7100 jako baseline.

W grze po odpowiedniej kompilacji sprawdzić, czy marker
`berserker_focus` podczas Sweep unika ID własnych
sprzed kontroli (23/24/26 dla obserwowanego seeda),
nie uruchamia nowych nielegalnych akcji,
nie blokuje X4/relay i czy poprawia native win i końcowe
punkty. Jest to **ochrona wyboru celu**, nie obietnica
poprawy 21 pustych ruchów w turach1–3 lub przeżywalności;
to kolejne zadania #56.

Surowe logi, minidumpy, prywatne configi, SKU/SDK,
pliki/ścieżki użytkownika nie są publikowane.
