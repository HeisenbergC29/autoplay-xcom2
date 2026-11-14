# #38b — kontrakty natywnego AoE i wąskie rozszerzenie Faceoff

Aktualna baza po integracji #96: `main 2800a84d1433d0e26992b6dddec06b8eb09edd5e`
(`mission-report-v41`). Wcześniejszy audyt rozpoczęto od v40; #97 uwzględnia już
scaloną bazę i marker **`mission-report-v42`**. Runtime Faceoff jest odrębnym
etapem po sekwencyjnym marszu/pamięci; nie zastępuje jego kontroli Controller/
MissionPlanner/ExplorationPlanner. Marker i bieżące testy rewizji są zsynchronizowane.

Użytkownik chce wybierać ofensywne AoE maksymalizując korzyść z wielu
legalnych celów i zachowując bezpieczeństwo sojuszników, cywili,
celów misji i efektów środowiskowych. WOTC Windows make / game:
**NOT RUN**. Bramka [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4)
wstrzymana do ukończenia [#86](PREBUILD-QUEUE.pl.md).

## Macierz natywnych rodzin — 14 listopada 2026

Zweryfikowano bezpośrednio w dostarczonym kompletnym stock WOTC SDK
(podane pliki/linie względne wobec `XComGame/Classes/`, żadnego
prywatnego kodu do publicznego repo):

| Rodzina | Kontrakt stock SDK | Rozstrzygnięcie source |
| --- | --- | --- |
| `ThrowGrenade`, `LaunchGrenade` z `FragGrenade` / `AlienGrenade` | `X2Ability_GrenadierAbilitySet` / `X2Ability_DefaultAbilitySet`, `X2TargetingMethod_Grenade`, natywna trajektoria `XComPrecomputedPath` i `X2AbilityMultiTarget_Radius` | **Wdrożone wcześniej** w `APX_AreaAttackPlanner`: runtime free-aim legalna trajektoria, protected `BlastIsSafe`, `GetDamagePreview` per enemy, single/group score, pre-dispatch revalidation. |
| `Throw/Launch` z `Firebomb`, `GasGrenade`, `AcidGrenade`, `FlashbangGrenade`, `SmokeGrenade`, `EMPGrenade`, `ProximityMine`, inne granaty | `X2Item_DefaultGrenades.uc:186–1269`: różne efekty fire/poison/acid/EMP, buff/debuff, mines/triggers i target immunities | **UNSUPPORTED** w obecnym grenade solver: nie wystarcza suma obrażeń `ApplyWeaponDamage`; trzeba source-safe native persistent effects/target immunity/world delta i specyficzne warunki zapalnika. `GetSupportedGrenade` nadal fail-closed. |
| `Faceoff` | `X2Ability_SharpshooterAbilitySet.uc:989–1049`: native `X2AbilityMultiTarget_AllUnits`, `bUseAbilitySourceAsPrimaryTarget=true`, `bAcceptEnemyUnits=true`, osobne `X2Effect_ApplyWeaponDamage`, `X2AbilityToHitCalc_StandardAim`, **nie free-aim/cursor** | **Nowy, ograniczony source consumer** `APX_NativeMultiTarget.ScoreFaceoff`, w `APX_CombatPlanner.ChooseAction`. Tylko aktualne `AA_Success`, native `AvailableTargets`, primary hostile + co najmniej 1 additional enemy, ograniczony kontrakt pistoletu bez extra ammo/upgrade/applied bonus effects i wszystkie widoczne hostile. Innych rodzin nie włączono. |
| `RocketLauncher`, `BlasterLauncher` | `X2Ability_HeavyWeapons.uc:23–85,314–377`: `X2AbilityTarget_Cursor` + `X2AbilityMultiTarget_Radius`, ale **odrębne** `X2TargetingMethod_RocketLauncher` / `X2TargetingMethod_BlasterLauncher`, specjalne native projectile / guided geometry | **UNSUPPORTED**: `X2TargetingMethod_Grenade` i jego `ComputeImpact` nie uzasadniają identycznej trajektorii/impact ani splash; wymagany odrębny native trajectory i pełny protected footprint/revalidation. |
| `ShredderGun`, `ShredstormCannon`, `Flamethrower` / Mk2 | `X2Ability_HeavyWeapons.uc:87–314`: `X2TargetingMethod_Cone`, `X2AbilityMultiTarget_Cone`, flamethrower dodatkowo `X2Effect_ApplyFireToWorld` | **UNSUPPORTED**: cone sample nie jest radius/cursor; wymagane native full cone geometry/LOS, środowisko/fire i friendly/civilian/objective/chain collateral. |
| `PlasmaBlaster`, `NullLance` | `X2Ability_HeavyWeapons.uc:380–444`, `X2Ability_PsiOperativeAbilitySet.uc:909–982`: `X2TargetingMethod_Line` + `X2AbilityMultiTarget_Line` | **UNSUPPORTED**: brak per-target full native line/penetration/cover geometry + source-safe cursor position. Nie przechodzi do Faceoff/grenade. |
| `SaturationFire` | `X2Ability_GrenadierAbilitySet.uc:665–752`: `X2TargetingMethod_Cone`, native conditional ammo i `X2Effect_ApplyDirectionalWorldDamage`, template może obejmować friendly | **UNSUPPORTED**: potrzebna pełna geometria kierunkowa, realny world damage i ochrona objective/sojuszników przed emisją. |
| `VoidRift` | `X2Ability_PsiOperativeAbilitySet.uc:985–1069`: native `X2TargetingMethod_VoidRift`, radius z `bIgnoreBlockingCover`, damage + `X2Effect_TriggerEvent` `VoidRiftInsanity` | **UNSUPPORTED**: wpływ losowego trigger/insanity, LOS i multiple statuses nie jest równoważny grenade safe radius. |
| `Fuse` | `X2Ability_PsiOperativeAbilitySet.uc:708–812`: single unit with explosive, secondary damage preview and environmental blast | **UNSUPPORTED**: bez natywnego dowodu rzeczywistego triggera i pełnej propagacji blast/child/events nie uznajemy potencjalnej detonacji za pewny, bezpieczny AoE. |
| `KillZone` | `X2Ability_SharpshooterAbilitySet.uc:786–884`: cone `X2Effect_ReserveActionPoints` + `X2Effect_MarkValidActivationTiles`, native reaction `KillZoneShot` dopiero później | **DEFENSIVE PREPARATION, NOT DAMAGE AOE NOW**. Nie wolno przypisać natywnych przyszłych trafień do bieżącej decyzji albo udawać nowego `AA_Success` na wroga. |
| `Volt` i burst shots | `X2AbilityMultiTarget_Volt`, `X2AbilityMultiTarget_BurstFire` | Obsługiwane dotychczas w dedykowanych gałęziach `APX_CombatPlanner`. Nie zmienia się ich w tej pracy, bo nie stanowią wolnego kursora AoE. |

## Dokładny nowy kontrakt Faceoff

`APX_CombatPlanner.ChooseAction` wciąż zaczyna od własnego
`GetGameRulesCache_Unit`, `AA_Success`, `bInputTriggered`,
`!bFreeAim`, realnego `Ability.OwnerStateObject` oraz
`GetAllVisibleEnemiesForPlayer`. Nowa gałąź tylko dla nazwy
`Faceoff` działa **przed** ogólnym wykluczeniem
`AbilityMultiTargetStyle`; inne multi pozostają nieobsługiwane.

`APX_NativeMultiTarget.SupportedFaceoff` sprawdza dokładny
stock `AllUnits` enemy-relative-to-shooter contract, zaznaczone
enemy only, excluded friendly i neutral, brak random subset;
**natywny cel główny to pierwszy wróg, nie strzelec**.
`Faceoff_BuildVisualization` w `X2Ability_SharpshooterAbilitySet.uc:1122–1130`
jawnie wykonuje pierwszy strzał w `PrimaryTarget`, potem pozostałe.
**Ważna korekta kontraktu:** `Faceoff()` nie ustawia jawnie
`Template.TargetingMethod`, ale `X2AbilityTemplate.uc:987`
ustawia domyślne `class'X2TargetingMethod_TopDown'`; nie jest
to `none` i nie wolno z tego powodu odrzucać zdolności.
Weryfikujemy tę dokładną klasę, a nie nieuprawniony
`X2TargetingMethod_Grenade` lub inne free-aim cursory.
LEAD zawęził dodatkowo sprawdzany kontrakt: dokładna klasa
`X2AbilityToHitCalc_StandardAim` z niezależnymi multi-hit rolls
(`bOnlyMultiHitWithSuccess=false`) i dokładny `X2AbilityTarget_Single`,
jak `default.SimpleSingleTarget` z `X2Ability.uc:1686–1689`.
Oba kanały muszą zawierać dokładny `X2Effect_ApplyWeaponDamage`,
bez podklasy, `bExplosiveDamage` i jawnego `EnvironmentalDamageAmount`.
Ten ostatni ma w stock efektu domyślną wartość int0; nie jest tym samym
co `iEnvironmentDamage` samej broni.

Źródłowa broń musi mieć `X2WeaponTemplate.WeaponCat='pistol'`.
Nie dopuszczamy loaded/source ammo, zainstalowanych weapon upgrades
ani niepustych `BonusWeaponEffects`, gdy zdolność stosuje tę listę.
Liczba upgrade jest odczytywana z `GetMyWeaponUpgradeTemplateNames`
(`XComGameState_Item.uc:647–650`), który tylko zwraca zapisane nazwy,
bez getteru uzupełniającego cache upgrade templates. To konserwatywny
podzbiór: również nieszkodliwy aim-only upgrade wyłącza tę gałąź.
Sprawdzenia nie wykrywają każdej możliwej modyfikacji template albo
niestandardowego kodu innego moda; nie są certyfikatem dowolnego Faceoff.

`ScoreFaceoff` wymaga prawdziwego `PrimaryTarget` będącego wrogiem
oraz 1–15 `AvailableTarget.AdditionalTargets` — w sumie
2–16 **unikalnych** celów w bieżącej natywnej akcji.
**Każdy (także PrimaryTarget)** musi być aktualnie widocznym hostile, żywym, nie NPC
objective/civilian, nie wcześniej kontrolowanym oddziałem XCOM.
W razie choć jednego wyjątku **cała** akcja jest odrzucana.
Nie przeszukujemy wszystkich ukrytych jednostek ani nie tworzymy
przyszłych targetów. Dla każdego prawidłowego enemy:
read-only kopia native `AvailableTarget` do `GetShotBreakdown`
(tylko *preview* hit probability), właściwy osobny damage effect
`GetDamagePreview(..., true)` dla pierwotnego wroga oraz
`GetDamagePreview(..., false)` dla dodatkowych, korekta pancerza i bieżącego
HP/Shield, `APX_CombatPlanner.ScoreDamage`. `ScoreFaceoffOutcome`
sumuje oczekiwany potencjał co najmniej dwóch **użytecznie
trafialnych** wrogów (każdy wymaga natywnego hit chance ≥
`APX_CombatPlanner.MinimumHitChance` i dodatniej maksymalnej
prognozy obrażeń); wrogów z 0% / zerowym damage wciąż
sprawdza pod kątem collateral, ale nie powiększa za nich
wyniku. Funkcja pobiera
niewielki koszt cooldown/zużycia AP (12) oraz maksymalnie 12
premii za **wysoką szansę kończenia**, nigdy nazwaną
gwarantowanym killem. Wynik bierze udział w standardowym
porównaniu z pojedynczym shot/medic/rescue/goal.

Nie generujemy `AvailableAction`/preview locations, nie
przechodzimy przez globalny grenade `PRECOMPUTEDPATH` ani
nie zmieniamy AP, hit RNG lub native WOTC damage.
Controller nadal wysyła **oryginalny** `AvailableAction` i
`TargetIndex`, a silnik weryfikuje ability przy dispatch.

**Ograniczenie źródłowe**: `X2AbilityMultiTarget_AllUnits.GetMultiTargetOptions`
jest `native`; pełna treść jego implementacji C++ nie
występuje w dostępnym SDK `.uc`. Nie utożsamiamy
`bUseAbilitySourceAsPrimaryTarget` z oddaniem strzału w strzelca:
native stock visualization dowodzi strzału w osobnego pierwszego
wroga. Jeśli prawdziwa bieżąca `AvailableTargets` nie zawiera
legalnego, obecnie widocznego pierwszego wroga i co najmniej
jednego kolejnego wroga, ta gałąź pozostanie nieaktywna. Stock `Faceoff`
pozwala na bonus weapon effects; nowy guard odrzuca jawnie stosowany
niepusty kanał oraz każdą zainstalowaną weapon upgrade. Nie jest to
pełny solver wszystkich pasywnych efektów lub innego modowanego kodu.
Nie odrzucamy zwykłych pistoletów za ich bazowe `iEnvironmentDamage`:
`X2Effect_ApplyWeaponDamage.uc:214–235` może dodać bazowe obrażenia
środowiska broni nawet przy jawnym EnvironmentalDamageAmount=0.
Bezpośrednia lista trafianych jednostek jest sprawdzona, lecz zniszczenie
osłony pociskiem i dalsze chain reactions **nie są certyfikowane**,
tak samo jak w istniejącym wyborze pojedynczego strzału. Nie nazywać
tej gałęzi pełnym collateral-safe solverem ani nie przenosić tego
ograniczenia na granaty przez usunięcie ich dotychczasowych guardów.

## Wtórne wybuchy — konkretny brak native dowodu

`XComDestructibleActor_Action_RadialDamage.GetBlastExtents`
zawiera bounds eventu, `XComDestructibleActor.GetRadialDamageTiles`
zweryfikowane przy istniejącym zdarzeniu, a
`GetDestroyedDamagePreview` potrafi policzyć nominalne
`UnitDamage` w UI. To **nie wystarcza**, by potwierdzić,
że jeden zwykły strzał/granat zabije obiekt o rzeczywistym
`Health`, że system wyzwoli wszystkie potomne
`DestroyedEvents`, w jakiej kolejności i jaki
footprint/effect dotknie friendly/civilian/objective.
W projekcie istnieje `APX_AreaAttackPlanner.HasDangerousScenery`:
`HasRadialDamage || bDestroysSurroundingArea ||
AffectedChildren.Length>0`. Te same bazowe i pre-dispatch
guards **pozostają aktywne**. Każdy solver przyszłych
secondary blasts musiałby mieć zweryfikowane native
trigger+damage thresholds, health/support, event sequence,
transitive bounded child graph, tile extents i pełny
protected object footprint; inaczej UNKNOWN i
fail closed. Brak tych danych nie jest ukończoną
implementacją `wysadzania samochodów`.

## Testy

`tests/test_native_multitarget_38b.py` uruchamia
prawdziwą czystą funkcję UC `ScoreFaceoffOutcome`:
0/1/2/3/4/17 targetów, wiele mocnych kończeń,
nieopłacalne ataki, limit bonusu. Source contracts sprawdzają
wybrany stock kontrakt klas/efektów/broni, native hit/weapon previews,
pełny weryfikowany current-only target list, brak
dodania nowych `AvailableAction`, zachowane
`BlastIsSafe/HasDangerousScenery`.
Prywatny SDK test jest opcjonalny i jawnie SKIP
w publicznym CI. Windows/game acceptance z późniejszej
jednej rundy: natywne `Faceoff` 0/1/2/3 wrogów,
pełny aktualny target list, hit chance oraz
prawdziwie zaakceptowane wywołanie; przypadek
mindcontrolled ally/civilian/mission objective, custom
ammo, brak AP/cooldown i alternatywne single shot.
Osobne próby rocket/cone/line/psi/explosive chain
pozostają **DEFERRED**, nie sygnalizujemy
fikcyjnego success.
