# Próba v11 — źródło początkowych 24000 punktów

Raport `AutoplayXCom2-20261103-225232-18035b97.zip` zawiera cztery sesje.
Wszystkie cztery pliki zgadzają się z rozmiarem i SHA-256 manifestu.
Najnowsza sesja to `2026-11-3_23-46-34-684_888`, `SabotageCC`, trudność 3,
rewizja `mission-report-v11`. Zakończyła się porażką w turze 6.

## Wyniki sesji w archiwum

| Sesja | Misja | Rewizja | Wynik | Przyjęte rozkazy |
| --- | --- | --- | --- | --- |
| `2026-11-3_17-9-22-656_892` | SabotageCC | v10 | loss, znana wcześniejsza próba | 55 |
| `2026-11-3_19-44-47-805_915` | ChallengeAbductionGasStation | v10 | loss | 34 |
| `2026-11-3_20-52-32-977_889` | SabotageCC | v10 | loss | 67 |
| `2026-11-3_23-46-34-684_888` | SabotageCC | v11 | loss | 25 |

W najnowszej próbie przyjęto wszystkie 25 rozkazów, bez odrzuceń: dziesięć
ruchów, sześć `StandardShot`, pięć overwatch, dwa `HunkerDown`, jeden `Reload`
i jeden `ThrowGrenade`. Końcowe obserwacje potwierdzają śmierć wszystkich
czterech żołnierzy oraz cztery zabicia widocznych przeciwników.
`Logs/Launch.log`: start w linii 252, zakończenie w linii 3878,
`outcome=loss`, `history_pending=0`.

## Co faktycznie pokazywał licznik v11

Pierwszy zapis `hud_score` w najnowszym logu (linia 472) zawiera `~24000/…`,
jeszcze przy decyzji 0. Późniejsze odczyty to 24500, 23500, 24300, 18300,
13300, 7300, 6300 i 6400. Prefiks `~` potwierdza użycie oceny porównawczej.
W tej zwykłej misji nie ma `game_score`, `score_delta` ani inicjalizacji
natywnych tabel `XCom_Challenge`.

24000 wynika z konwencji profilu `wotc_legacy_observed_v1`: czterem
kwalifikowanym żołnierzom doliczono na początku po 6000, a następnie odejmowano
kary. To własna konwencja porównawcza wprowadzona w modzie i analizatorze.
Log nie dostarcza dowodu, że gra przyznaje takie punkty na początku misji.

Mianownik w samym pliku logu zapisuje się jako znak sterujący U+0014.
Jest to zgodne z utratą wyższych bajtów znaku „—” przez zapis tekstu w logu;
archiwum nie zawiera obrazu HUD-u, więc nie potwierdza wyglądu tego znaku
na ekranie gry.

## Dowód z natywnej punktacji Legacy

Nowa próba GasStation na v10, w
`Logs/Launch-backup-2026.11.03-20.51.09.log`, rejestruje natywny
`CumulativeScore=0` na starcie (linia 314), a następnie wynik −15000 przy
zakończeniu (linia 5713). Maksymalna pula tabeli gry wynosi 46000.

W tej tabeli `UninjuredBonus=1000` i `WoundedBonus=5000` występują w wierszach
maksymalnej puli za czterech żołnierzy (linie 299–301), z `ScoreMin=0`.
Są to parametry punktacji i maksima kategorii. Nie są potwierdzeniem
przyznania 6000 punktów na żołnierza w momencie startu. Odczyt natywny
rzeczywiście zaczyna się od zera.

## Ostatni tekst HUD-u a końcowe obserwacje

Ostatni `hud_score` najnowszej próby, 6400, został zapisany w linii 3755,
przed ostatnią śmiercią. Później HUD jest ukryty; żołnierz `428` ginie
w końcowych obserwacjach linii 3875–3877. Brakuje późniejszego odczytu
tekstu licznika.

Analiza archiwalnym profilem v1 daje końcowy częściowy subtotal 1400:
24000 początkowych premii − 4000 za rany − 20000 za cztery śmierci + 1400
za cztery zabicia. `total` pozostaje nieznany. Ostatni widoczny odczyt
6400 i końcowa suma 1400 mają różne okna obserwacji; nie wolno przedstawiać
pierwszego jako odczytu po ostatnim zdarzeniu. Obie liczby są oceną
porównawczą v1, nie natywnymi punktami tej misji.

W najnowszym logu nie ma `ScriptWarning`, `Accessed None`, `Fatal` ani
`Critical`. Są komunikaty zasobów i efektów dźwiękowych gry. Archiwum nie
zawiera logu kompilatora ani zapisu gry.

[Opis licznika](score-display-v10.pl.md) · [Rejestracja misji](mission-recording.pl.md)
