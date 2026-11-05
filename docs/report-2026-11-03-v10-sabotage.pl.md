# Próba v10 — SabotageCC i brak natywnej punktacji

Raport `AutoplayXCom2-20261103-161607-122b620a.zip` zawiera cztery sesje.
Najnowsza to `2026-11-3_17-9-22-656_892`, misja `SabotageCC`, trudność 3,
rewizja `mission-report-v10`. Pozostałe sesje są wcześniejszymi próbami v8/v9.
Wszystkie cztery pliki zgadzają się z rozmiarem i SHA-256 manifestu.

## Wynik najnowszej próby

`Logs/Launch.log`: start w linii 250, zakończenie w linii 7595,
`outcome=loss`, `history_pending=0`. Ostatnia tura to 12.
Gra przyjęła wszystkie **55 rozkazów**, bez odrzuceń: 22 ruchy,
22 overwatch, dziewięć `StandardShot`, jeden `HunkerDown` i jeden `ThrowGrenade`.
Potwierdzono dwa zabicia widocznych przeciwników.

Na końcu żołnierze `411`, `417` i `423` nie żyją. Żołnierz `429` nadal
jest żywy, ma 1 HP, ale jest obezwładniony i wykrwawia się. Nie należy
zaliczać go jako czwartej potwierdzonej śmierci.
Nie ma `ScriptWarning`, `Accessed None`, `Fatal` ani `Critical`.
Log potwierdza uruchomienie v10; nie zawiera obrazu HUD-u ani audytu kompilacji.

## Dlaczego licznik pokazywał „—”

W najnowszej sesji nie ma `game_score`, `score_delta`, `score_rule` ani
inicjalizacji tabel `XCom_Challenge`. Brakuje dowodu natywnego wyniku oraz
maksymalnej puli tej zwykłej misji. V10 wyświetla wyłącznie punktację gry:
`APX_MissionScore.GetText()` zwraca znak niedostępności, jeśli nie znajduje
stanu Legacy (`Ladder`) ani natywnego Challenge Mode (`ChallengeData`).
To wyjaśnia sam znak „—”; ten raport nie pokazuje dostępnego oficjalnego
wyniku, który zostałby ukryty.

Osobny problem kodu v10 dotyczy misji z dostępnym bieżącym wynikiem, ale bez
maksimum: warunek `MaximumPoints <= 0` również ukrywa całe pole. Ta gałąź
została poprawiona w v11 przez rozdzielenie dostępności wyniku i maksimum.
Poprawka tej gałęzi
nie tworzy natywnej punktacji dla zwykłego `SabotageCC`.

Analizator raportu oblicza osobno **częściowy subtotal 5200**, `total=null`,
według wspólnego profilu `wotc_legacy_observed_v1`. To premie obserwowanych
żołnierzy, pomniejszone o rany i trzy śmierci, oraz dwa zabicia z domyślną
regułą SDK. Brakuje pełnego pokrycia celów i ratowania cywilów oraz pewnych
reguł i pochodzenia przeciwników. **5200 nie jest oficjalnym wynikiem gry**
i nie zostało wyświetlone przez natywny licznik v10.

## Kierunek osłony w telemetrii

Planer ocenia osłonę względem poszczególnych widocznych przeciwników.
W decyzji 34 (linie 4222–4224) ten sam ruch żołnierza `411` ma osobne wpisy
dla przeciwników `903`, `905` i `907`: każdy podaje bieżącą i docelową osłonę,
LOS oraz wkład do ryzyka. W tym przykładzie docelowa osłona ma poziom 1
względem wszystkich trzech, ale LOS i ryzyko są różne. Są to dane planera,
nie zrzut ekranu natywnego podglądu osłony.

[Licznik v10](score-display-v10.pl.md) · [Rejestracja misji](mission-recording.pl.md)
