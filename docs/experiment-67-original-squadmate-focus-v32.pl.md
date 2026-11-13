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
`PriestPsiMindControl` skierowane w24 są MISS, lecz rejestrator mógł
pomijać udane przejęcia przy sprawdzaniu własności dopiero po akcji.
Te pudła nie wykluczają zwykłego Mind Control; konkretny sprawca pozostaje
nieustalony. Nie opierać bezpieczeństwa wyłącznie
na `IsReclaimableControlledSquadmate`, który chroni konkretny,
odwracalny aktywny efekt. Szczegóły [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4#issuecomment-6851447903).

## Zmiana źródeł v32

W `APX_BerserkerFocus.uc` dla aktualnie wrogiej
jednostki `BerserkerMP` rozważanej jako członek `AIGroup`
sprawdzamy read-only stan jednostki as-of zweryfikowany początek misji:
`GetGameStateForObjectID(UnitState.ObjectID,, StartIndex)`.
LEAD zastąpił proponowane GetOriginalGameStateRevision: ten stock getter
zwraca najstarszy stan w bieżącym archiwum, bez gwarancji początku misji.
StartIndex musi być nieujemny, a kontekst stanu typu TacticalGameRule
z GameRuleType TacticalGameStart. Nigdy nie przekazujemy -1, które oznacza
stan bieżący. Wzorzec as-of początku misji występuje w stock WillRoll.
Jeżeli początkowy stan jest XCOM i należy do tego samego
`PlayerID`, **nie nadajemy bonusowego wspólnego celu** na tej
jednostce. Jeżeli oryginału nie można bezpiecznie odczytać,
również pomijamy wyłącznie bonus/goal dla niezweryfikowanego
BerserkerMP — fail closed, nigdy nie zmieniamy natywnej
listy akcji ani legalności przeciwnika.

Własny squad i tak zawsze oceniamy osobno z aktualnego
`XComGameState_Unit`. Pierwotnie wrodzy BerserkerMP pozostają
dozwolonymi kandydatami, jeżeli stan początku misji pozwala potwierdzić,
że nie należeli do gracza. Dla innych szablonów jednostek
nie wykonujemy dodatkowego odczytu historii. Zliczanie
`MaxUnitStatesPerDecision`, `MaxMemberRefsPerDecision`,
`MaxGroupsPerDecision` i reszta filtrowania bez zmian.
To tylko wybór celu; nie naprawia źródła berserk/possession,
nie decyduje, czy wolno legalnie zabić dawną jednostkę,
nie przejmuje/odwołuje kontroli. BerserkerMP utworzony dopiero po początku
misji może nie mieć potwierdzonego stanu i nie otrzymać miękkiego fokusu.

Żadnych zmian w `APX_Controller`, `APX_MissionPlanner`,
`APX_CombatPlanner`, X4/relay/plant, timerze, scoringu
lub już bezpiecznym providerze punktacji v28. LEAD poprawił również
RecordResults: wynik pozostaje w zapisie, jeżeli źródło lub cel należał
do lokalnego gracza przed albo po akcji. Dotyczy to primary i multi-targetów,
także redakcji identyfikatorów. Poprzedni indeks nie przekracza początku
misji i nigdy nie korzysta z -1 jako odczytu poprzedniego stanu.
Source_scope nadal opisuje obserwację po akcji; niewidoczne źródło pozostaje
ukryte, a brak pewnego sprawcy nie jest zastępowany domysłem. Format rekordów,
wyniki natywnych akcji i punktacja nie zmieniają się.
V32 rejestratora/diagnostyki
pozwala odróżnić zachowanie od v31 w nowym teście.
`tests/test_berserker_focus.py` wykonuje czystą regułę UC
`ExcludeFormerLocalBerserker` i kontroluje strukturalnie
historyczne ownership/scope/fail-closed; sama kontrola
źródłowa nie zastępuje kompilacji SDK.

## Kolejność integracji i ograniczenia

PR #68 powstał jako stos nad #63/v30 i #65/v31. LEAD scalił te dwa tematy
osobno, uwzględnił main z #64/#66, poprawił odczyt początku misji i lukę
rejestratora. Końcowa paczka zachowuje usunięcie nieużywanej Distance.
Kompilacja Windows i gra v32: **NOT RUN**. Paczka v29 pozostaje historycznym
baseline: native LOSS i finalne +7100.
[Niezależnie sprawdzony raport v29](report-2026-11-13-v29.pl.md).

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
