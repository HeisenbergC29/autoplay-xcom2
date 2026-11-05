# Współpraca przy Autoplay XCOM 2

Zacznij od [AGENTS.md](AGENTS.md), [podziału pracy](docs/TEAM.pl.md)
i [aktualnego stanu projektu](docs/PROJECT-STATE.pl.md).
Wspólna baza to `main`; zmiany trafiają przez pull requesty.

## Przed rozpoczęciem

Przeczytaj aktualne issue i PR-y. W wybranym issue napisz rolę `HELPER` albo
`LEAD`, zakres plików i SHA bazy; otwórz roboczy PR. Zmiany z osobnego repozytorium
najpierw zinwentaryzuj względem aktualnej bazy. Nie przenoś całej starej gałęzi
nad kod v16. [Procedura importu](docs/TEAM.pl.md#import-z-osobnego-repozytorium).

## Testy dostępne bez SDK

```text
python -m unittest discover -s tests -p 'test_*.py' -v
pwsh -NoProfile -File tests/Test-BuildHelpers.ps1
pwsh -NoProfile -File tests/Test-CollectMissionRecording.ps1
pwsh -NoProfile -File tests/Test-CollectSdkSources.ps1
git diff --check
```

Publiczne CI uruchamia testy Python i pomocników PowerShell. Testy prywatnych
wejść są wtedy pomijane; w raporcie podaj rzeczywiste liczby PASS/SKIP.

## Dodatkowe kontrole z prywatnymi wejściami

Jeżeli masz odpowiednie pliki, ustaw lokalne zmienne:

| Zmienna | Katalog |
| --- | --- |
| `APX_SDK_SOURCE_ROOT` | źródła SDK `Development/SrcOrig` |
| `APX_GAME_CONFIG_ROOT` | bazowy `Config` gry |
| `APX_SDK_CONFIG_ROOT` | bazowy `Config` SDK do porównania |
| `APX_GAME_DLC_ROOT` | katalog z podfolderami `DLC_1`, `DLC_2`, `DLC_3`, `TLE`, `XCom_DLC_Day0`, każdy z `Config` |

Uruchom ponownie odpowiednie kontrole; dla zmian UnrealScript także
`python tools/check-sdk-references.py --sdk <katalog-źródeł-SDK>`.
Nie publikuj tych wejść. [Dane i pochodzenie katalogu](docs/dlc-config-knowledge.pl.md).

Kompilację Windows i testy w grze raportujemy osobno, z dokładnym SHA i scenariuszem.
Nie są wykonywane przez publiczne CI. [Budowanie i próba](docs/legacy-test.pl.md).
Sukces misji wymaga zwycięstwa i pewnego wyniku większego od zera.
