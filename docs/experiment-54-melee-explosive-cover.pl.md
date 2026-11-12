# #54 — ryzyko detonacji osłony od wrogiego ataku wręcz (HELPER)

## Dowód i zakres

Baza: `main` v26 `37e4fdeff3c8ac075e621a7b71284afcb01c69fc`.
Raport prywatny: `AutoplayXCom2-20261112-112454-bfc285c6.zip`,
manifest `2026-11-12T11:24:54.6409968Z`, jeden aktualny `Launch.log`.
Odpowiada on przesłanemu osobno `Launch.log` (bajtowo identyczny,
SHA-256 `6781233a38c09389395cefc3303e82981c3c9c572591be8ebac5a0b59e35c251`).
Nie ma materiałów prywatnych w commicie.

GasStation `mission-report-v26`: `ChallengeAbductionGasStation`,
15 accepted chosen, 0 `ambush_setup` i 0 `ambush_opening`, native loss
z finalnym natywnym wynikiem **−21200**. `Faceless` unit63506
wykonał `ScythingClaws` (history556) z podglądem target63480,
po czym w historii wystąpił `CMPT_DeadSoldier −5000` (history595).
Gracz zaobserwował zniszczenie wybuchowego otoczenia przy ataku,
ale sam recorder **nie zapisuje** identyfikatora ani efektywnego
`EnvironmentDamage` konkretnego wybuchającego aktora. Nie przypisuj
śmierci wyłącznie wybuchowi; target preview akcji pokazuje HP 5→5
dla tego zdarzenia, a końcowy stan żołnierza to HP0.

## Potwierdzony błąd źródłowy

`APX_ExplosiveCoverKnowledge.HasRelevantRangedThreat` przed
obliczaniem radial-damage cover wykluczało `Enemy.IsMeleeOnly()`.
W związku z tym przy braku wroga z wyposażeniem ranged nawet
realny, nadal żywy `XComDestructibleActor` z nominalnymi obrażeniami
`DestroyedEvents` nie dawał kary za groźne stanowisko, jeśli
jedynym pobliskim zagrożeniem był Faceless. Nie jest to dowód,
że detona­cja jest pewna lub że dotyczy dokładnie podejścia unit63480.

## Zmiana

Zastępujemy filtr `HasRelevantRangedThreat` nowym
`HasRelevantDestructionThreat`. Dodany czysty
`MayDamageCoverFromPosition` zachowuje dotychczasowy warunek
ranged/area w 22 polach (X/Y) i maksymalnie ±2 poziomach Z.
Dla melee `IsMeleeOnly()` rozpoznaje możliwą zdolność uszkodzenia
otoczenia w **konserwatywnym, ograniczonym** promieniu
`FClamp(Mobility*0.5+2,4,16)`. To geometryczny *scenariusz*,
nie odczyt cudzych AP, cooldownów, aktualnego celu, RNG, trafienia ani
gwarancja reakcji. Właściwy naliczany koszt wciąż wymaga natywnych
`GetActorsOnTile`, `XComDestructibleActor`, `DestroyedEvents`,
`RadialDamage.UnitDamage`, `GetBlastExtents` i potwierdzenia,
że przyszły wybuch nie jest już niemożliwy. Istniejący maksymalny
koszt/penalty wynosi 42 i nie stanowi absolutnego zakazu ruchu.
Wszystkie limity inspekcji (32 wrogów, 5 pól, 16 aktorów, 32 eventy
i zewnętrzny budżet kontrolera) pozostają.

## Testy i granice

`tests/test_explosive_cover.py` zawiera dodatkowe wykonywalne próby
prawdziwego helpera z UnrealScript: bliski/daleki melee przy Mobility4/14/
300, pułap Z, zakres ranged/area oraz odrzucenie wroga bez zdolności.
Kontrakty strukturalne potwierdzają obecność filtra melee w estymatorze,
brak nielegalnego odczytu AP i zachowanie natywnych radial events.

Kompilacja Windows WOTC SDK i test gameplay są osobnymi dowodami.
Weryfikacja A/B: GasStation na analogicznym seedzie, instrumentować
kandydujące pozycje pod kątem natywnych radial extents i oceny końcowej,
porównać strategiczne decyzje oraz wynik bez obietnicy uniknięcia
każdego kolejnego wybuchu. Nie zmieniono wyboru patrolu i akcji
faceless przez samą grę. LEAD nie powinien scalać bez przeglądu
exact HEAD i zatwierdzonego CI.
