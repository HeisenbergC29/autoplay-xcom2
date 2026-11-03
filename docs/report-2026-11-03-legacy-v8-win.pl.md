# Pierwsze zwycięstwo Legacy Operations — mission-report-v8

Raport `AutoplayXCom2-20261103-002926-7428f88e.zip` potwierdza zwycięstwo
pierwszej misji „Blast From the Past”: `ChallengeAbductionGasStation`,
trudność `2` (Dowódca), rewizja `mission-report-v8`. Sesja
`2026-11-3_1-16-10-739_915` rozpoczyna się w `Logs/Launch.log`, linia 364,
i kończy wynikiem **win w turze 14** (linie 7969, 7982 i 8035).
Użytkownik również potwierdził sukces i zapowiedział próbę następnej misji.

To potwierdzenie pojedynczego ukończenia tej misji. Nie potwierdza jeszcze
całej operacji Legacy, wyniku punktowego ani zwycięstw w innych misjach.

## Integralność i sesje w archiwum

Sprawdzono rozmiary i SHA-256 wszystkich czterech logów wymienionych
w `manifest.json`: **4 z 4 wpisów zgodne**. Bieżący `Launch.log` ma
1767881 bajtów, SHA-256
`079afb1b45f438ceebc9df4fe89b883838ede9d1deee6c20654cbad94893a00c`.

Archiwum zawiera pięć sesji. Tylko ostatnia dotyczy zwycięskiej próby v8;
rewizje ustalono z wpisów `start`, nie z dat plików.

| Sesja | Misja | Trudność | Rewizja | Wynik |
| --- | --- | --- | --- | --- |
| `2026-11-2_20-59-12-60_915` | `ChallengeAbductionGasStation` | 2 | v7 | `loss`, kopia poprzedniego raportu |
| `2026-11-2_21-20-47-711_891` | `SabotageCC` | 3 | v7 | `loss` |
| `2026-11-2_21-27-11-349_2` | `SabotageTransmitter` | 2 | v7 | `unknown`, brak wpisu końca |
| `2026-11-2_23-54-25-941_890` | `SabotageCC` | 3 | v7 | `loss` |
| `2026-11-3_1-16-10-739_915` | `ChallengeAbductionGasStation` | 2 | v8 | **`win`** |

Backup `21.19.20` jest identyczny z ostatnim `Launch.log` poprzedniego
archiwum `200526`. Pozostałe cztery sesje są nowe względem wcześniejszych
raportów. Łącznie z dotychczasowym materiałem daje to jedenaście odrębnych
sesji, w tym cztery próby Legacy Operations.

Niepełna sesja `SabotageTransmitter` ma nietypowy skład własnych jednostek
`BerserkerMP` i zdolność `DevastatingPunchMP`. Nie należy zaliczać jej jako
porażki, testu Legacy ani potwierdzonego trybu multiplayer wyłącznie na
podstawie nazwy szablonu. Dwie dodatkowe porażki Gatecrashera dotyczą v7,
więc nie stanowią testów skuteczności v8.

## Przebieg zwycięskiej próby

Autoplay wydał **56 zaakceptowanych poleceń, bez odrzuceń**:

- 23 ruchy;
- 15 `StandardShot`, 1 `SniperStandardFire`, 3 `SwordSlice`;
- 4 `Reload`, 4 overwatch, 2 `HunkerDown`;
- 3 `AidProtocol`, 1 `MedikitHeal`;
- 0 granatów i 0 ewakuacji.

Ostatni `StandardShot` Centrala zabija Viper `63509` z 1 HP, po czym zapis
dochodzi do `outcome=win` bez zaległych klatek historii (linie 8034–8035).
Analizator wskazuje osiem potwierdzonych eliminacji widocznych wrogów.

Końcowy stan czterech żołnierzy:

| Jednostka | Ostatni stan | Linia |
| --- | --- | --- |
| Specjalista `63468` | żywy, 1/5 HP, `incapacitated=False` | 7850 |
| Central `63474` | żywy, 2/7 HP, `incapacitated=False` | 7983 |
| Snajper `63480` | martwy, 0/5 HP | 8031 |
| Żołnierz `63486` | martwy, 0/5 HP | 8032 |

Zwycięstwo oznacza więc ukończenie celu z dwiema śmierciami i dwoma rannymi
ocalałymi. Jakość wyniku i straty pozostają osobnymi miarami do poprawy.

W logu występuje jedno włączenie autoplaya (linia 363), a zatrzymanie dopiero
przy zakończeniu misji (linia 8036). Brak ręcznych zatrzymań w rejestrze
wspiera ocenę ciągłego działania, lecz sam log nie rejestruje wszystkich
naciśnięć gracza i nie jest pełnym dowodem braku każdej możliwej interwencji.
Nie ma `ScriptWarning`, `Accessed None`, `Critical` ani `Fatal`.

## Co ta próba potwierdza, a czego nie

Raport potwierdza uruchomienie v8, wykonywanie rozkazów do końca misji,
użycie wsparcia, leczenia, obrony i wspieranych ataków wręcz. Powstają nowe
propozycje granatów dla par, np. `pair_offset_centers=2` w decyzji 2
(linia 919), ale żaden rzut nie został przyjęty.

Wszystkie zapisane `candidate` i `chosen` mają `known_released_allies=0`
i `known_linked_enemies=0`. Ta próba **nie potwierdza praktycznie nowej premii
za zabicie źródła kontroli lub zombie**, bo nie wystąpił oceniony kandydat
z taką znaną korzyścią. Nie należy przypisywać jej zwycięstwa.

W 51 sprawdzeniach obsługiwanej zdolności granatu oceniono 203 punkty: 75 odrzucono
przez zasięg, 6 przez trajektorię i 122 przez bezpieczeństwo. Dziesięć migawek
ostatniego powodu odrzucenia `objective_near_blast` podaje `empty_footprint`, ID 0 i klasę
`redacted` (decyzje 2–10). To konkretny sygnał ograniczenia przy braku geometrii
chronionego celu, a nie potwierdzenie jego rzeczywistej bliskości. Tożsamości
obiektu nie ustalono. Ochrony nie rozluźniono na podstawie tej jednej próby.

Agregat wyników podaje trzy pudła przyjazne i dwa wrogie w zdarzeniach
`result`. Dwa dodatkowe `result_target.hit=3` opisują pudła pazurów wobec
specjalisty (linie 5033 i 5380). Agregat nie obejmuje wszystkich celów ataków
obszarowych i nie jest pełną statystyką celności.

## Punktacja Legacy

Log potwierdza system oceniania: ukończenie celu i eliminacje mają wartości
malejące z upływem tur, a osobno występują kategorie ocalałych i nietkniętych
żołnierzy. Inicjalizacja pierwszej misji podaje m.in. maksymalnie 10000 punktów
za cel, 12000 za ośmiu przeciwników oraz limity kategorii żołnierzy
(linie 326–345).

**`MaxScore=46000` jest pułapem wyliczonym przy inicjalizacji, a nie zdobytym
wynikiem.** W raporcie nie ma końcowej liczby zdobytych punktów, sumy operacji
ani medalu. Nie wyliczamy ich zastępczo ze statystyk autoplaya. Kolejne próby
powinny rozdzielać: zwycięstwo, straty, liczbę tur, wynik misji i wynik operacji,
jeśli gra je pokazuje.

## Następna misja na tej samej wersji

Po zwycięstwie gra ładuje `Plot_TWN_Abduction_Cemetery` (linia 8055),
a inicjalizacja punktacji wskazuje `ChallengeAbductionCemetery`
(linie 8161–8162). Kismet zapisuje `Ladder and rung` z wartościami 1 i 2
(linia 8115). Potwierdza to wejście do drugiej misji operacji, lecz nie jej
rozegranie: w tym pliku nie ma kolejnego `APXREC start`.

Inicjalizacja następnej misji podaje `MaxScore=64000` i pięciu żołnierzy.
To również wartości konfiguracji nowej misji, nie zdobyte punkty ani wynik
całej operacji. Następną próbę wykonujemy na **tym samym v8**. Aktualizacja
dokumentacji wyniku nie zmienia kodu moda i nie wymaga ponownej kompilacji.
Po uzyskaniu sterowania trzeba ponownie włączyć autoplay dla nowej misji.
