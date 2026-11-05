# Rejestr misji i obrona oddziału

Ta wersja dodaje zapis decyzji do logu gry. To rejestr diagnostyczny, nie film
ani odtwarzalny replay silnika. Ma pokazać, jakie akcje były dostępne, co wybrał
automat i co rzeczywiście wydarzyło się po rozkazach.

[Analiza pierwszego raportu z Gatecrashera i wynikające z niej poprawki](report-2026-11-02.pl.md).
[Analiza drugiej próby i rewizja `mission-report-v3`](report-2026-11-02-second.pl.md).
[Analiza trzeciej próby i rewizja `mission-report-v4`](report-2026-11-02-third.pl.md).
[Czwarta próba: zasadzka działa, granat użyty, misja przegrana](report-2026-11-02-fourth.pl.md).
[Pierwsza misja Legacy Operations: wynik v5 i przygotowanie v6](report-2026-11-02-legacy.pl.md).
[Kolejna próba Legacy: wynik v6 i poprawki v7](report-2026-11-02-legacy-v6.pl.md).
[Trzecia próba Legacy: wynik v7 i dalsze problemy](report-2026-11-02-legacy-v7.pl.md).
[V8: źródła kontroli, punkty AoE i zasięg wręcz](tactics-v8.pl.md).
[Pierwsze zwycięstwo v8 w Legacy i przejście do kolejnej misji](report-2026-11-03-legacy-v8-win.pl.md).
[V9: ratunek, łup i punktacja każdej symulacji](tactics-v9.pl.md).
[Próba v9: stabilizacja potwierdzona, GasStation przegrane](report-2026-11-03-legacy-v9.pl.md).
[V10: licznik punktów bieżącej misji nad przyciskiem](score-display-v10.pl.md).
[V13: wiedza o przeciwnikach, broń i kontrataki](enemy-knowledge-v13.pl.md).
[V14: konfiguracje jednostek i ryzyko oznaczonego żołnierza](config-knowledge-v14.pl.md).
[Raport v12 i napotkane zdolności](report-2026-11-04-v12-enemies.pl.md).
[Raport v14: ruch, trucizna i trzy porażki](report-2026-11-04-v14-poison.pl.md).
[V15: AP, chmury i dodatni wynik misji](tactics-v15.pl.md).
[Raport v15: trzy zatrzymania przed rzutem](report-2026-11-04-v15-stops.pl.md).
[V16: odrzucenie granatu i potwierdzanie końca tury](tactics-v16.pl.md).
[V17: ciosy Berserkera i ochrona przejętego sojusznika](tactics-v17.pl.md).

Wynik misji, punktację porównawczą i oficjalne punkty gry zapisujemy oddzielnie.
`score` w rekordach `candidate`/`chosen` jest oceną heurystyki, a startowe
`MaxScore` z `XCom_Challenge` to pula maksymalna. Rejestrator od v9 odczytuje
oficjalne `CumulativeScore` dla bieżącego etapu Legacy. Analizator stosuje
także wspólny profil oparty na regułach gry do wszystkich misji, również tych
bez oficjalnej punktacji. Do raportu dopisz oficjalny wynik z ekranu podsumowania,
ewentualny medal, restarty i ręczne działania, jeśli dane są dostępne.

Licznik HUD pokazuje natywny wynik **bieżącej misji**, gdy gra go prowadzi.
W Legacy odejmuje wynik przeniesiony na start etapu; zapis
`game_score.cumulative_score` pozostaje surowym wynikiem drabinki. To różne
wartości w kolejnych etapach. V10 pokazywało „—” w zwykłych misjach.
Od v11 HUD może pokazywać tam częściową ocenę porównawczą `~wartość/—`.
V12 i domyślny analizator używają profilu `wotc_legacy_observed_v2` od zera,
bez błędnej bazy +6000 na żołnierza ze starego v1. Tylda oznacza ocenę
porównawczą, nie wynik gry. Zakres obserwacji HUD-u i logu może się różnić,
szczególnie po wczytaniu zapisu.

## Co się zmieniło w taktyce

- V15 dodaje ograniczoną ocenę ruchu z zachowaniem podstawowego strzału.
  Natywna widoczność z rozważanego pola nie oznacza pełnego podglądu przyszłego
  trafienia; ograniczona projekcja jest jawnie heurystyczna. Po ruchu akcja
  i szansa są sprawdzane ponownie.
- Chmura trucizny jest sprawdzana osobno od statusu `Poisoned`. Bezpieczne
  wyjście może przejść przez początkowe pola własnej chmury, lecz musi skończyć
  na czystym widocznym polu, bez ognia/kwasu i ponownego wejścia po wyjściu.
  Wyjście nie usuwa już nałożonej trucizny.
- Overwatch konkuruje ze słabymi strzałami, zamiast zawsze otrzymywać minimalną
  ocenę. Obsługiwany jest też wariant `LongWatch` snajpera.
- Hunker Down jest oceniany według ran i zagrożenia ostrzałem. Może być
  priorytetem przy podpaleniu, ponieważ standardowa zdolność usuwa Burning.
  Nie jest traktowany jak ochrona przed bliską walką wręcz.
- `AidProtocol` specjalisty może osłaniać zagrożonego sojusznika. Automat
  respektuje dostępność, koszt i warunki gry, w tym już działający efekt.
- Flankowanie wymaga potencjalnej linii widzenia sprawdzonej przez silnik.
  Ruch w walce odrzuca nieodkryte pola na całej trasie; to ogranicza ryzyko
  wejścia w kolejną grupę podczas trwającej walki, ale nie gwarantuje jego braku.
- Podczas marszu do celu i eksploracji brana jest pod uwagę osłona na końcu
  ruchu. Zachowane są ograniczenia AP, wsparcia i niebezpiecznych pól.
- Po utracie widoczności niedawni przeciwnicy są pamiętani przez dwie tury.
  Poszukiwanie ich ostatniej widocznej pozycji odbywa się krótkimi krokami;
  częściowe przeładowanie nie wypiera wtedy overwatch. Ocena spekulacyjnego
  ruchu została ograniczona, aby nie wypierała dobrego strzału.
- Przy ukrytym oddziale atak może zostać poprzedzony przygotowaniem pozycji
  pozostałych żołnierzy i overwatch. Strzelec otwierający zachowuje akcję;
  przygotowanie ma limit sześciu poleceń na turę.
- Tylni żołnierze bez osiągalnej linii ostrzału mogą przed ujawnieniem dogonić
  strzelca otwierającego. Ruch musi materialnie skrócić odległość, zachować AP
  i nie zwiększać ocenianego ryzyka; nadal obowiązują kontrole wykrycia i trasy.
- Bezpieczny granat na pojedynczy cel może konkurować ze słabym strzałem,
  jeśli ma duże obrażenia z szansą zabicia albo sprawdzone dobicie sojusznika.

Przycisk Skyranger oznacza wezwanie ewakuacji, jeśli misja na nią pozwala.
Ewakuacja nie oznacza zwycięstwa w Gatecrasherze. Automat korzysta ze strefy
ewakuacji oraz jej wyznaczania zgodnie z dotychczasowymi regułami misji; nie
przerywa sam Gatecrashera tylko dlatego, że walka idzie źle.

Nie każda zdolność gracza ma automatyczny planer. Obsługiwane są skonfigurowane
ataki, leczenie, stabilizacja, przeładowanie, overwatch, hunker, Aid Protocol,
zwykłe granaty Frag/Alien, natywne `Loot` oraz rozpoznane akcje celu i ewakuacji. Pozostałych
zdolności automat nie uruchamia bez rozpoznania sposobu celowania i skutków.
Rejestr pokazuje także dostępne polecenia bez planera, żeby kolejne zmiany
wynikały z konkretnej misji.

Od v15 analizator oddzielnie zapisuje `attempt_verdict`. Do zaliczenia próby
potrzebne są zwycięstwo oraz pewny wynik bieżącej misji większy od zera.
Wynik zero lub ujemny przy zwycięstwie oznacza nieudaną próbę; brak pewnego
końcowego wyniku nie daje potwierdzenia. Oficjalne `outcome` gry pozostaje
osobnym faktem. [Reguła i przykłady](tactics-v15.pl.md).

## Zbudowanie i pierwsza próba

1. Pobierz aktualne źródła v17, rozpakuj je i zbuduj jak poprzednio na zachowanym
   SDK WOTC. Bez `-BuildBase`, jeśli pakiety bazowe są już przygotowane.
2. Zainstaluj nowy `dist\AutoplayXCom2.zip` i uruchom grę ponownie. Stara paczka
   z `release` nie zawiera rejestratora.
3. Wczytaj osobny zapis Gatecrashera na Commanderze albo Legendzie. Włącz
   autoplay. Rejestr rozpoczyna się przy pierwszym włączeniu i obejmuje też tury
   przeciwnika oraz późniejsze ręczne działania po zatrzymaniu autoplaya.
4. Po wyniku misji zbierz raport **przed ponownym uruchomieniem gry**, ponieważ
   następne uruchomienie zmienia pliki logów.

## Jak zebrać raport po misji

Możesz wcześniej usunąć pobrane źródła — skrypt jest instalowany razem z modem.
Otwórz w Eksploratorze folder:

```text
<SteamLibrary>\steamapps\common\XCOM 2\XCom2-WarOfTheChosen\XComGame\Mods\AutoplayXCom2\Diagnostics
```

Wpisz `powershell` w pasku adresu i naciśnij Enter. W otwartym oknie uruchom:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\Collect-MissionRecording.ps1'
```

Skrypt poda ścieżkę do nowego ZIP-a w:

```text
<Dokumenty>\AutoplayXCom2-Reports\
```

Załącz ten ZIP do rozmowy i dopisz poziom trudności, wynik, straty oraz czy
wydawałeś rozkazy ręcznie. Skrypt kopiuje `Launch.log` i do trzech najnowszych
kopii logu; nie zmienia ich i niczego nie wysyła samodzielnie.

Jeśli zachowałeś źródła, odpowiednikiem jest uruchomienie z ich katalogu:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\collect-mission-recording.ps1'
```

Możesz opcjonalnie dołączyć konkretny zapis taktyczny sprzed złej decyzji:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\Collect-MissionRecording.ps1' -SavePath 'D:\Zapisy\PrzedDecyzja.XComSave'
```

Zapis jest dołączany wyłącznie po podaniu `-SavePath`. Skrypt nie zbiera gry
ani SDK. W przypadku innej lokalizacji Dokumentów można podać `-LogDirectory`.

## Zawartość i ograniczenia rejestru

Wpisy `APXREC` zawierają identyfikator sesji, turę i zespół wykonujący ruch,
pozycje i stan własnego oddziału, kontakty widoczne dla gracza, dostępność
zdolności, najlepsze kandydatury z każdego planera, wybraną akcję i ocenę,
podgląd trafienia i surowych obrażeń oraz rzeczywiste wyniki akcji z historii.
Śledzone są także pauzy, odrzucenie rozkazu i koniec obserwacji.
Rewizja `mission-report-v4` dodaje znaczniki `ambush_setup` i `ambush_opening`.
Podsumowania `grenade_scan` rozróżniają dopuszczone i odrzucone okazje na
pojedynczy cel (`single_opportunities`, `single_rejected`) oraz ostatnie minimalne
i maksymalne obrażenia, HP celu i ocenę dostępnego zwykłego strzału. Liczniki
dotyczą sprawdzanych punktów w kolejnych decyzjach, a nie liczby rzuconych granatów.

Rewizja `mission-report-v5` dodaje `area_target_preview` dla wybranego granatu:
identyfikatory znanych celów, HP/tarcze i przewidywane obrażenia surowe oraz po
pancerzu. Główny cel granatu ma prawidłowo ID 0; opis trafionych jednostek znajduje
się w tych osobnych wpisach. `chosen` zapisuje także punkt celowania i lądowania.
Podgląd poprzedza aktywację, a faktyczne przyjęcie i obrażenia potwierdzają dopiero
`chosen.accepted` i późniejsze `result_target`. Pola `last_single_*` opisują ostatni
sprawdzany punkt skanu, który może być inny od wybranego.

Dla wybranego ruchu `move_threat_preview` pokazuje geometryczną osłonę
obecnej/docelowej pozycji względem każdego widocznego wroga oraz LOS. Pola
`current_default_view` i `destination_default_view` opisują widoczność z domyślnej
pozycji strzelca, bez wychylania. Używane zapytanie o LOS nie wypełnia natywnego
`TargetCover`; osłona jest liczona osobnym `GetCoverTypeForTarget`. Listy podglądów
mają limit 64 wpisów na akcję i nie są emitowane dla każdej propozycji ruchu.
Dane nie obejmują ukrytych kontaktów ani przyszłego ruchu przeciwnika.

Od `mission-report-v6` `move_threat_preview` zawiera też `enemy_template`,
`melee_only`, `current_distance`, `destination_distance`, `current_threat_risk`
i `destination_threat_risk`. Ryzyko jest wkładem pojedynczego widocznego wroga
z tej samej funkcji, której używa planer, przed łączeniem zagrożeń i mnożnikiem
zdrowia. Wartości nie są procentem trafienia ani prognozą obrażeń. Przeciwnik
wręcz może mieć wkład zero przez obecną granicę dystansu 12 pól; sam wpis osłony
nie oznacza, że chroni ona przed jego atakiem. Wycenę Aid Protocol, hunker
i overwatch ujednolicono z ruchem w zakresie przeszkód zasłaniających ostrzał.

Od `mission-report-v7` kandydaci i wybrane ruchy zawierają `best_attack_now`,
`best_attack_after_move_ap` oraz `potential_attack_loss`. To najlepsze oceny
obecnie legalnych, bezpiecznych ataków dystansowych przed ruchem i przy AP
pozostałych po niebieskim ruchu. Porównanie używa bieżących celów i pozycji,
bez przewidywania nowej widoczności, zasięgu lub trafienia. Dodatnia różnica
obniża ocenę zwykłego ruchu bojowego; zachowano wyjątek awaryjnego odwrotu
rannego żołnierza. Pole `potential_attack_loss` opisuje potencjalną utratę,
więc także przy ewakuacji i ruchu poza walką nie oznacza automatycznie kary
zastosowanej do końcowego wyniku ruchu. Szarże muszą ponadto przejść te same
kontrole znanego terenu, wsparcia, wysokości i bezpiecznej trasy co zwykły ruch.

Od `mission-report-v8` ataki zapisują `known_released_allies` i
`known_linked_enemies`: znane widoczne jednostki powiązane aktywnym efektem
z celem ataku. Liczniki opisują możliwe skutki jego śmierci, nie gwarantowany
wynik, natychmiastowy strzał odzyskanej jednostki ani zastosowaną premię
w każdej zdolności wielocelowej.

`move_threat_preview.melee_threat_reach` podaje rozpoznany możliwy zasięg
ruchu i ataku wręcz w polach. `-1` oznacza model nieobsługiwany. Wewnątrz
rozpoznanego obszaru ryzyko pozostaje wysokie; jest to oszacowanie bez
przyszłej trasy, ścian i decyzji wroga. Zasięgi są wyliczane raz na widoczny
kontakt w danym przeszukiwaniu ruchu, bez globalnej pamięci między decyzjami.

W `grenade_scan` dodano `pair_offset_centers` oraz
`blast_blocker_kind/id/class/geometry`, `blast_blocker_radial/children/surrounding`
i `blast_safe_radius_units`. Rozdziela to rzeczywistą bliskość chronionego
obiektu od braku interfejsu/pustej geometrii oraz różne rodzaje propagacji
zniszczeń. Dane szczegółowe dotyczą ostatniej blokady bezpieczeństwa w skanie,
a niekoniecznie wybranego punktu. Tożsamość i właściwości niewidocznych obiektów
pozostają zredagowane. [Interpretacja i granice v8](tactics-v8.pl.md).

Od `mission-report-v9` wpisy `rescue_candidate` i `loot_candidate` wskazują,
że propozycja ruchu ratunkowego lub po łup została w danej chwili najlepszym
planem. Nie są jeszcze potwierdzeniem wykonania: ostateczny wybór opisuje
`chosen`, a wynik zwykłe rekordy historii. `ability.handler=loot` rozpoznaje
obsługiwane natywne zbieranie przedmiotów.

Własne jednostki mają dodatkowo `bleeding_turns_remaining`, `score_eligible`,
`highest_hp`, `lowest_hp`, `unconscious` i `ladder_killed_scored`. Te pola
pozwalają odróżnić pierwszą ranę od kolejnych trafień i wyłączenie od śmierci.
`result` oraz `result_target` zapisują turę właściwej klatki historii oraz stan
celu po zdarzeniu, w tym `target_alive_after`, `target_incapacitated_after`
i `target_bleeding_out_after`. Samo HP równe zero nie dowodzi zabicia przeciwnika.

Zdarzenia punktacji:

- `hud_score` (od v11) — dokładny tekst wyświetlony nad przyciskiem, np.
  `~5200/—` albo `1200/—`. Zapis powstaje przy zmianie wartości, tylko podczas
  istniejącej rejestracji. Nie jest zdarzeniem przyznania punktów; tylda
  nadal oznacza częściową ocenę porównawczą.
- `game_score` — oficjalny odczyt `cumulative_score` z `legacy_runtime`,
  identyfikator drabinki i etapu, klatka historii oraz faza `start`, `observe`
  lub `finish`. Odczyt powstaje tylko wtedy, gdy stan drabinki nadal odpowiada
  rejestrowanej misji.
- `score_delta` — zaobserwowana rewizja natywnego `XComGameState_ChallengeScore`.
  `added_points`, `ladder_bonus` i `scoring_type` zachowują informację gry;
  analizator nie sumuje ich jako zamiennika oficjalnego wyniku.
- `score_rule` — parametry odczytane przez natywne gettery punktacji w Legacy:
  `kind=enemy`, `objective`, `soldier` lub `time`. Reguła przeciwnika pochodzi
  z widocznego podglądu, a reguła celu z jawnego zaliczenia. Powtarzające się
  identyczne reguły nie są ponownie emitowane. Analizator zachowuje je wraz
  ze startowymi tabelami gry w `native_rules_observed`.
- `scoring_coverage` — zakres obserwacji; obecnie `complete=false`, ponieważ
  uruchomienie F8 nie dowodzi rejestracji od początku misji.
- `objective_completed` — jawne zdarzenie zaliczenia pozycji listy celów,
  stabilny identyfikator i tura. Zwycięstwo nie zastępuje zdarzeń celów pobocznych.
- `civilian_rescued` — jawne zdarzenie ratunku przez własnego żołnierza.
  Tożsamość niewidocznego cywila pozostaje zredagowana.

Analiza dodaje `game_scoring` do każdej sesji. `official` zawiera rzeczywisty
odczyt gry, gdy był dostępny; `recording_delta` to różnica z okresu rejestracji
od F8, a nie dowód punktów za całą misję. `comparison` stosuje stały profil
`wotc_legacy_observed_v2`, opisany wraz z pochodzeniem parametrów w
`tools/legacy-score-rules.json`. V1 pozostaje w `tools/legacy-score-rules-v1.json`;
wyników różnych profili nie porównujemy wprost. Przy brakach zwraca `status=partial`,
`observed_subtotal` i listę `missing_components`; `total` pozostaje nieznany.
Składniki natywne pozostawione poza zakresem wspólnego profilu opisuje osobna
lista `excluded_native_components`. Nie uzupełniamy brakujących celów,
pochodzenia wrogów lub końcowych premii domysłami. Starsze raporty v8 także
otrzymują analizę, lecz nie zyskują przez to danych, których nie rejestrowały.
[Reguły i ograniczenia punktacji](tactics-v9.pl.md).

Podgląd nie przewiduje ukrytego losowania. Zniknięcie przeciwnika z pola widzenia
nie jest uznawane za zabicie. Brak końcowego wpisu albo osiągnięcie limitu
oznacza niepełne dane, a nie domyślnie wygraną lub przegraną. Rejestr nie
wykorzystuje ukrytych pozycji do wybierania akcji.

Do lokalnego podsumowania na komputerze z Pythonem służy:

```powershell
python .\tools\analyze-mission-log.py 'D:\Raporty\AutoplayXCom2-raport.zip' --json 'D:\Raporty\analiza.json'
```

Ustawienia w `Config\XComAutoplayXCom2.ini`:

```ini
[AutoplayXCom2.APX_Controller]
EnableMissionRecording=true
RecordCandidateScores=true
RecordingInterval=1.0
ContactMemoryTurns=2
ContactSearchDistance=4.0
CoordinateConcealedAmbush=true

[AutoplayXCom2.APX_SquadPlanner]
MaxCandidateTiles=64
MaxPreparationActionsPerTurn=6

[AutoplayXCom2.APX_MissionRecorder]
MaxRecords=20000
MaxHistoryFramesPerObserve=128
```

Zmiany wprowadzaj przy zamkniętej grze. Raport pozwala analizować decyzje,
ale nie potwierdza, że nowa wersja wygrywa misję. Kompilacja Windows i rzeczywisty
Gatecrasher nadal wymagają sprawdzenia w grze.

Od `mission-report-v11` znany natywny wynik i nieznane maksimum dają
`aktualne/—`. W misji bez natywnej punktacji licznik porównawczy daje
`~wartość/—`. Pojedyncze „—” oznacza brak dostępnego odczytu w trybie gry
prowadzącej punktację, np. bez pewnego stanu początkowego Legacy.
[Wyjaśnienie na raporcie SabotageCC](report-2026-11-03-v10-sabotage.pl.md).

Od `mission-report-v12` ocena porównawcza zaczyna od zera. Kara za pierwszą
ranę i potwierdzoną stratę jest odejmowana od tej bazy; nie ma początkowej
premii 6000 ani zakładanych premii końcowych. Stare `hud_score` z v11 zachowuje
oryginalny tekst v1, podczas gdy nowa analiza może obliczyć osobny wynik v2.
[Raport potwierdzający źródło przesunięcia](report-2026-11-03-v11-score.pl.md).

Od v12 wpis `hud_score` z oceną porównawczą zawiera też
`comparison_profile=wotc_legacy_observed_v2`. Historyczne odczyty v11
pochodzą z profilu v1; nie należy porównywać ich liczbowo z v2 bez
ponownego przeliczenia tych samych zdarzeń.

Od `mission-report-v13` wpis `enemy_knowledge` opisuje rozpoznane dane
widocznego kontaktu użyte przez nowy model. `move_threat_preview` pozwala
zestawić zastosowaną wagę z osłoną, LOS i rozpoznanym zasięgiem melee.
Dane opisują potencjał broni i zdolności, nie gotowość ataku ani decyzję AI.
Wagi są heurystyką planera; nie są trafieniem, obrażeniami z losowania ani
punktacją misji. [Zakres i ograniczenia](enemy-knowledge-v13.pl.md).

Od `mission-report-v13` `enemy_knowledge` zapisuje wyłącznie aktualnie
widocznych przeciwników: `primary_weapon`, `weapon_mean_damage`, bieżące
`aim`, `mobility`, `armor`, bazowe pola `base_*` załadowanego szablonu,
`robotic`, `tech_vulnerable`, `immune_types`, `threat_weight`, `target_threat`,
`capabilities` i `melee_counter_possible`. Maska zdolności: kontrola 1,
obszar 2, wsparcie 4. Są to parametry i potencjalne zdolności, bez odczytu
bieżących AP, amunicji, cooldownu i zamiaru AI. `move_threat_preview` zapisuje
wagę używaną dla obu ocenianych pozycji. [Interpretacja v13](enemy-knowledge-v13.pl.md).

Od `mission-report-v14` `move_threat_preview` dodaje `marked_aim_bonus`
i `target_status_weight`. Opisują aktywny, jawny efekt Marked na własnym
żołnierzu oraz jego ograniczoną wagę w ocenie otrzymywanego zagrożenia.
Przy przekazanej konfiguracji wartości wynoszą 10 i 1,1; bez oznaczenia 0 i 1.
Ta sama waga dotyczy pozycji bieżącej i docelowej oraz ocen obrony korzystających
ze wspólnego ryzyka. Nie jest natywną szansą trafienia ani dodatkową karą punktową.
Katalog poza grą zawiera osobne `config_values` i `configuration_audit`;
nie rozszerza to logu o niewidocznych przeciwników.
[Źródła, zakres i ograniczenia v14](config-knowledge-v14.pl.md).


Od `mission-report-v15` wpisy własnych jednostek dodają `poisoned`,
`poison_cloud` i `poison_cloud_harmful`. Rozdzielają status żołnierza od
publicznej chmury na jego polu; istniejący status nie jest odpornością.
Podgląd ruchu dodaje `current_poison_cloud`, `destination_poison_cloud`
i `needs_poison_escape`.

Ruch z prognozą podstawowego strzału zapisuje `offensive_forecast`,
`forecast_target`, `native_chance_now`, `projected_chance`,
`projected_attack_value` i `forecast_model=bounded_geometry`.
`native_chance_now` jest bieżącym odczytem gry, a `projected_chance`
ograniczoną prognozą geometryczną. Dotychczasowe `best_attack_after_move_ap`
nadal oznacza wyłącznie filtr kosztu AP, bez przewidywania nowej szansy.

V15 `game_score` dodaje `mission_points_known`, `mission_points` oraz
`mission_final`. Końcowy znacznik wymaga zatwierdzonego wyniku i nadrobionej
historii. Wynik Legacy odejmuje bazę rzeczywistego startu etapu, zamiast
utożsamiać całą sumę drabinki lub deltę od F8 z punktami jednej misji.
Znacznik nie obiecuje przyszłych nagród po ekranie końca. Starszy lub
niepełny odczyt HUD-u pozostaje informacją wstępną.

`attempt_verdict` analizatora opisuje ocenę próby według
`victory_and_positive_mission_score_v1`. Brak pewnego końcowego wyniku,
niepełna ocena porównawcza albo konflikt danych nie potwierdzają zaliczenia.
Wszystkie te dane są obserwacjami; nie zmieniają punktów ani zwycięzcy gry.

Podglądy czynności przygotowawczych dodają `ap_combo_available`,
`ap_combo_followup_ability_id`, `ap_combo_followup_target` oraz
`ap_combo_retained_attack_value`. Model
`ap_combo_model=current_legal_attack_after_stationary_preparation` opisuje
atak obecnie legalny i mieszczący się w projektowanych pozostałych AP
po Aid Protocol lub czynności medycznej. Nie kolejkuje tego ataku;
po rzeczywistej akcji kontroler ponownie ocenia cały oddział.


Od `mission-report-v16` `area_revalidation_rejected` opisuje granat odrzucony
przy końcowej kontroli, zanim powstał rozkaz dla silnika. Szczegóły zawierają
`unit`, `ability_id`, `history` oraz `reason`, `available_code`,
`evaluation_stage`, `evaluation_reason`, `impact_delta_sq`,
`location_delta_sq`, `expected_targets` i `fresh_targets`. Liczby świeżych
celów pozostają −1 do przejścia pełnej kontroli bezpieczeństwa. Taki wpis
może poprzedzać kolejną decyzję
i inną akcję bez `autoplay_stop`. Zero odrzuconych rozkazów nie oznacza braku
odrzuconych podglądów. W v15 ogólny komunikat nie wystarcza do wskazania,
który konkretny warunek nie został spełniony.

Potwierdzenie końca tury w v16 zapisują znaczniki `end_turn_requested`,
`end_turn_confirmed` i `end_turn_unconfirmed`. Potwierdzenie korzysta
z nowego kontekstu `SkipTurn` (`evidence=skip_turn_history`) lub zmiany
gracza/tury (`evidence=player_or_turn_transition`). Pole `native_return`
przy żądaniu jest diagnostyką; sam wynik `PerformEndTurn()` nie dowodzi
przyjęcia ani odrzucenia. Żądanie, potwierdzenie i brak potwierdzenia trzeba
oceniać razem z historią oraz zakresem misji. Po limicie oczekiwania
zapamiętane niejasne żądanie nadal blokuje jego duplikat po OFF/ON.
[Interpretacja zatrzymań i scenariusze](tactics-v16.pl.md).

Rewizja `mission-report-v17` oznacza integrację obsługi `DevastatingPunch`
i `DevastatingPunchMP` oraz ochrony własnego żołnierza pod rozpoznaną
odwracalną kontrolą umysłu przed wyborem ataku i granatu. Zachowuje pola
diagnostyczne v16; nie dodaje potwierdzenia kompilacji, przebiegu misji ani
nowej punktacji. Pole rewizji identyfikuje uruchomiony kod. Nie dowodzi,
że w danej misji wystąpił Berserker, efekt kontroli lub okazja do sprawdzenia
tych zachowań. [Scenariusze v17](tactics-v17.pl.md).
