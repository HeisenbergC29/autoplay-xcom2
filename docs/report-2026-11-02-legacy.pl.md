# Próba Legacy Operations „Blast From the Past”

Najnowszy `Launch.log` z archiwum
`AutoplayXCom2-20261102-190216-c40ac147.zip` zapisuje porażkę pierwszej misji
„Blast From the Past”: `ChallengeAbductionGasStation`, poziom trudności `2`
(Dowódca), sesja `2026-11-2_17-31-55-750_915`, rewizja `mission-report-v5`.
Misja zakończyła się w turze 7. Jest to materiał porównawczy do następnej
kompilacji, a nie test zmian przygotowanych po tej sesji.

Numery linii poniżej dotyczą właśnie tego `Logs/Launch.log`, chyba że wskazano
inny plik. Początek sesji jest w linii 273; faza końcowa i wynik `loss` w liniach
5237–5244.

## Integralność archiwów i powtórzenia

Zweryfikowano rozmiar i SHA-256 każdego z czterech logów wymienionych
w `manifest.json` obu archiwów: wszystkie **8 z 8 wpisów** odpowiada plikom
w ZIP-ach. Nie wykryto rozbieżności. Nazwy ZIP-ów zawierają czas zebrania
raportu; nie są identyfikatorami osobnych prób gry.

Archiwum `AutoplayXCom2-20261102-162041-fbabf2b4.zip` zawiera cztery starsze
sesje Gatecrashera (`SabotageCC`). W późniejszym archiwum trzy pliki są kopiami
tych samych logów:

| Plik w ZIP-ie `190216` | Identyczny plik w ZIP-ie `162041` |
| --- | --- |
| `Logs/Launch-backup-2026.11.02-16.09.07.log` | ten sam plik |
| `Logs/Launch-backup-2026.11.02-17.02.08.log` | ten sam plik |
| `Logs/Launch-backup-2026.11.02-17.31.00.log` | `Logs/Launch.log` |

W obu archiwach łącznie jest pięć unikatowych sesji. Nie należy sumować
powtórzonych plików jako dodatkowych testów:

| Sesja | Misja | Trudność | Wynik |
| --- | --- | --- | --- |
| `2026-11-2_13-34-41-138_888` | `SabotageCC` | 3 | `loss` |
| `2026-11-2_14-8-10-938_890` | `SabotageCC` | 3 | `loss` |
| `2026-11-2_16-22-52-641_888` | `SabotageCC` | 3 | `loss` |
| `2026-11-2_17-7-19-819_887` | `SabotageCC` | 3 | `loss` |
| `2026-11-2_17-31-55-750_915` | `ChallengeAbductionGasStation` | 2 | `loss` |

Tylko ostatnia sesja jest nową próbą w archiwum `190216`. Cztery wcześniejsze
dotyczą innej misji i nie stanowią czterech dodatkowych prób Legacy Operations.

## Zarejestrowane działania i stan końcowy

Autoplay wydał 29 zaakceptowanych poleceń, bez odrzuceń:

- 14 ruchów;
- 3 `StandardShot`, 4 `SniperStandardFire`, 2 `PistolStandardShot`;
- 2 `SwordSlice`, 1 `AidProtocol`, 1 `overwatch`, 2 `Reload`;
- 0 granatów i 0 `HunkerDown`.

Odnotowano jedno pudło przyjaznej jednostki. To liczba zapisanych wyników,
nie pełna miara jakości ostrzału ani dowód kompletności rejestracji działań
przeciwnika. W najnowszym logu nie ma `ScriptWarning`, `Accessed None`,
`Critical` ani `Fatal`. Są ostrzeżenia silnika. Zapis dochodzi do zakończenia
misji; nie wskazuje zawieszenia autoplaya na interfejsie.

Końcowe obserwacje jednostek:

- `63468`: 0/5 HP, martwy (linia 5238);
- Central `63474`: 1/7 HP, żywy, lecz niezdolny do działania
  (`incapacitated=True`, linia 5239);
- `63486`: 0/5 HP, martwy, `removed=True` (linia 5240);
- snajper `63480`: ostatnio zapisany jako `visible_enemy`, nadal żywy z 5/5 HP
  (linia 5227). Wcześniej był przyjazny, również z 5/5 HP (linia 4921).
  Zapis wskazuje przejęcie jednostki przez przeciwnika, a nie jej śmierć ani
  niewyjaśnione zniknięcie. Snapshot przeciwnika nie zawiera pola
  `mind_controlled`, więc sam ten rekord nie identyfikuje zdolności ani
  dokładnego momentu przejęcia.

W ostatnim zapisanym ataku `ScythingClaws` Faceless obniża HP Centrala z 3 do 1;
następnie `KnockoutSelf` wyłącza go z walki (linie 5241–5243).

## Osłony i wybór odwrotu

W podglądzie decyzji 21 Faceless `63506` i `63507` mają zapisaną zmianę osłony
Centrala z `0` do `2`, przy zachowaniu linii widzenia. Łączna ocena ryzyka ruchu
spada z `56.4` do `5.64` (linie 3898–3902). Sprawdzenie źródeł gry oraz
odtworzenie rachunku **nie potwierdziły błędu osłon wobec Faceless**:

- stock Faceless ma `IsMeleeOnly() == true`;
- od Centrala na `(30,17,1)` Faceless na `(42,20,1)` i `(45,18,5)` dzieli co
  najmniej 12 pól; obecna funkcja ryzyka przypisuje im wtedy wkład `0`;
- Sectoid na `(44,16,1)` daje wkład `30`; po uwzględnieniu 3/7 HP Centrala
  `CombinedExposure` zwraca zapisane `56.4`;
- po ruchu do `(30,20,1)` wkład Sectoid wynosi `3`, co daje zapisane `5.64`.

Pola osłony w podglądzie same nie określają użytego wkładu przeciwnika.
Zgodność tego rachunku wyklucza wcześniejsze podejrzenie, że dziesięciokrotny
spadek ryzyka wynikał z zastosowania osłony przeciw pazurom Faceless.
Nie potwierdza natomiast, że przyjęty zasięg ryzyka wręcz dobrze przewiduje
następną turę; granica 12 pól wymaga osobnej weryfikacji osiągalności ataku.

Osobnym obserwowanym problemem są kolejne ruchy kosztem ofensywy. Nie każdy
odwrót jest błędem: w decyzji 19 żołnierz mający 1 HP odchodzi spod trzech
widocznych zagrożeń (linie 3564–3571). Późniejsze decyzje Centrala wymagają
jednak porównania z następną próbą:

| Decyzja | Najlepszy zapisany atak Centrala | Wybrany ruch |
| --- | --- | --- |
| 24 | `StandardShot`, 92%, wynik `46.952` | wynik `59.1484`, zużycie ostatniego AP; linie 4403–4413 |
| 29 | `StandardShot`, 85%, wynik `42.4` | wynik `42.8833`, zużycie ostatniego AP; linie 5075–5083 |

Następnie Faceless dopada Centrala. Sekwencja pokazuje, że wycofywanie nie
zapewniło przeżycia i ograniczyło zadawane obrażenia. Nie dowodzi jednak,
że wybranie któregoś strzału wygrałoby misję. Te odwroty pozostają odrębnym
problemem planowania, którego nie wyjaśnia obalone podejrzenie osłon.
Potrzebna jest osobna ocena osiągalności ataku wręcz, odległości i zachowanych
możliwości walki całego oddziału.

## Potwierdzona niespójność oceny AidProtocol

W decyzji 5 specjalista wybiera `AidProtocol` na sobie z wynikiem `32.8`, przed
cofnięciem ocenionym na `26.0` (linie 1217–1224). Po turze przeciwnika zostaje
wyłączony. Klasyfikacja zagrożeń wręcz również w tej decyzji jest poprawna.
Konkretną niespójnością jest za to pominięcie linii widzenia podczas wyceny
wsparcia:

- `DefensiveRisk`, używane przez `AidProtocol`, liczy Viper jako zagrożenie
  dystansowe z wkładem `30`, chociaż między nim a chronioną jednostką nie ma
  linii widzenia. Łączny wynik wynosi `42`, a wartość wsparcia `32.8`.
- `ExposureRisk`, używane przez ruch, stosuje do tego samego zagrożenia
  `KnownThreatRisk`: przy braku linii widzenia wkład spada do `10.5`.
  Zastosowanie tej samej reguły w obronie daje łączny wynik `14.7` i wycenę
  wsparcia `21.88`, czyli poniżej ocenionego na `26.0` odwrotu.

To odtworzenie lokalnej punktacji, nie odtworzenie misji po alternatywnym
poleceniu. Pokazuje konkretną zmianę preferencji między tymi kandydatami,
ale nie dowodzi bezpieczeństwa wybranej pozycji ani uratowania specjalisty.

## Dlaczego nie użyto granatu

Zapis zawiera 33 sprawdzenia dostępnej, obsługiwanej zdolności granatu i 170
ocen punktów detonacji: 84 odrzucenia zasięgu, 1 trajektorii oraz 85 odrzuceń
bezpieczeństwa wybuchu. Żaden kandydat nie przeszedł tych etapów. Licznik
odrzuceń wartości ataku wynosi 0, więc najnowszej próby nie wyjaśnia nadmierna
ostrożność przy punktowaniu pojedynczego celu.

Przykładowe zapisane powody to `protected_unit_in_blast`,
`protected_unit_near_blast`, `objective_near_blast` oraz
`dangerous_scenery_in_blast`. Szczegółowe powody są migawkami ostatniego
odrzucenia w danym skanie, a nie pełnym histogramem wszystkich punktów.
Nie wynika z nich, że na mapie istniał bezpieczny rzut, który mod pominął.
Nie należy usuwać ochrony sojuszników, cywilów, celów misji ani niebezpiecznej
scenerii na podstawie samego braku granatów.

## Zmiany do kolejnej próby — mission-report-v6

Poprawka wprowadza wspólne `ThreatRiskAtTile` dla wyceny ruchu
i obrony. Ocena obrony stosuje dzięki temu tę samą regułę braku linii
widzenia dla zagrożeń dystansowych. Podział na zagrożenia dystansowe i wręcz
pozostaje zachowany; poprawka nie przypisuje premii osłony przeciw atakom wręcz.

Rewizja zapisu `mission-report-v6` dodaje do podglądu każdego przeciwnika
klasyfikację `melee_only`, odległość i wkład ryzyka bieżącej oraz docelowej pozycji.
Pozwoli to oddzielić wpływ osłony, linii widzenia i dystansu bez wnioskowania
wyłącznie z łącznego wyniku.

Granica 12 pól w obecnej ocenie ryzyka wręcz pozostaje bez zmian do czasu
osobnego sprawdzenia osiągalności ataku. Poprawka nie wyjaśnia wszystkich
późniejszych odwrotów i nie usuwa ograniczeń bezpieczeństwa granatów.
Weryfikacja po otrzymaniu `Development.rar`: 176 testów Python zaliczonych,
bez pominięć; kontrola odwołań do SDK i wszystkie trzy zestawy PowerShell
zaliczone. [Szczegóły weryfikacji SDK](SDK-AUDIT.pl.md). Kompilacja Windows
i wynik następnej próby w grze pozostają niepotwierdzone; zmiana nie gwarantuje
zwycięstwa.


[Instrukcja kompilacji i kolejnej próby](legacy-test.pl.md).
