# #79 etap D — źródła i pochodzenie punktacji w raporcie (bez zmiany runtime)

Baza `main c833dcc4189a84b90b169803a2531889e9c48fb4`,
`mission-report-v38`; gałąź `helper/79-v3-report-provenance`.
Ten etap zmienia **tylko analizator Python i jego prezentację/testy**,
nie kod moda w grze ani marker runtime.

## Rzeczywista luka

`APX_MissionRecorder.RecordHUDScore` w rewizji v38 dla licznika
nonnative zapisuje w prawdziwym `hud_score`:

- `display=~<signed_integer>/--` (albo symbol nieznanego limitu),
- `comparison_profile=wotc_legacy_config_observed_v3_partial`,
- `comparison_status=partial`,
- `rate_source=installed_ladder_config`,
- `native_parity_proven=false`,
- `event_coverage_proven=false`.

Offline `tools/game_scoring.py` dotychczas zawsze przeliczał
**archiwalny** `wotc_legacy_observed_v2` z
`tools/legacy-score-rules.json`; nie odczytywał osobno rzeczywistej
obserwacji v3. Przy braku natywnej końcowej punktacji
`assess_attempt` mógł wybrać v2 jako źródło obserwowanego wyniku,
mimo że log wskazywał inny, nowszy licznik v3.
To błąd atrybucji (nie dowód błędnych stawek v3).

## Poprawka i granice

`runtime_observed_v3(records)` jest odrębną obserwacją.
Dla **dokładnego** profilu v3 wymaga kompletnych flag partial,
realnego `installed_ladder_config` i poprawnie oznaczonego
`~<liczba>/<nieznany limit>`. Zachowuje ostatnie zaobserwowane
subtotal, liczbę obserwacji i provenance. Sprzeczna/missing flaga,
nieznane źródło stawek lub błędny HUD oznacza
`incomplete_runtime_v3_observations` i nie podaje wiarygodnego
subtotal; nie zgaduje go na podstawie wcześniejszego poprawnego
wpisu. Wynik nadal zawsze `status=partial`, `total=None`,
`is_official_game_score=False`, z brakami
`native_rule_parity`, `complete_event_coverage` i
`final_mission_score`.

`score_session` zwraca teraz trzy rozłączne grupy:
`official` (natywny wynik),
`runtime_observed_v3` (rzeczywiste częściowe HUD) i
`comparison` (historyczne, zamrożone przeliczenie v2).
W `assess_attempt` **potwierdzony końcowy native score ma
pierwszeństwo**; v3 jest wybierany nad retrospektywnym v2
tylko wtedy, gdy v3 faktycznie występuje w sesji.
Pozytywne ~7100 v3 + native WIN daje nadal UNKNOWN z
`mission_score_incomplete`; LOSS jest FAIL niezależnie od punktów.
Historyczne sesje bez v3 nie zmieniają dawnych założeń/przeliczeń v2.
`tools/analyze-mission-log.py` wyświetla obie wartości i źródła
oddzielnie; nie oznacza v3 jako oficjalnego.

Nie zmieniamy stawek, nie rekonstruujemy nowych zdarzeń,
nie odczytujemy ukrytego stanu ani nie przekazujemy do gry
wymyślonych wartości. W szczególności v3 nie dowodzi jeszcze
pełnej kwalifikacji reinforcement/disabled/restart/bonusów ani
kompletności historycznych zdarzeń cywilnych; to kolejne kontrakty
w #79. Pełna zgodność native award/decay wymaga dokładnego porównania
z wynikiem silnika na tych samych zdarzeniach. Brak ujawnionych
ciał native C++ nie jest dowodem, że punkty są równe.

## Dodatkowy audyt źródeł prywatnego WOTC SDK — disposition

Przeprowadziłem niezależne porównanie istniejącego
`APX_LegacyObservedV3.OnCivilianRescued` z prawdziwym źródłem
zdarzenia gry: `XComGame/Classes/X2AIBTDefaultActions.uc:1222`
emituje `CivilianRescued`, przekazując w `EventData` żołnierza
ratownika, a w `EventSource` ratowanego cywila. Tę konwencję
potwierdza `AnalyticsManager.uc:354`. Obecny observer w
`APX_LegacyObservedV3.uc` poprawnie przypisuje
`Rescuer = EventData`, `Civilian = EventSource`.
**Hipoteza o odwróconych argumentach była błędna — odrzucona,
nie wprowadzono niepotrzebnej zmiany.** Natywny
`XComGameState_LadderProgress.OnCivilianRescued` w
`:1395–1412` deleguje do `XComGameState_ChallengeScore.AddCivilianRescued`,
której ciało jest native i nie można z samej deklaracji odtworzyć
wszystkich warunków przyznania nagrody. Brak dowodu, że samo
`bRemovedFromPlay` cywila po wczytaniu oznacza akcję ratunku
dokonaną przez XCOM (możliwe inne przyczyny). Dlatego **late
civilian replay: UNSUPPORTED**, bez przyznawania punktów
na podstawie bieżącej flagi. Potrzebny byłby dowiedziony
historyczny event/context ze źródłem i unikalnym ID cywila
oraz zgodność z natywną kwalifikacją.

`X2ChallengeModeDataStructures.uc:350–367` posiada stawki
`SpawnedPoints`, `ReinforcementPoints`, `DisabledPoints`,
`MinDisabledPoints`. Istnienie pól nie dowodzi, że obecne
`NewSpawnedUnit` odróżnia wszystkie posiłki ani że niepełne
`GetPreviousTeam` lub koniec gry kwalifikują disabled.
`XComGameState_ChallengeScore.uc:18–24` wystawia native
`AddKillMail`, `AddCompletedObjective`,
`AddCivilianRescued`, lecz nie zawiera ich ciał.
**Reinforcement/disabled: nadal UNSUPPORTED** dla niepotwierdzonych
przypadków; wymagana autentyczna klasyfikacja z native zdarzenia
oraz porównanie nagrody z obserwowanym `score_delta` na tym
samym `history` i `ObjectID`.

`XComGameState_LadderProgress.uc:116` deklaruje
`RestartScorePenalty`, a `UIPauseMenu.uc:541`
przekazuje go do parametru menu restartu. Nie jest to
dowód, że samo `restart_requested` może bezpiecznie odtworzyć
przyznaną karę końcową. **Restart/bonus: UNSUPPORTED**
bez potwierdzonego natywnego księgowania w historii
i kompletności przed/po load. `TurnOffset` i
`DecreasePerTurn` potwierdzają konfigurację, ale exact
decay/qualification C++ wymaga native delta dla granicznych tur.
To świadoma decyzja: brak nowych fikcyjnych punktów,
zachowany v3 partial i brak automatycznej oficjalności.

## Walidacja i końcowa bramka

`tests/test_runtime_v3_provenance.py` uruchamia prawdziwy analizator
na syntetycznych `APXREC`: dodatnie i ujemne subtotal, zero,
brakujące/niepoprawne flagi, konflikty atrybucji, sekwencję
obserwacji, znany native final, dziedziczny v2 i czytelny raport.
`tests/test_game_scoring.py` zachowuje dotychczasowe reguły v2.
To nie jest native WOTC make ani test gry.

Stan #4 **BLOCKED** na polecenie użytkownika. Po review LEAD
nie przekazywać oddzielnego buildu tej poprawki; dopiero po
skończeniu całej skończonej kolejki #86 jedna paczka do Windows
i misji. Native make/game: **NOT RUN**.
