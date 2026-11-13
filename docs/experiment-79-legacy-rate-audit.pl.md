# #79 — deterministyczny audyt stawek punktacji Legacy (etap danych, bez runtime)

## Po co ten etap

Dostarczone pliki gry/SDK ujawniają rzeczywiste tabele `XComGameState_LadderProgress`,
których nie uwzględnia w pełni obecne `wotc_legacy_observed_v2`.
Różnica w stawkach jest **odrębna** od problemu kompletności
obserwacji i od zgodności natywnej kwalifikacji zdarzeń.

Nowe narzędzie `tools/audit-legacy-ladder-rules.py` wyciąga TYLKO strukturalne
reguły scoringu z prywatnie wskazanych `DefaultLadder.ini` i
`TLE/Config/XComLadder.ini`. Nie publikuje surowych plików,
ścieżek absolutnych, pamięci procesu ani pakietów SDK. Zwraca
tylko SHA256 plików wejściowych, liczbę rekordów, kontrolowane
przykłady różnic oraz jawne luki dowodu. Nie nadpisuje raportu.

Przykład (tylko na własnym komputerze, podstawiając realne ścieżki):

```powershell
py tools/audit-legacy-ladder-rules.py `
  --base "C:\...\XCom2-WarOfTheChosen\XComGame\Config\DefaultLadder.ini" `
  --overlay "C:\...\XCom2-WarOfTheChosen\XComGame\DLC\TLE\Config\XComLadder.ini" `
  --comparison tools/legacy-score-rules.json `
  --output .build/legacy-rate-audit.json
```

Ścieżki w przykładzie są **schematyczne**, wymagają ustalenia lokalnego
położenia `TLE`. Pliki wejściowe są tylko czytane.

## Zweryfikowany zakres rzeczywistych prywatnych configów

| Dane | DefaultLadder.ini | TLE/XComLadder.ini | Razem |
| --- | ---: | ---: | ---: |
| Wiersze `DefaultEnemyScoringTable` | 132 | 2 | 134 |
| Wiersze `DefaultObjectiveScoringTable` | 55 | 61 | 116 |
| Wiersze `DefaultMissionScoringTable` | 20 | 0 | 20 |
| Stawka domyślna przeciwnik/cel/misja, żołnierz | obecna | — | odzyskana |
| `RestartScorePenalty` | — | 1 | odzyskana |

Dodatkowa weryfikacja prywatna: dla TLE brak kolizji
z tymi samymi kluczami enemy `CharacterTemplateName` oraz
objective `(MissionType,TextPoolIndex,GroupID,LineIndex)`
w bazowym pliku.

SHA256 oryginalnych prywatnych konfiguracji (służą tylko do
reprodukcji, **nie jest to udostępnianie plików**):
- DefaultLadder.ini:
  `3cc04039444c8e3d4172e008f2f201c67ef33d202b8e72aa666559519b570a19`
- TLE/XComLadder.ini:
  `366ab8068a32fbd95b8bd860e7ef4df210417fc2ff18f378dad4da4bad442d13`

## Trzy konkretnie potwierdzone rozbieżności

| Przypadek, tura 10 | Stary observed_v2 | Stawka w grze |
| --- | ---: | ---: |
| Zwykły `AdvTrooperM1` | 100 | 1000 |
| Zwykły `AdvPriestM3` | 100 | 2000 |
| Cel `ChallengeTerrorBar`, Pool0/Group1/Line0 | 5000 | 10000 |

Ostatnia kolumna używa wzoru decay znanego z
`observed_v2` na stawkach `StartingPoints/MinPoints/DecreasePerTurn/TurnOffset`;
**natywna granica decay w implementacji C++ nie jest ujawniona**.
Dla wybranej późnej tury minimum jest niezależne od
różnicy o jeden w liczeniu czasu, dzięki czemu porównanie
jest stabilnym kontrprzykładem dla starych kwot.

Pozostałe ważne dane wejściowe obejmują:
`SpawnedPoints`, `ReinforcementPoints`, `DisabledPoints`,
`MinDisabledPoints`, `UninjuredBonus`, `WoundedBonus`,
`RescuedCivilianBonus`, `RestartScorePenalty`.
Parser nie wyrzuca ich przy uproszczeniu.

## Rozmyślnie NIE wykonano w tym etapie

Nie zmieniono `APX_ComparisonScore.uc`, profilu
`wotc_legacy_observed_v2`, `APX_MissionScore`, rejestratora,
rev `mission-report-v33`, natywnych punktów, benchmarku
GasStation ani paczki użytkownika.

`XComGameState_ChallengeScore.AddKillMail`,
`AddIndividualMissionObjectiveComplete` i części awarded
to native funkcje bez ciał w UC. **Zgodność tabel nie dowodzi**:
- kiedy C++ wybiera zwykłą stawkę, `SpawnedPoints`,
  `ReinforcementPoints`, disabled lub kiedy nie przyznaje punktów;
- obsługi restartów i dodatkowych premii;
- kompletności zabitych/ran/uratowanych/eventów celu po wczytaniu,
  po przerwanym HUD lub poza zasięgiem obserwatora;
- tego, że odtworzony wynik z misji bez Ladder ma już
  pełny natywny zakres i oficjalną końcowość.

Wymagane dalsze wdrożenie #79: łączyć zgodne reguły
z native manager getterami tam, gdzie można je
bezpiecznie odczytać, wykrywać i klasyfikować pochodzenie
zdarzeń, ustalać pełny coverage, a dopiero na końcu
nadawać **nowy** profil/revision i ewentualnie status
oficjalny po udowodnieniu parytetu.
Nie przyznawać fałszywych punktów w celu
uzyskania dodatniego wyniku SabotageCC.

Testy `tests/test_legacy_ladder_rules.py` wykonują parser
na izolowanych sztucznych konfiguracjach, sprawdzają
kwoty, multi-field objective key, konfliktowe i
niepełne rekordy, prywatność raportu i negatywne
kontrakty oficjalności. Opcjonalny test prawdziwych
INI jest uruchamiany tylko po ustawieniu
`APX_GAME_LADDER_INI` oraz `APX_TLE_LADDER_INI`.

Ten etap jest **dowodem stawek**, nie dowodem
całego algorytmu punktów Legacy. Nie należy go
scalać jako „oficjalnego licznika” ani mieszać
z osobnymi PR #69 v34 i #70 v35.
