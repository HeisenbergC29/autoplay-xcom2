# #123 — aktualne wyposażenie jednostki

Baza 411c8d4828be6315b750231967a959da884381ef. Etap 2 programu #120,
po odbiorze #125 w #128. Bez konsumenta rankingowego i bez zmiany v50.

## Kontrakt

APX_UnitStats.ReadUnitEquipment(History, HistoryIndex, ObserverID, SubjectID,
ItemIDs, Slots, Presence, Categories, Values, Status). Obie metody odczytu
statystyk i wyposażenia korzystają z jednego ResolveAuthorizedSubject:
aktualna historia i indeks, lokalny obserwator, dotychczasowy APX_FullIntel.
Bez cache między decyzjami. Przed każdym odczytem przedmiotu i po całości
sprawdzamy aktualność snapshotu; false zawsze czyści wszystkie tablice.
True nie oznacza pełnej wiedzy.

Cztery tablice wierszy: ID służy wyłącznie do odszukania, Slot to bieżący
EInventorySlot przedmiotu (nie domyślny slot template), Categories to
załadowany ItemCat, Presence: 0 nieznany, 1 rozpoznany przedmiot i template,
2 jawnie pusty slot. Zachowujemy osobne pozycje utility/grenade pocket,
heavy weapon, combat sim, ammo pocket (tylko tożsamość przedmiotu) i
dodatkowe sloty broni. Mission, Backpack i Loot nie są wyposażeniem.
Nie zakładamy, że pusty Utility wyklucza grenade pocket lub inne sloty.
Brak rozwiązanego przedmiotu/obcy owner/usunięty obiekt -> wiersz unknown
slot; brak template przy znanym slocie -> unknown w tym slocie.
Duplikaty nie są liczone dwukrotnie i obniżają pewność kompletności.
Puste sloty główny, dodatkowy, armor i utility dopisywane jawnie jako absent
tylko po rozpoznaniu wszystkich slotów. Gdy choć jedna referencja niepełna,
brakujący slot jest unknown. Limit 64 referencje + maks. 4 placeholdery;
przekroczenie limitu odrzuca snapshot, nie zgaduje braków.

Values i Status mają po 19 pól na wiersz. Index = row * EquipmentFactCount
+ stała. Status=1 znane (także zero), 0 nieznane (wartość wypełnienia zero).

| Indeks | Pole | Znaczenie |
|---|---|---|
| 0–6 | Damage, Spread, PlusOne, CritDamage, Pierce, Shred, Rupture | surowe BaseDamage; PlusOne procent, pozostałe punkty |
| 7–8 | Aim, CritChance | surowe punkty szablonu broni |
| 9–10 | Range, Radius | iRange w natywnych jednostkach (-1 LOS, 0 melee); iRadius w metrach |
| 11–14 | UpgradeCount, UpgradeAim, UpgradeCrit, UpgradeDamage | liczba zainstalowanych ulepszeń i sumy ich nominalnych pól |
| 15–18 | ArmorHP, ArmorMitigation, ArmorDefense, ArmorMobility | nominalne bezwarunkowe deklaracje UIStatMarkups, nie efektywne statystyki |

WeaponTemplate obejmuje również X2GrenadeTemplate. Nie interpretujemy
RangeAccuracy, ExtraDamage, specjalnych efektów, modyfikatorów zależnych
od celu, AP, amunicji, liczby ładunków, cooldownu i gotowości.
Inne utility mogą mieć wyłącznie znaną kategorię/slot i nieznane liczby.
UpgradeDamage może oznaczać obrażenia przy pudle; nie jest dodatkiem
do bazowego trafienia. Puste nazwy upgrade slotów pomijamy, nierozpoznana
nazwa lub >32 wpisy unieważniają agregaty, nie podstawowe pola broni.
Nie wywołujemy callbacków ulepszeń ani obliczeń zależnych od HQ.
Brak deklaracji pancerza, warunkowa deklaracja lub >64 wpisy markups =
unknown. Jawne zero bezwarunkowe jest znane. To dane deklaratywne UI,
a nie pełny efekt wyposażenia; NIE dodawać ich do HP, obrony, mobilności
ani pancerza #125 (ten już uwzględnia aktualny bonus i shred).
Brak reguł zależnych od nazw jednostek lub przedmiotów.

## SDK

Prywatny dostarczony SDK, XComGame/Classes. InventoryItems jest
protectedwrite (odczyt dozwolony); GetAllInventoryItems pomija
nierozwiązane referencje, dlatego korzystamy z własnego ograniczonego
odczytu aktualnych referencji. AddItemToInventory przypisuje InventorySlot
i OwnerStateObject. GetMyTemplate jest native. GetMyWeaponUpgradeTemplateNames
zwraca nazwy zainstalowane, GetMyWeaponUpgradeTemplates zapisuje cache;
używamy pierwszego API i FindItemTemplate menedżera, bez callbacków.
X2WeaponUpgradeTemplate deklaruje AimBonus, CritBonus, BonusDamage.
X2EquipmentTemplate.UIStatMarkups zawiera StatType, StatModifier i
ShouldStatDisplayFn; nie wywołujemy GetUIStatMarkup (delegate i bonusy HQ).
Brak prywatnych plików SDK w repo.

## Testy i ograniczenia

Test-only translator wykonuje rzeczywiste metody UC na kontrolowanych
mockach natywnych usług. E2E publicznego odczytu obejmuje wymianę broni
i pancerza jednej jednostki w kolejnej ramce, różne ID/nazwy przy
identycznych faktach, utility, cargo, brak danych, zero, warunkowe
markups, niekompletne upgrades, autoryzację i invalidację snapshotu.
To nie native game E2E. Zachowane testy #125. Opcjonalny kontrakt SDK
sprawdza deklaracje i źródłowy getter z prywatnego pakietu.

Windows: po review skompilować zintegrowaną paczkę. Mod sam nie używa
nowego odczytu w decyzjach; jego obserwację w grze zaplanować wraz z
pierwszym konsumentem (lub przez tymczasowy debugger SDK), na własnym
żołnierzu z bronią, ulepszeniem, armor i utility oraz autoryzowanym wrogu.
Porównać wartości z aktualnymi template/slotami, w osobnej próbie podmienić
broń i zbroję tej samej jednostki, a po shred sprawdzić że bieżący
pancerz #125 nie sumuje deklaracji drugi raz. Native build/game NOT RUN.
Nie zmieniamy markerów ani dotychczasowych decyzji; nie jest to dowód
zmiany skuteczności taktycznej. Kolejne etapy wyłącznie po review LEAD.
