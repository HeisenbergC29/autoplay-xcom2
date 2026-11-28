# #130 — blokada przedwczesnej ewakuacji w NeutralizeFieldCommander (v53)

Baza po ponownym review: 4d3a6fd27508e2855896f2c82ef428eb9698b75c.
Gałąź helper/130-required-sweep-before-evac, PR #134. Historyczna nazwa
pliku pozostaje v51. Rewizja runtime v53 zachowuje poprawkę #135/v52.

## Dowód z v50 i zakres korekty

Prywatny raport 27 XI, sesja NeutralizeFieldCommander
2026-11-27_15-53-1-38_3889, difficulty=3. KillCommander t5/h2587/seq4402,
PlaceEvacZone D32/unit410/seq4624, EVAC D34/unit428/seq4992 i
D36/unit410/seq5293, Sweep failed t8/h3354/seq6385, ekstrakcja h3357/seq6386,
native loss h3370/seq6394, history_pending=0.
Druga sesja: KillCommander t4/h2505, Sweep t8/h3340, bez end.
Nie wynika z tego, że pozostanie na mapie gwarantuje wygraną.

Pierwsza wersja PR nadmiernie uogólniała flagi strategiczne/taktyczne.
LEAD wskazał regresję Alien Facility. W zainstalowanym DefaultMissionDefs.ini:
- NeutralizeFieldCommander (sType NeutralizeFieldCommander): KillCommander
  strategiczny, Sweep taktyczny.
- SabotageAlienFacility (sType Sabotage): Sweep taktyczny, DestroyFacility
  strategiczny.
SDK X2StrategyElement_DefaultMissionSources.CreateAlienNetworkTemplate
przypisuje WasMissionSuccessfulFn=OneStrategyObjectiveCompleted, którego
implementacja wywołuje BattleData.OneStrategyObjectiveCompleted().
Dlatego stockowe Sabotage może wygrać przez ekstrakcję po DestroyFacility
bez Sweep. Flagi taktyczne same nie przesądzają warunków wygranej.
XGGameData.MissionDefinition.sType jest string; MissionObjectiveDefinition
zawiera ObjectiveName, bIsTacticalObjective, bIsStrategyObjective i bCompleted.
XComGameState_BattleData.AllStrategyObjectivesCompleted zwraca true także
dla pustego zbioru; zachowujemy oddzielne wymaganie istnienia celu strategicznego.
SeqAct_CompleteMissionObjective zapisuje ukończenie natywnie.
X2Ability_AbortMission ustawia bMissionAborted.

## Implementacja po review

- HasPendingRequiredCommanderSweep: dokładny native sType, brak abort,
  rzeczywista pozycja Sweep, bIsTacticalObjective i !bCompleted. Brak
  zweryfikowanego wymaganego Sweep nie dodaje veto. Bez nazwy lokalizowanej UI,
  prognozowania ukończenia ani wymuszania stanu.
- SquadEvacuationReason: dotychczasowa bramka niepustego zbioru celów
  strategicznych i natywnego AllStrategyObjectivesCompleted, dodatkowo
  wyłącznie powyższy Sweep. Przywrócono dotychczasowe zachowanie pozostałych
  misji, w tym ExtractAll; nie dodajemy ogólnego wyjątku ekstrakcyjnego.
- IsRescueEvacuation zachowuje cywila pod kontrolą XCOM i rzeczywistego
  nosiciela objective unit (zgodny SourceStateObjectRef i ObjectiveInfo).
- ShouldEvacuate: wspólna bramka celu marszu FindGoal i ChooseInteraction.
  Ruch bojowy na pole strefy nie jest zabroniony. Placement bez zmian.
- IsRequiredSweepEvacuationBlocked: dodatkowe veto tylko dla automatycznego
  Evac w CanUseAction i MakeDecision, także po ponownej walidacji.
  Nie rozszerzamy starej kontroli strategicznej na inne ścieżki dispatch.
  Native AA_Success, ownership, AP, ręczna ewakuacja i abort bez zmian.
- Marker evacuation_blocked opisuje zweryfikowany Sweep po strategicznym
  ukończeniu, raz na decyzję przy strefie, oraz odmowę dispatch.
  Rewizja v53 w Recorder/UI/DLC; #135 (terminal po limicie) pozostaje.

## Testy

tests/test_required_sweep_evac_v51.py wykonuje produkcyjne metody UC na
mockach native, w tym obie rzeczywiste gałęzie wyboru ewakuacji.
NeutralizeFieldCommander: przed/po KillCommander, przed/po Sweep,
abort, nieznane lub niewymagane Sweep, cywil/nosiciel, brak danych.
Sabotage: flagi stockowej definicji, przed DestroyFacility brak zgody,
po DestroyFacility przy otwartym Sweep dozwolony marsz do strefy i Evac;
brak nowego veto dispatch. Regresja starych reguł innych misji, ExtractAll
i pustego zbioru strategicznego. Synthetic ZIP→CLI zachowuje marker i
odrębny wcześniejszy loss. Trzy prywatne kontrakty SDK dotyczą flag,
completion/abort i warunku sukcesu AlienNetwork. To nie jest natywne
wykonanie Kismet ani rozgrywki.

## Próba Windows po review

Jedna paczka wyznaczona przez LEAD. NeutralizeFieldCommander: po KillCommander
i przed Sweep postawić legalną strefę; zwykły oddział pozostaje na mapie,
marker widoczny, po natywnym ukończeniu Sweep legalny Evac możliwy.
Alien Facility: po DestroyFacility przy otwartym Sweep sprawdzić możliwość
marszu i ekstrakcji oraz natywny wynik. Sprawdzić wyjątki rescue, ręczny
abort i ręczne Evac. Odrębnie ocenić native win i końcową punktację >0.
Windows build/game NOT RUN. Nie udowodniono skutecznego wykonania Sweep
na każdej mapie. Nie zmieniono scoringu ani innych misji.
