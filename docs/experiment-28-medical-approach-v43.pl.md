# #28 — pilne natywne leczenie / detoks i bezpieczne podejście (v43)

Baza: `main 2f0ba0c514bcdb119f07ae7586b8ec3795773bf0`, runtime
`mission-report-v42`. HELPER branch `helper/28-urgent-medical-approach-v43`,
nowy marker `mission-report-v43`. Jedyny pozostały wcześniej READY punkt
[#86](PREBUILD-QUEUE.pl.md); [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4)
**BLOCKED** do końcowego LEAD review/integracji. Native Windows make i gra:
**NOT RUN**. Ta zmiana nie certyfikuje wcześniejszego scenariusza v19
GasStation, gdzie legalność i bezpieczna trasa nie były potwierdzone.

## Dowody źródłowe — dostarczony prywatny WOTC SDK

- `X2Ability_DefaultAbilitySet.uc:2504–2584`:
  `MedikitHeal/NanoMedikitHeal` są `X2AbilityTarget_Single`
  z `OnlyIncludeTargetsInsideWeaponRange=true`; koszt 1 ammo +
  1 AP; `X2Effect_ApplyMedikitHeal` i rzeczywisty
  `X2Effect_RemoveEffectsByDamageType.DamageTypesToRemove` z
  `MedikitHealEffectTypes`. `ExcludeFullHealth=true`
  w target condition **nie odrzuca** pacjenta, gdy ma faktycznie
  usuwalny trwały typ obrażeń (źródło:
  `X2Condition_UnitProperty.uc:28`).
- `X2Ability_SpecialistAbilitySet.uc:557–638`:
  `GremlinHeal` zużywa 1 AP i 1 `X2AbilityCost_Charges`
  (`SharedAbilityCharges` ze `GremlinStabilize`),
  `SingleTargetWithSelf`, `ExcludeFullHealth` i
  `X2Effect_RemoveEffectsByDamageType` przez
  `RemoveAllEffectsByDamageType()`. Źródła nie dowodzą
  identycznej geometrii co lokalny medikit: nie narzucamy
  urojonego zasięgu medikitu zdalnemu Gremlin.
- `XComGameState_Ability.uc:111–157`: natywna
  `CanActivateAbility` weryfikuje aktualny shooter/cooldown,
  realne `CanAfford` (ammo/charges/AP) i shooter conditions;
  **nie** wymaga, by dowolny pacjent był już obecnie w zasięgu.
  `X2AbilityTemplate.CheckTargetConditions` sprawdza
  natywne statusy aktualnego pacjenta.
  `X2AbilityTarget_Single.uc:20–22` udostępnia
  `GetHitRange` (−1 = brak limitu) oraz natywne
  `ValidatePrimaryTargetOptionFromRemoteLocation` użyte
  **wyłącznie jako planistyczny test** miejsca, nie jako
  po-ruchowy `AA_Success`.
- `XComGameState_Unit.uc:7670–7675`: `IsPoisoned`,
  `IsUnitAffectedByDamageType`; drugi warunek odróżnia
  status rzeczywiście możliwy do usunięcia przez efekty
  tej konkretnej zdolności od samej nazwy trucizny.
  `X2Effect_RemoveEffectsByDamageType.uc:5–46` potwierdza,
  że effect jest relewantny tylko gdy faktyczny unit
  posiada typ zawarty w `DamageTypesToRemove`.
- `XComTacticalController.CreatePathDataForPathTiles`,
  `X2AbilityCost_ActionPoints.ApplyCost` i aktualny
  `X2ReachableTilesCache` pozostają właścicielami
  native path/AP. Nie kopiujemy jednostki, nie przesuwamy
  historii w celu testu ani nie zakładamy arbitrary
  2×Mobility dash.

## Co wdrożono

**1. Detoks, także przy pełnym HP:** dotychczasowe
`APX_CombatPlanner.ScoreMedical` zachowuje swój kontrakt:
bleeding+stabilize=400, zwykłe rany są punktowane wg HP,
pełne HP bez potrzeby=−10000. W gałęzi już
**natywnie legalnego** `AvailableAction AA_Success`
`ScoreUsefulHealing` dodaje wartość tylko, gdy bieżący
`X2Effect_RemoveEffectsByDamageType` z konkretnej
zdolności faktycznie odpowiada
`TargetUnit.IsUnitAffectedByDamageType`.
Poisoned bez relevantu NIE podnosi punktacji. Nie wolno
przywrócić leczenia martwego/krwawiącego, obcego
lub kontrolowanego wroga przez sam efekt.
`APX_ActionEconomy.ScoreWithRetainedAttack` nadal
zarządza porównaniem z zachowanym legalnym atakiem.

**2. Pozycjonowanie niekrwawiącego:** nowy
`APX_MedicalApproach.uc` posiada jawne kontrakty
własnego żywego pacjenta, realnie zainstalowanej zdolności,
statusu i aktualnych kosztów. Natywna `AA_NoTargets`
sama nie dowodzi braku medikitu — `CanActivateAbility`
może być legalne, a `CheckTargetConditions` pacjenta
pomyślne, choć zasięg/LOS nie pozwalają leczyć z
obecnego pola. **Jeżeli obecna natywna lista zawiera
jakiekolwiek sensowne leczenie własnej drużyny, planner
nie przemieszcza medyka zamiast wykonania tej akcji.**
Gremlin z nielimitowanym `GetHitRange=-1`
nie otrzymuje fikcyjnego celu podejścia;
może natomiast wykonać normalną akcję z aktualnej
natywnej listy (w CombatPlanner).

**3. Jeden bezpieczny blue do prawdopodobnie
legalnego pola:** `APX_MissionPlanner.ChooseMedicalMove`
rozważa **wyłącznie** pacjenta z HP ≤45% albo
poison+rzeczywiście usuwalnym typem obrażeń.
Nie wybiera już krwawiących, nieprzytomnych,
nieswoich, martwych, przenoszonych ani kosmetycznych
jednostek. Jeśli pacjent nadal stoi w źródłowo
rozpoznanej chmurze trucizny, nie traktuje samego
detoksu jako trwałego rozwiązania: pierwszeństwo
ma jego `ChoosePoisonEscape`; nadal możliwe jest
pilne leczenie bardzo niskiego HP.

Rzeczywisty medyk ma ≥2 AP standardowe, natywne
`StandardMove`, prawdziwe aktualne warunki
strzelca/cooldown/ammo/charges; po symulowanym
zużyciu **dokładnie kosztu jednego BLUE** konkretna
heal nadal spełnia `CanAttackWithActionPoints`.
Każdy endpoint musi być z rzeczywistego native
`XGUnit.m_kReachableTilesCache`:
`IsTileReachable`, `GetPathCostToTile <= GetMobility`,
`BuildPathToTile` z kontrolą początku/końca;
docelowe `X2AbilityTarget_Single` ma skończony
native hit-range i przyjmuje pacjenta z propozycji
`ValidatePrimaryTargetOptionFromRemoteLocation`.

Cała trasa, maksymalnie 48 kafli, musi spełnić:
znane i widziane własnej drużynie tiles,
brak `APX_HazardKnowledge.HasBlockingHazard`,
`IsSupportedAdvanceStep/Destination`,
`IsSupportedCombatDestination`, natywne
`APX_ConcealmentPlanner.InspectPathRisk`,
`APX_ExplosiveCoverKnowledge.InspectRiskAtTile`
(wspólny budżet),
`ExposureRisk(tile) <= current+3`
**dla każdego tile**, a obszarowe skupienie
oddziału zmniejsza ranking `SquadPositionScore`.
Skan jest skończony: max 128 weryfikacji unit,
16 pacjentów, 80 iteracji zdolności, 64
kandydaty pól/pacjenta i 48 pól/ścieżkę.
Wyczerpany budżet/nieznane wzorce
**odrzucają** próby, nie zatwierdzają ryzyka.

`HasActiveMissionDeadline`, aktywne bleeding rescue,
evac, własna ucieczka z trucizny oraz specjalny
`SabotageTransmitter` mają priorytet;
konkurencyjne legalne strzały, normalne objective
i wcześniejszy ratunek nadal są porównywane
w istniejącym Controller. Candidate oznaczony
`medical_approach_candidate` nie wykonuje
w sobie leczenia. `CanUseMove` i zwykły
`GameStateMoveUnitSingle` muszą zatwierdzić
faktyczny native ruch, po którym następny cykl
re-cachuje wszystkie `AvailableActions/Targets`
z rzeczywistego aktualnego `UnitState`.
Nie ma mutacji natywnego świata, ukrytych AP,
fabrykowanych celów lub gwarancji, że z nowej
pozycji medikit zostanie użyty.

## Ograniczenia / test w jednej wspólnej paczce po #86

- **Gremlin unlimited-range oraz modyfikowane
  teleport/area heal i revival:** brak dowodu
  pola docelowego dla nawigacji → nie generujemy
  osobnej trasy; obecnie realnie legalne działania
  nadal są obsługiwane. Zdalny heal może być
  użyty bez przemieszczania się.
- **Dojście wymagające więcej niż jednego BLUE:**
  nie jest rozbijane na wieloturowy plan z
  rezerwacją zasobu, ponieważ taki bieg
  nie gwarantuje przeżycia i legalności
  przyszłego `AA_Success`. Zostaje zwykły
  bezpieczny ruch i priorytety misji.
- Native `ValidatePrimaryTargetOptionFromRemoteLocation`
  nie wykonuje `GetGameRulesCache_Unit` po
  przyszłym ruchu. Wynik to kandydat
  do ponownej oceny, NIE potwierdzona akcja
  heal. LOS/protokół GREMLIN/efekty
  zdarzenia/civilian/wybuch wrogów w przyszłej
  turze pozostają nieznane. Nie przewidujemy
  przeciwniczych przyszłych ruchów ani RNG.
- Do łącznej kontrolowanej próbki WOTC po
  końcowym LEAD review: HP=1+poison
  poza chmurą, HP=max+usuwalny poison,
  HP=max bez typu efektu, bleeding/Unconscious,
  Medikit ammo 0, Gremlin shared charges 0,
  jedynie 1 AP lub specjalne AP, obecny
  AA_Success dla innego pacjenta, native LOS
  z i bez move, zbyt daleki target, błędny
  footprint/collateral/explosive cover,
  FOW=false i multi-tile, timer/evac/X4,
  aktualny combat i brak kolejnego
  dostępnego celu heal po ruchu.
  Dopiero realna misja wygrana autonomicznie
  z wszystkimi zadaniami i znanym finalnym
  native score>0 spełnia projektowy PASS.

Testy `tests/test_medical_approach_v43.py`
wykonują rzeczywiste funkcje UC
`ScoreUsefulHealing` i `ScoreMedicalApproach`,
kontrolują natywne warunki celu, current AA,
ap cost i whole-route source contracts.
Dostarczony SDK sprawdzany prywatnie; CI
z pominięciem opcjonalnego private SDK testu
nie jest natywną kompilacją WOTC.
