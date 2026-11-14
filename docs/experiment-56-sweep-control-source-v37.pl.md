# #56 P1b — v37: ruch do aktualnie potwierdzonego kontrolera w Blood Killer Sweep

## Tło / dowód

Autonomiczne Blood Killer v32: native LOSS t14 mimo
końcowego native +7100; X4/relay completed t8, Sweep/Extract
failed t14. 53 pierwsze wybrane rozkazy identyczne z v29,
0 aktywacji `phase=contact`. Raport LEAD po analizie
prywatnego ZIP potwierdza trzy **udane** natywne
`PriestPsiMindControl`: 46→23 t8, 46→25 t12,
37→24 t14. Sama dawna udana akcja nie stanowi
dowodu, że efekt nadal trwa. Błędne jest także
wnioskowanie `mind_controlled=False` z brakującego
pola w redacted enemyrecord.

W `APX_CombatPlanner` już istniały bezpieczne
`GetKnownSourceBenefits`, `ScoreSourceBenefits` i
`IsReclaimableControlledSquadmate`. Pierwsze
dwie funkcje zwiększają wartość **już legalnego**
trafienia, jeśli przeciwnik jest rzeczywistym
źródłem aktualnego efektu `X2Effect_MindControl`
z `bRemoveWhenSourceDies` na wcześniej własnym
żołnierzu. Dotychczas **FindGoal podczas Sweep**
nie wykorzystywało tej informacji do wyboru
kierunku ruchu: preferowało aktualny AIGroup,
immediate threat lub dowolnego znanego wroga.

## Rzeczywista poprawka

`APX_MissionPlanner.FindGoal` po sprawdzeniu
`ShouldEvacuate` i wyłącznie przy:
- `BerserkerMP` w `SabotageTransmitter`;
- **natywny** `PlantBomb` z `bCompleted=true`;
- HP aktywnej własnej jednostki >= 40% jej maksimum;
- brak własnego żołnierza wymagającego pilnej pomocy przy wykrwawianiu;
- wrogi source żywy, nieusunięty,
  nieincapacitated i wybrany z bieżącej
  ograniczonej `VisibleEnemies` (max24);
- `APX_CombatPlanner.GetKnownSourceBenefits`
  zwraca `ReleasedAllies>0`;

przyznaje preferencję celu **ruchu**, nie akcji.
GetKnownSourceBenefits samo sprawdza aktualną
natywną widoczność wroga i efektu na widocznym
wcześniej własnym XCOM oraz link
`EffectState.ApplyEffectParameters.SourceStateObjectRef`
i `TargetStateObjectRef`. Nie porównuje nazw
`AdvPriestM3` i nie korzysta ze starych logów
`PriestPsiMindControl` ani z ukrytego zamiaru AI.
Z wielu aktualnie legalnych źródeł wybiera
najwyżej ocenione według liczby potencjalnie
uwalnianych żołnierzy i dystansu.

`Goal.Tile` staje się aktualną rzeczywistą
pozycją tego źródła. `Goal.bCombat=true`,
więc dalszy `ChooseMove` zachowuje istniejące
ograniczenia native path, AP, hazardów,
wsparcia i oceny ryzyka. Jeżeli źródło już
nie żyje, nie jest widoczne, efekt minął,
oryginalna własność jest niepotwierdzona,
zdrowie spadło lub nie ma bezpiecznego ruchu,
normalne planowanie zachowuje swoje uprawnienia;
nie przyznano sztucznej zdolności.

Przegląd LEAD wykrył, że samo ustawienie combat `Goal.Tile` zmieniało
głównie dodatkowego kandydata ClosestTile. Przy widocznym przeciwniku
nie działa routine route, a ogólny PositionScore ocenia wszystkich wrogów.
Dlatego potwierdzony cel dostaje teraz lokalną flagę
`bSweepControlSourceGoal`. W zwykłej ocenie kandydatów ruchu tylko ta
flaga dopuszcza miękki bonus za rzeczywiste zmniejszenie odległości
do źródła: 2 punkty użyteczności za pole, maksymalnie 12.
Przy ruchu w bok/od źródła, mniej niż 2 AP lub wzroście ryzyka
bonus wynosi zero. To nie jest bonus do trafienia/obrażeń.
Kandydat nadal musi przejść native move/path, pełne hazardy,
wsparcie, IsUsefulReposition i koszt utraconego ataku.
Nie odblokowano routine route przy kontakcie ani ostatniego AP.
Flaga nie jest zapamiętywana między decyzjami; ratunek blokuje nową
preferencję jeszcze przed wyborem źródła.

Odpowiedni marker w `Launch.log`:
`Berserker sweep control source|unit=...|source=...|priority=...|target_x=...|target_y=...|target_z=...`.
Przy kolejnym native rezultacie po śmierci
źródła i ewentualnym zniesieniu `MindControl`
następna decyzja oblicza cel od nowa; brak
pamięci spekulacyjnej o tymczasowym efekcie.
Zachowany stary bonus natywnego attack i
ochrona przed strzelaniem do odzyskiwalnego
kontrolowanego sojusznika. Pełne reguły
`LastAP`, `Relay/X4` i ratunek nie są zmienione.

## Ograniczenia / test

To jest **P1b etap kontrolera podczas Sweep**,
NIE rozwiązanie całej kwestii podejścia i przeżycia.
Preferencja nie gwarantuje bezpiecznego dojścia
do wroga, zabicia źródła, zerwania kontroli
ani native victory. Niezabezpieczone zwroty
`GetKnownSourceBenefits` dają zero i nie
zmieniają ruchu. Przy HP<40% żadne obejście
ograniczeń bezpieczeństwa nie jest włączone.

`tests/test_sweep_control_source.py` sprawdza
faktyczne helper policy UC, rodzaj misji,
post-X4 gate, dowody aktywnego linked effect,
bounded loops, brak niedozwolonych odczytów
enemy AP/cooldown, natywne guards i zachowanie
`ScoreAttack` oraz APX_Route.
Regresje LEAD wykonują również rzeczywisty helper bonusu: dwa
konkurencyjne stanowiska, ograniczenie 12, brak premii za oddalanie,
nieaktywny cel, ostatnie AP i zwiększenie ekspozycji. Kontrakty
wiążą bonus z aktualnie zweryfikowaną flagą i zachowanymi kontrolami.

Integracja **stacked**: baza PR #83
`helper/79-runtime-legacy-v36`, nowa rewizja
`mission-report-v37`. LEAD scala #83 albo
świadomie rebase'uje #56 bez nadpisania v36.
Nowy plik V3 punktacji pozostaje obecny w
tej gałęzi, ale nie jest częścią różnicy PR #56.
Bez zmiany starego observed_v2 i kryteriów.

WOTC SDK compile v37: **NOT RUN**.
Gra i autoteliczna misja Blood Killer v37:
**NOT RUN**. Po LEAD review/merge sprawdzić
w próbie realny marker + wynik native ciosu
w konkretne sourceID, reakcję efektu na
śmierć źródła, X4/relay, straty, terminal
native outcome i znane punkty końcowe.
