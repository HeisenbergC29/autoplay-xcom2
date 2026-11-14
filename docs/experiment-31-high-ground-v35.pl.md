# #31 P2a — bezpieczna ocena wysokiego stanowiska strzeleckiego (v35)

## Zadanie i pochodzenie reguł

Użytkownik zapytał o przewagę wysokości XCOM 2: War of the Chosen
i zastosowanie jej do autoplay. W stock
`X2TacticalGameRuleset.uc` są publiczne
`UnitHeightAdvantage` (standardowo3 polaZ)
i `UnitHeightAdvantageBonus` (standardowo+20 Aim).
`XComGameState_Unit.HasHeightAdvantageOver(Target,true)`
uwzględnia też `GetHeightAdvantageBonusZ` dla specjalnej
wysokości jednostki. `X2AbilityToHitCalc_StandardAim`
dolicza bonus do odpowiedniego legalnego ranged ataku, bez
domyślnej dodatkowej premii `Defense`. Mody mogą
nadpisywać szczególne sytuacje, a wynik po przemieszczeniu
nie jest dostępnym gotowym native `ShotBreakdown`.

Zweryfikowane źródła:
- [X2TacticalGameRuleset.uc](https://github.com/X2CommunityCore/X2WOTCCommunityHighlander/blob/master/X2WOTCCommunityHighlander/Src/XComGame/Classes/X2TacticalGameRuleset.uc)
- [XComGameState_Unit.uc](https://github.com/X2CommunityCore/X2WOTCCommunityHighlander/blob/master/X2WOTCCommunityHighlander/Src/XComGame/Classes/XComGameState_Unit.uc)
- [X2AbilityToHitCalc_StandardAim.uc](https://github.com/X2CommunityCore/X2WOTCCommunityHighlander/blob/master/X2WOTCCommunityHighlander/Src/XComGame/Classes/X2AbilityToHitCalc_StandardAim.uc)

## Konkretna zmiana w #31

Baza v33 z #56 PR #69. Nowy PR P2a jest **stacked na #69**,
a nie bezpośrednio na v32, żeby nie rozminąć znaczników
rejestratora. Nie zmienia to buildu v32 testowanego przez użytkownika.

1. `APX_MissionPlanner.OffensivePositionScore` nie używa
już każdego dodatniego `Tile.Z > Enemy.Z` jako przewagi
wysokości. Ocenia prawdziwy próg
`Tile.Z + UnitState.GetHeightAdvantageBonusZ()
>= EnemyTile.Z + Max(1, stock UnitHeightAdvantage)`.
Dotychczasowe +5 to **użyteczność stanowiska**,
nie dodatkowe +5 do Aim.
2. `APX_RepositionPlanner.GatherForecasts` dla już legalnych,
native `AA_Success`, single-target, basic
`StandardShot/PistolStandardShot` zapamiętuje, czy bieżący
`UnitState.HasHeightAdvantageOver(Target,true)`.
Natywny `GetShotBreakdown` dla obecnego miejsca
zawsze pozostaje bazą.
3. Dopuszczamy **tylko wyższe** i natywnie osiągalne w niebieskim
ruchu tile, z ograniczeniem dodatniej różnicy Z
`MaxElevationGainTiles=6` (1–8 w runtime).
Dla `ProjectedHeightAimBonus` liczy się jedynie przekroczenie
stock progu z miejsca bez natywnej przewagi na miejsce
z geometrycznie prawdopodobną nową przewagą.
Domyślny szacowany przyrost to `max(0,+20-5)=+15 Aim`.
Pięć punktów to jawny margines niepewności, nie
zmiana oryginalnej premii gry. Nie ma drugiego dodawania,
jeśli natywny atak już miał przewagę wysokości.
4. Suma `RangeDelta + CoverRecovery + HeightEstimate`
pozostaje w starym clampie **−35..+35**, a
`ProjectedHitChance <=95`. `MoveAndShotScore` nadal
wymaga rzeczywistego wzrostu >=12pp i wartości ataku>=8,
>=2 AP, `CandidateRisk <= CurrentRisk` i opłaca
dodatkowy ruch.
5. Bezwarunkowo pozostają native
`GetVisibilityInfoFromRemoteLocation`,
`EvaluateConditions`, single-target remote validation,
`GetAllPathableTiles`, mobility/path-cost, pełna
trasa, hazards, osłony, zakaz samotnego wejścia na
niepodparty dach (`IsSupportedCombatDestination`),
`IsSupportedAdvanceStep`, cohesion i ryzyko.
Brak udawanej zmiany `UnitState.TileLocation`,
brak `ModifyStateObject` lub własnego hit roll.
Atak po prawdziwym ruchu ponownie sprawdza
obecny natywny cache. Umiejętności melee, AoE, reakcje OW,
gwarantowane trafienia, multi-target, ruler actions
nie wchodzą w prognozę.
6. INI ma odwracalne
`EnableElevatedShotForecast=true`,
`MaxElevationGainTiles=6`, `HeightForecastDiscount=5`.
`false` przywraca dotychczasowe ograniczenie
do tego samego poziomu Z.

## Ograniczenia i test

`tests/test_high_ground_forecast.py` wykonuje rzeczywisty
czysty helper numeryczny UnrealScript: próg3, brak podwójnej
premii, brak bonusu na niższej/podobnej wysokości, discount,
max95, kontekst natywnej zdalnej wizji i pełnej trasy.
`tests/test_offensive_reposition.py` nadal bada
range/cover/native AP/stock danger. SDK testy dodatkowo
sprawdzają istniejące klasy/fieldy (jeśli prywatne źródła
zostały dostarczone). To nie jest natywna kompilacja
ani dowód zachowania gry.

Ponieważ mobilność, dojścia po drabinach, wysokość
specjalnych jednostek, zasłony, inne efekty i modowane
overrides mogą zmieniać wynik, +15 pozostaje
**prognozą**, a nie oficjalnym preview. Tylko faktyczna
późniejsza akcja jest native-legal. Nowy marker
`mission-report-v35` pozwala oddzielić ten wariant
od v32/v33.

W następnym teście GasStation/diff2 po review LEAD
porównać liczbę wybranych ruchów do wyższych stanowisk,
realny Aim%/trafienia po ruchu, rzeczywiste native
OverwatchShot, rozpad formacji, przeżywalność,
natywne zwycięstwo i **znane oficjalne końcowe punkty>0**.
Nie deklarować bonusu do obrony/ataku melee,
ukończenia synchronizacji OW ani zwycięstwa bez logów.

Dalszy #31 P2b: legalnie skoordynowane 2–3
Overwatch oraz jeden opener, ograniczone do aktualnie
zweryfikowanego AIGroup, bez gwarancji reakcji
na activation scamper. Nadal otwarte #56 P1b:
bezpieczny własny approach i przeżycie Sweep.
