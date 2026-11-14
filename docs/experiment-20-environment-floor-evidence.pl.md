# #20: audyt ScythingClaws, EnvironmentDamage, podpór i upadków (WOTC SDK)

Stan: **SOURCE AUDIT COMPLETE / FLOOR-COLLAPSE FORECAST UNSUPPORTED**.
Zakres zamkniętej kolejki [#86](PREBUILD-QUEUE.pl.md), baza
`main c833dcc4189a84b90b169803a2531889e9c48fb4`.
Ten przegląd **nie zmienia runtime**, reguł walki, punktacji, ani
`mission-report-v38`. WOTC Windows make/game nowych zmian:
**NOT RUN**. Brak podstaw do stwierdzenia, że historyczna śmierć
snajpera w GasStation v25 została spowodowana konkretnym autem,
bezpośrednio ciosem Facelessa lub zawaleniem podłogi.

## 1. Co naprawdę wynika ze źródeł

Źródła to kompletne, prywatnie dostarczone WOTC SDK. Poniżej tylko
ścieżki względne i pochodne ustalenia — nie kopiować plików ani assetów
do publicznego repozytorium.

| Kontrakt stock | Zweryfikowana treść | Czego nie dowodzi |
| --- | --- | --- |
| `XComGame/Classes/X2Ability_Faceless.uc:71–149,402–482` | `ScythingClaws` i MP definiują cone melee oraz `X2Effect_ApplyWeaponDamage.EnvironmentalDamageAmount=AREA_MELEE_ENVIRONMENT_DAMAGE`; używają target cursor/range/multi-target. | Że przyszły atak zostanie wybrany, gdzie będzie skierowany, czy zniszczy podporę. |
| `XComGame/Classes/X2Effect_ApplyWeaponDamage.uc:182–246` | Przy znanej lokalizacji trafienia oraz spełnieniu natywnych warunków tworzone są obrażenia środowiska, uwzględniające promień/kształt i źródło. | Przyszłego `TargetLocations`, projekcji obrażeń na aktualne HP każdego fragmentu konstrukcji ani przyszłej losowości. |
| `XComGame/Classes/XComGameState_EnvironmentDamage.uc:16–71` | Po wykonanym zdarzeniu zapisuje DamageAmount/HitLocation/HitLocationTile/DamageTiles, DamageCause/Source, DamageActors/DestroyedActors i inne metadane; `OnStateSubmitted` emituje `OnEnvironmentalDamage`. `CausedDestruction` jest native. | Czy nienaruszony dach ma wytrzymałość pozwalającą przeżyć przyszły cios, ani jakie `FractureTiles` powstaną, zanim silnik przeliczy destrukcję. |
| `XComGame/Classes/XComWorldData.uc:779–788` | Obserwacyjne `IsFloorTileAndValidDestination`, `GetFloorTileForPosition`, `TileHasFloorThatIsDestructible` dostępne w UC. | `TileHasFloorThatIsDestructible=true` nie oznacza: „ta podłoga upadnie od następnego melee”. Nie zapewnia HP fragmentów, nośności zależnej od sąsiednich podpór ani sekwencji pęknięć. |
| `XComGame/Classes/XComGameStateContext_Falling.uc:15–115` | Dopiero rzeczywisty context ma `FallingUnit`, `StartLocation`, `LandingLocations`, `EndingLocations`; stosuje obrażenia od wysokości (z wyjątkami odporności) i może generować wtórne EnvironmentDamage. | Że przed wykonaniem wrogiej akcji da się odtworzyć `EndingLocations` bez symulowania przyszłej destrukcji. |
| `XComGame/Classes/X2Action_UnitFalling.uc:50–97` | Odtwarzanie/visualization korzysta z już istniejącego `FallingContext.AssociatedState`. | Nie daje „bezpiecznego” prewencyjnego podglądu przyszłego miejsca spadku. |

W `XComWorldData.uc:557` istnieje deklaracja natywnego mechanizmu
`GetFallingFloor(FTTile, ResistiveHealth)` w części C++/native, ale
nie ma dostępnego w UC publicznego, niemutującego odpowiednika,
który dla dowolnej nieodbytej akcji wroga wyliczałby certyfikowaną
stabilność piętra lub cały łańcuch zniszczeń. Wywoływanie
mutujących przewidywaczy obrażeń, zmiana historii lub sztuczne
rozstrzygnięcie ataku wroga byłoby niedozwolone.

## 2. Co już chroni mod

`APX_ExplosiveCoverKnowledge.uc` ma realny, ograniczony model
`XComDestructibleActor_Action_RadialDamage.GetBlastExtents`,
`RadialEvent.UnitDamage`, stanu destrukcji i obecnych znanych
zagrożeń melee (w tym korekty #54/#55). Nie liczy jednak fizycznej
nośności wszystkich podłóg ani przyszłych `EnvironmentDamage`.
`APX_HazardKnowledge.uc` filtruje istniejące ogień/kwas/chmury
w ramach natywnych ograniczeń widoczności. `APX_MissionPlanner`
zachowuje legalne reachable cache/path/AP, osłonę, wsparcie,
eksplozje i soft formation-AoE z #20. To **istniejące zabezpieczenia**,
nie dowód pełnego przewidywania zawaleń.

## 3. Decyzja projektowa po audycie

**Nie implementować obecnie** twardego zakazu dachów, karania
każdego pola nad parterem ani modelu „100% zawalenia”.
Sama możliwość zniszczenia płyt podłogowych i geometria cone
bez rzeczywistej odporności podpór/celu przyszłego ataku dałaby
fałszywe pewne predykcje. W szczególności brak danych o
`ScythingClaws` jako aktualnie wybranej wrogiej akcji (a odczyt
ukrytych AP/cooldown/intent jest zakazany) oznacza, że statyczna
ocena „ten przeciwnik ma zdolność” jest najwyżej heurystyką,
nie dowodem kierunku czy rezultatu uderzenia. Istniejąca
legalna droga na dach i awaryjny fallback pozostają dostępne.

**Precyzyjny brakujący dowód** do ewentualnego bezpiecznego
rozszerzenia:
1. Na konkretnym asset/map tile: obserwacyjny, dostępny w UC
   kontrakt rzeczywistego HP/odporności **podpory oraz segmentów
   zależnych**, z aktualnym stanem uszkodzeń i wiarygodną mapą
   relacji konstrukcyjnych, bez mutacji świata.
2. Z rzeczywistej próby: wspólna historia `ScythingClaws`
   (SourceObject, target locations i wybrana legalna akcja),
   zapisane `XComGameState_EnvironmentDamage` (cause/source,
   tiles, amount, actual destroyed actors), następnie
   `XComGameStateContext_Falling` z FallingUnit, lokalizacjami
   start/koniec, wynikami HP i native end. To pozwoli oddzielić
   potencjalne zawalenie od bezpośrednich melee, granatu,
   eksplozji auta i wtórnych pożarów. Sama korelacja Z5→Z1
   nie ustanawia jedynej przyczyny.
3. Dla nowego predyktora: niezależne porównanie prognozowanej
   destrukcji z prawdziwymi native wynikami dla kilku typów
   floor assets, pięter i kolejności obrażeń, z rozróżnieniem
   false positives. Bez takiego kontraktu każdy risk jest
   tylko opisem podatności `destructible`, nie certyfikatem
   zawalenia.

W obecnym zakresie **source disposition: UNSUPPORTED** dla
wiarygodnego przewidywania upadku. Nie jest to porażka testu
moda i nie dowodzi niemożności bezpiecznego planowania.
Forma/AoE istniejąca do v38: **SOURCE DONE, GAME DEFERRED**.
Nie trzeba kolejnego osobnego Windows buildu; #4 pozostaje
zablokowane do końca #86. Audyt można zintegrować jako
dokumentację bez podbijania rewizji runtime.
