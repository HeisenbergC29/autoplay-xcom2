# #79 etap B — v36: rzeczywiste naliczanie zaobserwowanych zdarzeń ze stawek Legacy

Baza: `main` `543c5922fdc2bd94305f11c062a5a3ebf6281149`,
testowa rewizja runtime `mission-report-v36`.
Nie zmienia się native/Legacy score engine, taktyka, score/acceptance policy,
ani dostarczona użytkownikowi paczka v35. LEAD prowadzi review/merge.

## Co jest faktycznie wdrożone

Nowy, **oddzielny** obserwator `APX_LegacyObservedV3.uc`
ma profil `wotc_legacy_config_observed_v3_partial`.
Dotychczasowy `APX_ComparisonScore.uc` /
`wotc_legacy_observed_v2` pozostaje dokładnie bez zmian dla dawnych
raportów, odtwarzalności i wycofania nowej polityki.
`APX_MissionScore` korzysta z v3 tylko w trybie bez
`XComGameState_LadderProgress` i `XComGameState_ChallengeData`,
nadal za `CanReadScoreNow` (latent safety). Native gettery i
podsumowanie Legacy/Challenge mają **bezwzględny priorytet**.

Źródło nowych stawek jest prawdziwe `config(Ladder)` gry:
`class'XComGameState_LadderProgress'.default.DefaultEnemyScoring`
oraz `DefaultEnemyScoringTable` (rozpoznanie dokładnej nazwy szablonu),
`DefaultObjectiveScoring` / `DefaultObjectiveScoringTable`
(dokładny klucz `MissionType,TextPoolIndex,GroupID,LineIndex`)
oraz `DefaultSoldierScoring`.
Nie przeniesiono prywatnych INI ani 134 tablic do repozytorium.
Brak załadowania konfiguracji jest `unavailable`, a nie ukrytym
fallbackiem do niepoprawnych stawek ze stock structdefaultproperties.

Nowe **naprawdę liczone** zdarzenia:
- potwierdzony normalny wróg, którego stan `ObjectID` występuje
  już w zweryfikowanym `TacticalGameStart` i był tam wrogi XCOM: nadana stawka
  `StartingPoints/MinPoints/DecreasePerTurn/TurnOffset`;
- wróg z jawnym `GetUnitValue('NewSpawnedUnit')`:
  tylko tabelaryczne `SpawnedPoints`;
- wróg pojawiający się dopiero po `StartIndex` i bez
  jednoznacznego znacznika: **nie** otrzymuje punktów zwykłego wroga,
  tylko `bUnknownEnemyOrigin` i częściowość (może być
  reinforcement, summon albo inną jednostką);
- pierwsza obserwowana rana własnego kwalifikującego się żołnierza:
  `-DefaultSoldierScoring.UninjuredBonus`, tylko gdy stawka jest dodatnia;
- utrata żołnierza w obserwowanej historii:
  `-DefaultSoldierScoring.WoundedBonus`,
  w stock `LadderProgress.OnUnitDamage/OnUnitKilled`
  rzeczywiście takie potrącenia występują; zero/ujemna stawka nie daje premii;
- prawidłowo zidentyfikowany `MissionObjectiveMarkedCompleted`
  według konkretnego override celu misji i czasu;
- `CivilianRescued` przez aktualnie kontrolowanego gracza:
  `DefaultSoldierScoring.RescuedCivilianBonus`.
Suma nadal jest **zero-based**. Nie dodajemy domyślnych
początkowych premii, hipotetycznych zabitych poza obserwacją,
ani sztucznego maksimum.

Silnik ma strukturę `ChallengeEnemyScoring` z osobnymi
`ReinforcementPoints`, `DisabledPoints`, `MinDisabledPoints`.
Ich **stawki znamy**, ale nie udajemy, że same reguły
wystarczą do pewnego rozpoznania przyczyny powstania jednostki
albo dokładnej chwili natywnego disabled award.
W bieżącym pierwszym etapie nie wypłacamy tych kategorii bez
zweryfikowanego, odtwarzalnego natywnego zdarzenia.
Restart i opcjonalne native Ladder bonuses również
zostają poza zakresem dowodowym.

## Wyraźna granica oficjalności

V3 to **wynik częściowy**:
`GetCoverageStatus()` zwraca m.in.
`partial_unknown_enemy_origin`,
`partial_unverified_tactical_start`,
`partial_objective_civilian_listener_started_late` lub
`partial_native_disabled_restart_bonus_unverified`.
Rejestrator oznacza `hud_score` jako
`comparison_status=partial`,
`rate_source=installed_ladder_config`,
`native_parity_proven=false`,
`event_coverage_proven=false`.
HUD pozostaje z `~` i bez wymyślonego maksimum.

Wzór `DecayedPoints` pochodzi z dotychczasowego
`observed_v2` i jest porównany z konfiguracją,
ale ciała natywnych award/turn-decay C++ nie występują w UC.
Dlatego **nowy subtotal nie jest jeszcze oficjalnym,
kompletnym wynikiem misji**, nawet gdy wszystkie jego
zaobserwowane składniki są już liczone z poprawnych stawek.
Zasadę użytkownika przyjmujemy: gdy przyszły profil udowodni
identyczne reguły **i** kompletne zdarzenia końcowe, obliczony
przez mod wynik będzie oficjalny. To nie jest jeszcze ten etap.
Natomiast natywny terminalny wynik z gry ma pierwszeństwo
i zachowuje swój status.

## Dowód i odbiór

Przegląd LEAD doprecyzował kwalifikację startu: sam `FindStartStateIndex`
i obecność obiektu w archiwum nie wystarczają. Obserwator sprawdza
`XComGameStateContext_TacticalGameRule/eGameRule_TacticalGameStart`
i początkową własność. Pierwsza widoczna wersja przejętego dawnego XCOM
nie staje się przez to zwykłym wrogiem do naliczenia kill points.
Natywne previous-team XCOM blokuje enemy award także przy niepewnym starcie.
Przy takim starcie zachowujemy tylko składniki możliwe do kwalifikacji,
np. obserwowane kary aktualnie własnego żołnierza; nie udajemy znajomości
jego początkowej własności. Jawny native spawn pozostaje osobną klasyfikacją.

Niepełne lub nadmierne tabele (powyżej512 wpisów) są odrzucane zamiast
ucinać skan i stosować potencjalnie błędny default. Guardy dodatnich
UninjuredBonus/WoundedBonus odpowiadają natywnym handlerom, więc ujemne
wartości konfiguracji nie przyznają punktów za ranę/stratę.

Jednorazowy na inicjalizację/zmianę misji log `Legacy observed rates`
zawiera identyfikator profilu, długości załadowanych tabel enemy/objective
oraz flagi verified_tactical_start/early_event_coverage. Nie wypisuje
tabel ani jednostek. Pozwala sprawdzić faktyczne runtime config/TLE
na podstawie zwykłego raportu z niepunktowanej misji.

`tests/test_legacy_observed_v3.py` sprawdza rozdzielenie
v2/v3, faktyczny odczyt stock `config(Ladder)`, klucz
objective4 pól, prawidłowe przykłady minimum stawki
Trooper/Priest/TerrorBar, jednoznaczność pochodzenia,
first wound/death, obsługę cywilnych, latent safety,
bez mutacji historii i niezmieniony native score provider.
Regresje wykonują też rzeczywiste czyste helpery UC: niezweryfikowane
archiwum, śmierć dawnego XCOM pod kontrolą, zwykły/spawned wróg,
granice długości tabel i dodatnie/zerowe/ujemne potrącenia.
Przy dostarczonym SDK test sprawdza również stock
`XComGameState_LadderProgress` i deklaracje struktur.

Pozostały konieczny odbiór:
1. LEAD weryfikuje, czy `config(Ladder)` na rzeczywistym
   uruchomionym WOTC uwzględnia TLE/overrides; brak tabel
   powinien być widocznym `unavailable`;
2. user Windows SDK `make` po scaleniach na exact SHA i
   porównanie z native rzeczywistymi `score_delta` w
   Legacy (nie dopisywać punktów do porażek);
3. brak regresji głównej paczki v35 w X4, Blood Killer i
   GasStation, natywne zwycięstwo tylko przy braku manual;
4. kolejny etap: pochodzenie reinforcement/disabled z
   natywnych zdarzeń, restart/bonus i pełna rekonstrukcja
   objective/civilian po load i nawet przy późnym F8,
   a na końcu walidacja identyczności formuł / oficjalność.

**Native Windows make i gameplay dla v36: NOT RUN**.
Dostępne źródła SDK i pliki konfiguracyjne użytkownika
pozostają prywatne.
