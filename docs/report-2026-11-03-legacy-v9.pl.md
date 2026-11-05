# Próba v9 — ratunek potwierdzony, GasStation przegrane

Raport `AutoplayXCom2-20261103-154548-04a80f7b.zip` zawiera cztery sesje.
Najnowsza uruchamia `mission-report-v9` w **pierwszej** misji
`ChallengeAbductionGasStation`, na Dowódcy (`difficulty=2`). Nie jest to próba
drugiego etapu Cemetery. Końcowy rekord potwierdza **porażkę w turze 7**.

## Integralność i zakres

Wszystkie cztery pliki logów zgadzają się z rozmiarem i SHA-256 w manifeście.
Analizator odczytał 21 527 rekordów i cztery sesje bez ostrzeżeń o niepełnym
zakończeniu najnowszej próby. Archiwum zawiera logi, bez zapisu gry i bez
logu kompilatora. Uruchomienie v9 i wykonanie nowej procedury potwierdzają
działanie załadowanego pakietu; nie są audytem całego procesu budowania.

| Sesja | Misja | Rewizja | Trudność | Wynik | Przyjęte rozkazy |
| --- | --- | --- | --- | --- | --- |
| `2026-11-3_1-16-10-739_915` | GasStation | v8 | 2 | win, znana wcześniejsza próba | 56 |
| `2026-11-3_1-45-47-568_889` | `SabotageCC` | v8 | 3 | win | 68 |
| `2026-11-3_11-35-25-768_915` | GasStation | v8 | 2 | loss | 30 |
| `2026-11-3_16-39-15-336_915` | GasStation | **v9** | 2 | **loss** | **33** |

Wyniki v8 pozostają osobnymi próbami; nie dowodzą skuteczności v9.

## Przebieg najnowszej próby

`Logs/Launch.log`: start w linii 274, `revision=mission-report-v9`; zakończenie
w linii 5712, `outcome=loss`, `history_pending=0`. Ostatnia faza wskazuje turę 7.
Gra przyjęła wszystkie 33 rozkazy, w tym 14 ruchów; nie odrzuciła żadnego.
Pozostałe akcje to osiem `StandardShot`, jeden `SniperStandardFire`, cztery
`HunkerDown`, dwa `Reload`, dwa `AidProtocol`, jeden overwatch i jedna
`MedikitStabilize`. Granatów nie użyto.

Potwierdzono trzy zabicia widocznych przeciwników. Na końcu:

- żołnierz `63486` nie żyje;
- Central `63474` jest nieprzytomny, 1/7 HP, z `ladder_killed_scored=True`;
- snajper `63480` żyje, jest ustabilizowany i nieprzytomny, 1/5 HP;
- medyk `63468`, wcześniej własna jednostka, figuruje jako widoczny przeciwnik,
  3/5 HP — oddział utracił nad nim kontrolę.

Nie należy utożsamiać dwóch kar `CMPT_DeadSoldier` z dwiema fizycznymi
śmierciami: jedną z nich gra przyznaje za fabularne wyłączenie Centrala.

## Ratunek i łup

Nowa nawigacja ratunkowa zadziałała w grze. W decyzji 14 medyk `63468`
otrzymał `rescue_candidate` dla snajpera `63480` (linia 2423), wykonał ruch
do `(23,14,1)` (linia 2432), a w decyzji 15 użył legalnej stabilizacji
z oceną 400 i `accepted=True` (linia 2517). Następny zapis pacjenta
pokazuje `bleeding_out=False`, `unconscious=True` (linia 2578).
To potwierdza sekwencję podejście → odświeżony legalny cel → stabilizacja.
Uratowanie pacjenta nie wystarczyło do zwycięstwa całego oddziału.

W najnowszej próbie wszystkie 60 zapisów dostępności `Loot` mają
`AA_NoTargets`, z nowym `handler=loot`. Nie ma wybranego `Loot` ani
`loot_candidate`. Ten log nie potwierdza pominięcia legalnego podniesienia
ani działania nowej nawigacji po łup; ta część wymaga osobnego przypadku.

## Punktacja gry i ocena porównawcza

Nowa telemetria punktów działa. Gra podała startową pulę `MaxScore=46000`
oraz odczyty `CumulativeScore`: od **0** na początku rejestracji do
**−10000** przy jej zakończeniu. Drabinka i etap pozostają `1/1`.
Końcowy odczyt znajduje się w linii 5703. To wynik zaobserwowany w grze;
nie dowodzi przetworzenia wszystkich ewentualnych późniejszych ekranów premii.

Dziewięć zaobserwowanych zdarzeń natywnych obejmuje zabicia za 1500, 1400
i 1100, cztery pierwsze rany po −1000 oraz dwie straty po −5000.
W tej konkretnej próbie ich `AddedPoints` sumują się do −10000, zgodnie
z odczytem stanu. `LadderBonus` przy zabiciach nie jest dodatkowo doliczany
do tej sumy. Maksymalna pula 46000 nie jest zdobytym wynikiem.

Sześć zapisów `score_rule` odczytuje rzeczywiste reguły żołnierzy, czasu oraz
widocznych typów: Faceless, Viper, Sectoid i przejęty Soldier. Nie ma zaliczenia
celu misji, więc nie zostało przetestowane zdarzenie `objective_completed`.

Wspólny profil `wotc_legacy_observed_v1` zwraca **częściowy subtotal 14000**
i `total=null`. Zawiera z góry przewidziane premie żołnierzy, których bieżący
odczyt natywny nie uwzględnia w ten sam sposób. Brakuje dowodu pełnego pokrycia
celów i ratowania cywilów oraz pochodzenia zabitych przeciwników. Tego
subtotalu nie wolno przedstawiać jako oficjalnego wyniku −10000.

## Pozostałe ograniczenia

W najnowszym logu nie ma `ScriptWarning`, `Accessed None`, `Fatal` ani
`Critical`. Występują komunikaty zasobów gry: brak danych tekstury,
nieodczytana domyślna pula postaci oraz ostrzeżenia fizyki i ładowania.
Nie stanowią dowodu błędu nowej stabilizacji ani telemetrii.

Skan granatów nadal nie dopuszcza żadnego rzutu: 43 dostępne analizy,
163 sprawdzone centra, 47 odrzuceń zasięgu, cztery trajektorii i 112 obszaru
rażenia. Powody obejmują ochronę jednostek, celu i wybuchowych elementów
scenerii. Sam brak granatów nie uzasadnia usunięcia zabezpieczeń.

Żaden zapis kandydata lub wybranego ataku nie ma dodatnich
`known_released_allies` ani `known_linked_enemies`. Próba nie potwierdza
jeszcze skuteczności premii za zabicie źródła kontroli. Medyk po raz pierwszy
pojawia się jako wróg w linii 5687, już po ostatniej decyzji 33 (linia 5594).
Nie następuje kolejna decyzja ani atak, więc nie było okazji sprawdzić premii
po przejęciu żołnierza. Porażka pokazuje, że mimo skutecznego ratunku potrzebne
są dalsze próby całej taktyki.

[Reguły i ograniczenia v9](tactics-v9.pl.md) ·
[Rejestracja misji](mission-recording.pl.md)
