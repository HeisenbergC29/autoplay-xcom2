# #31 — etap 1: wspólny kontakt ujawnionych strzelców (v31)

## Dowód i punkt startowy

Użytkownik kompiluje/testuje v29, którego main `189aa3d3aba054109f7ca1405770a2c90b0676e9` jest niezależny od tej pracy. 
Przed v29 GasStation `ChallengeAbductionGasStation` kończył native LOSS,
z końcowym −21200 (v28) i −12900 (v27) w różnych próbach. Squad miał
`concealed=False`, więc ścieżka `ChoosePreparation` przygotowująca
zasadzkę z ukrycia nie była uruchamiana. V27 wykazała jednak trzy realne
`OverwatchShot`, więc reakcje już istnieją; brakuje koordynacji wspólnego
celu podczas standardowej walki.

Ten PR jest **zależnym/stacked** etapem na `helper/62-persistent-tactical-panel`
(PR #63, v30). Jego diff ma obejmować v31 po HUD v30; przed scaleniem
LEAD weryfikuje, że #63 znalazł się na main albo zmienia bazę/przenosi
rewizję. Użytkownik ma nadal testować **wskazane v29**, nie bieżący
roboczy PR.

## Zmiana taktyczna — tylko ujawniona grupa i bieżący kontakt

`APX_RevealedFocus.uc`: z publicznych `XComGameState_AIGroup.m_arrMembers`
wybiera **jedną aktualnie widoczną** dla własnej drużyny grupę.
Publiczne `GetAllVisibleEnemiesForPlayer` musi zawierać każdego
kandydata do tego fokusu: obecna wiedza full-intel o odległym wrogu
nie jest sama w sobie poleceniem aktywacji nowej grupy.
Usuwamy martwych/nieaktywnych/cywilów/kosmetycznych/własnych/odzyskiwalnych
kontrolowanych sojuszników. Spośród realnych członków grupy wybieramy
jednego przedstawiciela preferując dystans i już uszczuplone HP;
grupa z poprzedniej decyzji ma mały bufor stabilizacji (+9), ale
istotnie bliższy kontakt może ją zastąpić. Po zmianie bieżących stanów
AI przelicza wybór, bez arbitralnej rezerwacji trafienia.

Jeden read-only bounded skan na decyzję: max24 grupy, 128 referencji
grup, 128 stanów własnych+pozostałych jednostek, 12 własnych strzelców
i max64 natywne kontakty. Przekroczenie limitu skutkuje **fail closed**
bez częściowego obrazu grupy. Ranged-eligible: lokalne żywe
niecywilne niemelee jednostki XCOM, bez BerserkerMP.
Wykryte `IsBleedingOut`, aktywny timer, concealment, Squad<2,
`EnableFullIntel=false` lub misja `SabotageTransmitter` wyłączają
tę politykę; bez wyjątku dla Blood Killer.

Kontroler przechowuje jedynie group ID w granicach tego samego
`XCOMHISTORY`, `StartState`, `BattleData`, gracza i monotonicznego
`HistoryIndex`, reset przy OFF/rewind/zniszczeniu oddziału/nowej misji.
Rejestruje `revealed_focus`: group, native squad-visible primary target,
liczbę widocznych członków, strzelców i dystans.

`APX_CombatPlanner` po dotychczasowym
`AvailableCode == 'AA_Success'`, `IsVisibleHostile`, 
`AdditionalTargetsAreSafe`, `HasRequiredMeleePath` i `ScoreAttack`
daje miękkie +14..22 **tylko** dla legalnych
`StandardShot/PistolStandardShot/SniperStandardFire` na wskazany cel
(bez melee, granatów, obszarowych ani nieznanych rodzajów ataku).
Dostępne legalne ataki na innych wrogów pozostają do wyboru przy
wyższej bazowej wartości; nie obiecujemy, że cel fokusu zawsze wygra.

`APX_MissionPlanner`: podczas rzeczywistego bezpośredniego kontaktu
ranged może użyć tego celu do oszacowania pozycji, lecz wyłącznie po
istniejących kontrolach ewakuacji, SabotageTransmitter/X4, braku
terminu i braku pilnego ratunku; soft bonus do7 za zbliżenie.
Istniejące oceny ekspozycji, linii ognia, osłon, bliskich wrogów,
wspierania oddziału, całej ścieżki, ostatniego AP i konstruktywnego
fallbacku pozostają. Zero mutacji jednostek/AI, zero zmian punktacji.
Natywne `Ability.GetShotBreakdown` nadal uwzględnia prawdziwe bonusy
strzału z aktualnego stanowiska.

## Weryfikacja i dalsze etapy #31

`tests/test_revealed_group_focus.py` uruchamia realne numeryczne
helpery UC (native state gates, stabilizacja, HP/kill focus, ograniczony
postęp) i kontrakty integracji/odczytów. Kontrakty nie potwierdzają
natywnej kompilacji ani rzeczywistego zachowania wroga.
Faza 1 nie wprowadza **ustawiania 2–3 własnych jednostek w OW**,
planowania scamper ani wykorzystania waypointu jako przyszłej trasy,
nie odgrywa zasadzki concealed przy `concealed=False`. Fazy 2/3 #31
mają objąć oddzielnie legalne OW + potencjalny opener oraz rzeczywiste
przewagi wysokości (stock ranged Aim +20 przy progu3 Z), z ograniczonym
symulatorem ruchu i dodatkowymi testami. W obecnym PR nie wprowadzamy
niedowiedzionych bonusów defensywnych lub melee dla wysokości.

Odbiór w grze dopiero po LEAD integracji i kolejnym buildzie wskazanego
SHA: GasStation/diff2, aktywny pod, czy grupa i primary są faktycznie
widoczne i atakowalne, liczba trafień/obrażeń i straty, nieotwieranie
drugiego podu na ślepo, native victory i znane końcowe punkty >0.
Stare natywne punktowanie i bezpieczny odczyt HUD v28 niezmienione.
