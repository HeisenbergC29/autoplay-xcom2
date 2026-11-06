# Testy odbiorcze

V20: odzyskiwalny sojusznik pod kontrolą umysłu musi pozostać w ocenie
zagrożenia, chociaż nie może być celem pościgu, ataku ani granatu. Przy
takim widocznym zagrożeniu ruch nadal wymaga oceny bojowej; ewakuacja
zachowuje swój priorytet.

Najnowszy [raport GasStation v19](report-2026-11-06-v19-gasstation.pl.md)
kończy się porażką po 40 przyjętych rozkazach, z normalnym zamknięciem logu.
Ostatni odczyt −20100 jest częściowy (`mission_final=False`, 18 klatek
historii pozostało). Bieżące v20 wprowadza potwierdzoną przez użytkownika
pełną wiedzę o mapie i pozycjach aktywnych wrogów.
[Instrukcja v20](experiment-25-full-intel.pl.md). Kompilacja Windows i gra
v20: **NIEURUCHOMIONE**.

Raport z rewizją v17 obejmuje dwie porażki i awarię; analiza jest w
[issue #15](https://github.com/HeisenbergC29/autoplay-xcom2/issues/15).
Dokładny SHA kompilacji nie jest potwierdzony. Poprawka MP z v18 pozostaje
w bazie; jej [wcześniejsza próba A/B](experiment-15-berserker-mp-visualization.pl.md)
nie jest tym samym eksperymentem co obecny cache HUD.

Według [analizy pomocnika #21](https://github.com/HeisenbergC29/autoplay-xcom2/issues/21)
v18 dopasowało szablon MP i wykonało dwa ciosy bez dawnego redscreen,
lecz później nastąpiło zawieszenie w fazie wroga. Nie ma podstaw do
utożsamienia go z wcześniejszym potwierdzonym wyjątkiem v17. Ukryty HUD
sam nie dowodzi przyczyny. Historyczne v19 izoluje odczyty tekstu HUD.
[Instrukcja porównania v18/v19](experiment-17-hud-polling.pl.md).

[Raport v15](report-2026-11-04-v15-stops.pl.md): `SabotageCC`,
trudność 3, **FAIL** w turze 18, 80 przyjętych rozkazów i zero odrzuceń
przez silnik. Częściowy wynik porównawczy −17500. Jedno przestawienie
przed strzałem 47→68%: **POTWIERDZONE**; próby chmury trucizny i kombinacji
AP: **NIEURUCHOMIONE**. Trzy zatrzymania przed rzutem granatu są osobnym
błędem od odrzuconego rozkazu. Próby bieżącej rewizji v20 pozostają osobne
od tamtych wyników.
[Zakres i scenariusze v17](tactics-v17.pl.md) ·
[Zachowane scenariusze v16](tactics-v16.pl.md).

Od bieżącej serii **PASS wymaga zwycięstwa oraz wyniku misji > 0**.
Zwycięstwo przy zerze lub wyniku ujemnym daje FAIL próby; oficjalne zwycięstwo
gry pozostaje zapisane. Brak pewnego końcowego wyniku daje **NIEPOTWIERDZONY**,
bez zaliczenia na podstawie częściowego `~wynik/—`. Dawne opisy zwycięstw
v8 zachowują znaczenie historycznego wyniku gry.

V20: potwierdź `revision=mission-report-v20`, pole `full_intel_enabled`
oraz startupowe `Full intel|...enabled=True|map_revealed=True`. Sprawdź
odkrycie terenu, dojście do wroga poza LOS bez strzałów przez przeszkody,
aktualizację listy po zabiciu i pojawieniu się jednostki oraz zachowanie
pilnych celów, ratunku i ewakuacji przy znanym dalekim wrogu. Pozycja w
pełnej wiedzy nie może sama tworzyć natywnego celu ataku. Sprawdź też
wariant `EnableFullIntel=false` od nowego uruchomienia misji; nie wymagać
odtworzenia mgły po jej ujawnieniu w już trwającej próbie. Widoczność modeli
oceniaj osobno od odkrycia terenu i wiedzy planera. Zachowaj OFF/pauzę.

Zachowaj scenariusz cache HUD z v19: potwierdź `HUD score polling`
z rewizją aktualnej kompilacji, odczyt
przy F8 ON/OFF, pierwszym pokazaniu, zmianie historii i okresowo przy
stabilnej historii. Zmiana historii jest widoczna na następnym odświeżeniu
statusu, około 0,25 s; stabilny tekst może pozostać przez około 1 s plus
opóźnienie planowania UI. Wynik końcowy musi być odczytany bez cache HUD.
Przy częstych zmianach historii odczyt może pozostać przy około 4 Hz.
Porównuj podsumowania `GetTotalScore - TotalScore:`, nie wszystkie wiersze
ScoreType. Oceniaj osobno częstotliwość odczytów i zawieszenie.

Zachowaj scenariusz MP z v18: sprawdź startupowe `MP visualization patch`
z rewizją aktualnej kompilacji, `templates > 0`,
`matched > 0`, `skipped=0`, a potem rzeczywisty `DevastatingPunchMP`.
Pominięte warianty trudności dają wynik nierozstrzygający.
Bez tych danych brak redscreen
nie potwierdza działania poprawki. Porównanie wymaga dwóch kompilacji i
restartów gry; F8 OFF nie wyłącza poprawki szablonu. Zapis z późnej fazy bez
nowego ciosu nie weryfikuje wizualizacji. Późniejszą awarię oceniaj osobno.

Zachowaj scenariusze v17: legalne `DevastatingPunch` i `DevastatingPunchMP` Berserkera
sterowanego przez gracza oraz zachowanie ograniczeń AP, ścieżki, zagrożeń,
wsparcia i kontry. Własny żołnierz przejęty aktywną odwracalną kontrolą
umysłu nie może być wybrany jako cel ataku ani narażony przez wybrany granat.
Sprawdź zachowanie przeciw zwykłemu wrogowi i powrót kontroli po zabiciu
źródła, jeśli wystąpi taka okazja. Sam brak ataku na przejętego żołnierza
bez rozpoznanego efektu w raporcie nie dowodzi działania nowej ochrony.
PR #11 z filtrem pamięci marszu wymaga poprawek i nie jest objęty v17.

Zachowaj scenariusze v16: odrzucenie nieaktualnego granatu bez wyłączenia autoplaya,
wybór innej legalnej akcji, blokadę powtórzenia przy tej samej historii,
ponowienie po zmianie stanu i limit trzech niepowodzeń danej zdolności
w turze. Kontrola wybuchu, celów i sojuszników nadal musi działać.
Przy kończeniu tury sprawdź żądanie zwracające `false`, ale zatwierdzające
`SkipTurn`, opóźnione zatwierdzenie, zmianę gracza/tury, pauzę i rzeczywisty
brak potwierdzenia. Żaden z tych przypadków nie może wielokrotnie wysłać
tego samego końca tury.

Zachowaj scenariusze V15: porównaj słaby podstawowy strzał przy dwóch AP z bezpiecznym ruchem
poprawiającym celowanie, a dobry strzał z małą możliwą poprawą. Sprawdź
niewystarczające AP po ruchu, dwupunktowy strzał snajpera, różne typy AP,
wsparcie lub leczenie przed końcem tury i każdorazowe ponowne sprawdzenie
legalności akcji. Prognoza z docelowego pola jest heurystyką; rzeczywistą
szansę po ruchu odczytuje gra.

Sprawdź wyjście z wielopolowej chmury trucizny na czyste widoczne pole,
pozostający status po wyjściu, odporność, ogień i kwas na początku lub dalej
na trasie, brak bezpiecznego wyjścia oraz zakaz ponownego wejścia po czystym
polu. Nie wolno utożsamiać `Poisoned` z odpornością ani samym brakiem chmury.

Zachowaj scenariusze v13/v14: broń i zdolności widocznego kontaktu, zombie,
kontra Mutona, ekspozycja przy zasadzce i aktywne Marked. Dla konfiguracji
Marked oczekiwane są `marked_aim_bonus=10` i `target_status_weight=1.1`,
a po wygaśnięciu 0 i 1. Raport v14 nie sprawdził tego przypadku.

Profil punktacji v2 pozostaje bez zmian: `~0/—` na początku zwykłej misji,
pierwsza rana −1000, potwierdzona strata −5000. Wykrwawienie nie udaje śmierci,
leczenie nie zwraca kary, a F8 nie zeruje oceny.

Wcześniejszy materiał to [ponowna próba GasStation na v9](report-2026-11-03-legacy-v9.pl.md):
Dowódca, **FAIL** w turze 7, wynik gry **−10000** przy maksymalnej puli 46000.
Podejście i stabilizacja snajpera: **PASS**. Legalny pickup łupu: **NIEZAREJESTROWANY**.
Ten sam raport zawiera zwycięstwo v8 w `SabotageCC` na trudności 3.
Wcześniejsze zwycięstwo v8 w pierwszej misji Legacy pozostaje osobną próbą;
Cemetery nadal nie ma udokumentowanej próby autoplaya.
V10 działało w zwykłej niepunktowanej misji. Wyświetlanie liczb Legacy
oraz bieżące zmiany v20 nadal wymagają kompilacji Windows i próby w grze.
[Instrukcja Legacy](legacy-test.pl.md) · [Licznik v12](score-display-v10.pl.md).

Dotychczasowy wynik zgłoszony przez użytkownika: **PASS** — mod wydaje rozkazy;
**PASS** — pierwsza misja Legacy na v8; **FAIL** — dotychczasowe próby
Gatecrashera. Dawna paczka 0.1.0 alpha miała blokadę HUD-u. Wynik jednej misji
nie potwierdza pełnej obsługi wszystkich etapów ani innych rodzajów misji.
[Scenariusze taktyczne i kompilacja z zachowanym SDK](tactics-update.pl.md).

Nowe próby powinny korzystać z wersji zawierającej [rejestr misji](mission-recording.pl.md).
Sprawdź słaby strzał kontra overwatch, ranną jednostkę pod ostrzałem kontra
hunker, gaszenie Burning oraz ochronę Aid Protocol. Po porażce zachowaj raport
ZIP z `Diagnostics\Collect-MissionRecording.ps1` i poziom trudności. Test
rejestratora wymaga prawdziwej gry: obecność testów analizy logów nie potwierdza,
że nowy kod skompilował się i zarejestrował rzeczywistą misję.

Rewizja `mission-report-v4`: z zapisu sprzed pierwszego ataku sprawdź, czy
przedni strzelec zachowuje akcję, a pozostali ustawiają się i włączają overwatch
przed ujawnieniem oddziału. Sprawdź także brak bezpiecznej trasy, brak dostępnego
overwatch i wyczerpany budżet przygotowań: atak musi móc nastąpić bez zapętlenia.
Porównaj bezpieczny Frag 3–4 przeciw 4 HP ze strzałem około 30%, potem z dobrym
strzałem około 80%; wyjątek dla granatu nie powinien wypierać dobrego strzału
ani omijać kontroli sojuszników i obiektów celu. Prześlij raport również po
zwycięstwie, aby dało się ocenić wynik całej misji.

Rewizja `mission-report-v5`: przy tylnym żołnierzu ponad 8 pól od strzelca
otwierającego i poza zasięgiem wzroku celu sprawdź bezpieczny ruch doganiający
przed atakiem. Przybliżenie poniżej 2 pól lub wzrost ryzyka nie powinny wystarczyć.
Po ruchu nadal ma pozostać AP; limit przygotowań nie może powodować pętli.
Sprawdź geometryczną osłonę i LOS w `move_threat_preview`, w tym widoczność
z domyślnej pozycji oraz sytuację wymagającą wychylenia strzelca.
Przy granacie sprawdź, czy `area_target_preview` odpowiada wybranemu punktowi
i późniejszym `result_target`, także przy aktywnym Explosive Falloff.

Wyniki zapisuj osobno: PASS / FAIL / NIEURUCHOMIONY. Kompilacja nie potwierdza działania. Zacznij od osobnego testowego zapisu bez Ironman, z WOTC i wszystkimi oficjalnymi dodatkami, bez innych modów.

## Kompilacja i wejście

1. Zbuduj czyste pakiety SDK i mod; potwierdź brak błędów, świeży `.u` i poprawne polskie znaki po instalacji.
   Ostrzeżenia `Import failed ... property is config` dla `AutoplayXCom2` muszą zniknąć. Osiem znanych ostrzeżeń bibliotek SDK nie zastępuje osobnej kontroli logu moda. Sprawdź, że paczka zawiera `XComAutoplayXCom2.ini` z listami zdolności i `XComGame.ini` z identyfikatorem DLC.
2. Uruchom istniejącą misję z modem. Bez włączenia autoplaya żaden rozkaz nie może zostać wydany.
3. Przyciskiem i F8 włącz/wyłącz automat kilkukrotnie w jednej turze, podczas ruchu, strzału, tury obcych, Lost oraz reakcji władcy. Po wyłączeniu może skończyć się tylko rozpoczęta akcja, bez kolejnej.
4. Escape i pauza: brak nowych rozkazów. Po wczytaniu zapisu, restarcie misji i powrocie z kolejnej misji automat ma być wyłączony, panel pojedynczy.
5. Otwórz menu, wybór celu, ekran przedmiotu i dialog fabularny. Automat nie może sam zamykać nieznanego ekranu ani rozgrywać pod nim tury.
6. Wyłącz i włącz automat przed pojawieniem się jego ekranu hakowania, na ekranie wyboru nagrody oraz w czasie animacji hacka. Powinien wznowić tylko ten sam własny kontekst. Późniejszy ręczny hack tym samym żołnierzem i zdolnością nie może zostać przejęty.

## UI

- V12: nad przyciskiem widoczne `punkty/maksimum`, z wielkością czcionki
  przycisku. Sprawdź odświeżanie przy OFF, po zwinięciu przycisku i po wczytaniu
  zapisu ze środka misji. W kolejnym etapie Legacy wynik nie obejmuje wcześniejszych
  misji, a maksimum nie maleje po zabiciach i stratach. Ujemny wynik ma zachować
  minus. W v12 zwykła misja bez punktacji pokazuje `~wartość/—`; natywny
  wynik bez maksimum daje `wartość/—`. Pole przepuszcza kliknięcia mapy.
- W zwykłej turze XCOM z dostępnymi akcjami włącz autoplay. Nakładka tury i licznik celu misji (`UITurnOverlay`, `UISpecialMissionHUD`) nie mogą powodować stałej pauzy; automat powinien wydać legalny rozkaz.
- Sprawdź rzeczywiste menu, dialog, sekwencję blokującą sterowanie i ręczne celowanie. Nowe rozkazy mają czekać; po zamknięciu menu lub anulowaniu celowania automat może wznowić pracę. Ekrany znajdujące się pod HUD-em nie powinny samodzielnie powodować pauzy.
- Przy utrzymującej się blokadzie sprawdź status i wpisy `AutoplayXCom2` w `Launch.log`. Log powinien podawać przyczynę zmiany stanu i dane ekranu, bez powtarzania identycznego wpisu w każdej klatce.
- 1920×1080, 2560×1440, ultrawide i różne skale UI: przycisk czytelny, znacznik w obrębie ekranu.
- Wszystkie stockowe elementy HUD, w tym ewakuacja, pasek umiejętności, lista przeciwników, podgląd Wybranego i wskaźniki celów: sprawdzić kolizje i poprawić domyślne położenie, jeśli wystąpią.
- Wskaźnik pozostaje widoczny i reaguje na hover; wygaszony przycisk nie przechwytuje kliknięć pola bitwy; najechanie i przejście ze znacznika na przycisk nie powoduje migotania.
- Włączony znacznik zielony, wyłączony niebieski; statusy i skrót czytelne w PL/EN.

## Reguły walki

- V9 — wykrwawienie: ratownik z rzeczywistym ładunkiem i AP powinien podejść
  bezpieczną znaną trasą, zachować koszt stabilizacji i użyć jej dopiero przy
  legalnym celu. Sprawdź brak ładunku, ostatnią turę wykrwawiania, niedostępną
  trasę, przeszkodę przy pacjencie i zagrożonego rannego ratownika. Żołnierz
  ustabilizowany nie powinien pozostawać celem ponownej stabilizacji.
- V9 — łup: sprawdź darmową natywną akcję i automatyczny pickup po ruchu,
  upływ terminu łupu, brak LOS, wsparcie i zagrożenia na całej trasie. Widoczny
  przeciwnik, pamiętany niedawny kontakt, wykrwawienie w oddziale, ewakuacja,
  gotowy cel albo aktywny licznik misji powinny blokować wycieczkę po łup.
- Ranger, Specialist, Grenadier, Sharpshooter, Psi Operative, Reaper, Skirmisher, Templar, SPARK; brak amunicji, leczenie, wykrwawienie, melee, darmowe akcje i Lost headshot.
- Weryfikacja każdej domyślnej nazwy umiejętności, ograniczeń ładunków, cooldownów, trafień, pancerza i osłon. Brak strzałów do ukrytych wrogów i VIP-a do schwytania.
- Podpalenie/kwas na początku trasy i dalej na trasie: można wyjść z zagrożonego pola, ale nie przechodzić przez kolejne.
- Ruch przez drzwi, różne piętra, drabiny i blokady; prawidłowy koszt AP oraz ruch dołączonego GREMLIN-a. Brak pętli i rozkazów bez AP.
- Włącz automat po ustawieniu ręcznych punktów trasy: stara trasa nie może zostać dołączona do nowej ani do ruchu innego żołnierza. Przy ręcznym celowaniu automat ma czekać na zakończenie lub anulowanie celowania.
- Panika, ogłuszenie, kontrola umysłu, przejęte jednostki: wyłącznie jednostki rzeczywiście należące do lokalnego gracza.
- Żadnych dodatkowych AP, wymuszonego trafienia, odczytu ukrytego rzutu hacka ani sztucznego zwycięstwa.
- Granaty Frag/Alien: skupiona grupa wrogów, sojusznik lub cywil w obszarze, VIP, obiekt celu, zbiornik paliwa na trasie i w wybuchu, piętra nad wybuchem, rzut i granatnik. Faktyczny punkt lądowania i lista trafionych obiektów muszą odpowiadać natywnej trajektorii. Brak przejęcia grafiki trajektorii gracza podczas samej oceny.
- Eksploracja: brak widocznych wrogów, pełna kolejka pól, niedostępny cel dla jednego żołnierza, zmiana tury, zużycie wszystkich AP i przebudowa mapy. Nie może wystąpić nieskończone czekanie ani zniknięcie reszty niezeskanowanych pól po zapełnieniu kolejki.

## Cele i zakończenie misji — macierz obsługi v21

**Status w tabeli dotyczy implementacji, nie zaliczenia misji.**
`Częściowe` = istnieją ogólne legalne akcje, ale nie ma dowodu wykonania
wszystkich etapów. `Brak dedykowanego planera` = nazwa misji/etap
istnieje w SDK, lecz bieżący mod nie ma jawnego modelu jego całej sekwencji.
`Niezweryfikowane` = brak kompletnego wyniku gry dla tej kategorii.
**PASS** wymaga łącznie: wszystkich wymaganych celów, natywnego
`outcome=win` oraz **pewnych końcowych punktów misji > 0**.
`score` w wyborach AI ani `MaxScore` nie są punktami misji.

Źródła implementacji: `APX_MissionPlanner.uc` (`ChooseInteraction`,
`IsObjectiveAbility`, `FindGoal`, `ShouldEvacuate`, `ChooseMove`),
`APX_EvacPlanner.uc` (`PrimaryObjectivesCompleted`,
`ChoosePlacement`), `APX_CombatPlanner.uc` (`ScoreObjectiveAttack`,
`ChooseAction`) i `APX_Controller.uc` (`HandleOwnedHack`,
`MakeDecision`). Nazwy misji niżej pochodzą z dostarczonego SDK
`X2MissionSet.uc` oraz odpowiadających modułów DLC;
`SeqAct_DisplayMissionObjective.uc` zarządza wyświetleniem/oznaczeniem
celów, **nie** zastępuje planowania etapów w modzie.
Wszystkie źródła SDK są prywatne i nie są publikowane w repozytorium.

| Rodzaj / natywne misje (przykłady) | Obecny zakres kodu | Zweryfikowana próba / punkty | Luka i kolejny test |
| --- | --- | --- | --- |
| Eliminacja i sabotaż pomnika / `SabotageCC` | **Częściowe**: natywne ataki, przechodzenie mapy i rozpoznane cele | v21 `SabotageCC`: **win**, HUD około **~300** (porównawcze, nie końcowe). **Niepotwierdzony PASS** | Zarejestrować końcowe wiarygodne punkty i wykonanie wszystkich celów; nie mylić `win` z dodatnim wynikiem |
| Wyzwania TLE / `ChallengeAbductionGasStation` | **Częściowe**: akcje dystansowe, obrona i dostępne cele; brak planu izolowania grup | v21: **loss**, **−12 600** końcowych punktów natywnych | #20 grupowe zatrucie przez `PoisonSpit`, #31 izolowanie grup, #28 pilne leczenie; osobna próba po zmianie |
| Sabotaż / `SabotageTransmitter`, `SabotageAlienFacility`, Blacksite (`AdventFacilityBLACKSITE`) | **Częściowe**: `Interact_PlantBomb`, `Interact_TakeVial`, legalne cele, ruch do znacznika; v21 specjalny ruch `BerserkerMP` do bomby | v21 Blood Killer (`SabotageTransmitter`): **loss**; **+700** jako końcowy wpis `CMPT_TotalScore` i HUD, bez potwierdzonego `game_score.mission_points` | #29: zweryfikować *właściwy* bomb emplacement i legalną interakcję; następnie ewakuację/koniec etapu; brak ręcznego wymuszania celu |
| Hack / dane: `HackWorkstation`, `RecoverItemADV`, `RecoverItemTrain` | **Częściowe**: `Hack_Workstation`, `Hack_ObjectiveChest`, `Hack_Scan`; rozpoznaje własny ekran hakowania i dostępne nagrody | **Niezweryfikowane**; punkty **brak danych** | Przejść hack → animacja → `MissionObjectiveMarkedCompleted` → prawidłowe zakończenie; zarejestrować natywne punkty |
| Zniszcz/obroń obiekt: `DestroyRelay`, `ProtectDevice` | **Częściowe**: ocena ataku na obiekt misyjny, ochrona sojuszników/obiektów w planie granatu | **Niezweryfikowane**; punkty **brak danych** | Dowieść, że atak niszczy tylko właściwy cel, obrona nie niszczy chronionego urządzenia, działa timer i wynik |
| VIP/ewakuacja: `ExtractVIP`, `RescueVIP`, `NeutralizeTarget`, `CovertEscape` | **Częściowe**: rozpoznanie `ObjectiveInfo`, ratunek, przenoszenie, `ShouldEvacuate`, `ChoosePlacement` | **Niezweryfikowane**; punkty **brak danych** | Cała sekwencja porwania lub ratunku, stan niesionego VIP-a, ewakuacja wszystkich wymaganych jednostek, natywne `win` |
| Odwet/cywile: `Terror`, `ChosenRetaliation`, `GatherSurvivors` | **Częściowe**: ogólny ratunek i walka, możliwe interakcje/cel `ObjectiveInfo` | **Niezweryfikowane**; punkty **brak danych** | Limit cywilów, ratunek i neutralizacja przeciwników; nie zapętlać się na nieaktywnym markerze |
| Skrzynie: `SupplyExtraction`, napad na zaopatrzenie | **Częściowe**: `Interact_MarkSupplyCrate`, trasowanie do celu, legalne akcje | **Niezweryfikowane**; punkty **brak danych** | Termin, liczba skrzyń, oznaczanie przed ewakuacją oraz prawdziwe przejęcie i punkty |
| Etapy fabularne `LostAndAbandonedA/B/C`, pierwsze wydarzenia Legacy | **Brak dedykowanego modelu przejść**: ogólne akcje i cel; samouczek nie jest obsługiwanym wariantem | Jedna historyczna pierwsza misja Legacy v8 wygrana; nie świadczy o całej kampanii. Punktów tej próby nie potwierdzono według obecnego kryterium | Przetestować przejście A→B→C, eskortę/carry, zmiany jednostek i stan zwycięstwa każdej części |
| Alien Nest (`DLC_2/X2MissionSet_DLC_Day60.uc`) | **Brak dedykowanego planera misji**; dostępna ogólna walka/nawigacja | **Niezweryfikowane**; punkty **brak danych** | Sekwencja fabularna, silne jednostki, wymagane przejścia/zdarzenia i prawidłowy finał |
| Lost Towers / Shen: `LastGift`, `LastGiftB`, `LastGiftC` (`DLC_3`) | **Brak dedykowanego planera trzech etapów**; ogólne interakcje i ataki | **Niezweryfikowane**; punkty **brak danych** | Przejście poziomów, przełączniki, specjalne zdolności/sojusznik, boss i trzykrotna kontrola celu |
| Twierdza Wybranego: `ChosenStrongholdShort/Long`, `ChosenShowdown_*` | **Częściowe**: `Interact_ActivateAscensionGate` i możliwe ataki na cel, bez kompletnego scenariusza portal–sarkofag–boss | **Niezweryfikowane**; punkty **brak danych** | Weryfikacja portalu, urządzenia/sarkofagu, nawrotów bossa i końcowego warunku zwycięstwa |
| Obrona Avengera: `AvengerDefense`, `ChosenAvengerDefense` | **Częściowe**: ogólne ataki na obiekty/oddziały i cele ewakuacyjne | **Niezweryfikowane**; punkty **brak danych** | Rozpoznanie właściwego urządzenia, ochrona Avengera, warunki odwrotu, przejścia skryptu i końcowy wynik |
| Finał: `AssaultFortressLeadup`, `DestroyAvatarProject` | **Brak dedykowanego modelu pełnej sekwencji**; obecne tylko działania ogólne | **Niezweryfikowane**; punkty **brak danych** | Awatary, przejścia i skryptowane etapy, zachowanie krytycznych celów, potwierdzenie finału |

### Priorytety wynikające z braków

1. **P0 — ukończenie objective i dokładne punkty:** Blood Killer/#29,
   a także nieznany końcowy score zwycięskiego `SabotageCC`. Połączyć
   log celu z natywnie dostępną interakcją, **bez fikcyjnego zaliczenia**.
2. **P0 — stabilność i straty:** niezakończone dochodzenie #15/#21/#29;
   w GasStation eliminować skupienie pod AoE (#20) i pilnie dostępne
   leczenie (#28), chroniąc wynik przed karą −5000 za zgon.
3. **P1 — świadoma sekwencja grup i ukrycia:** #31 oraz #12/#32.
   Nie spowalniać misji, w których rzeczywisty timer albo punkty
   `CMPT_CompletedObjective` maleją z turą. `HasActiveMissionDeadline`
   rozpoznaje `XComGameState_UITimer`, ale nie wszystkie reguły punktowe.
4. **P1 — VIP/carry/evac i przejścia etapów:** dołożyć próby źródłowych
   etapów `LostAndAbandonedA/B/C` i `LastGift/B/C`; dopiero po logach
   wystawiać osobne, małe issue dotyczące rzeczywiście brakujących akcji.
5. **P2 — pozostałe fabularne misje:** Alien Nest, Twierdza Wybranego,
   AvengerDefense i finał; nie ogłaszać wsparcia na podstawie samej
   listy `IsObjectiveAbility`.

Żadna kategoria nie jest na dziś potwierdzona jako spełniająca
projektowy warunek „wszystkie cele + natywne zwycięstwo + znany
wynik punktowy > 0” na rewizji v21. Raporty prywatne pozostają poza repo.

## Punktacja każdej symulacji

Sprawdź `attempt_verdict` niezależnie od `outcome`: zwycięstwo i pewny
wynik > 0 dają `pass`, zwycięstwo z wynikiem <= 0 lub porażka gry dają
`fail`, a niepełne dane uniemożliwiają zaliczenie i dają `unknown`.
Przypadki obejmują dodatni, zerowy i ujemny wynik, brak końca, niepełną
historię, konflikt powtórzonych rekordów i przeniesione punkty Legacy.

Uruchom aktualny analizator dla każdego raportu, także Gatecrashera i innych misji
bez oficjalnych punktów. Sprawdź obecność `game_scoring.comparison` z profilem
`wotc_legacy_observed_v2`, listą składowych i brakujących danych. Jest to wspólna
miara porównawcza oparta na regułach gry; nie dodaje punktów do stanu misji.
Wcześniej podane ręcznie wartości zostały zastąpione regułami odczytanymi z gry.
V2 zaczyna od zera; baza +6000 na kwalifikowanego żołnierza w v1 została
usunięta jako niepoparte założenie. Archiwalny v1 zachowujemy osobno.
Nie porównuj sum obu profili bez przeliczenia.

Przypadki analizy: pierwsza rana kontra ponowne obrażenia i leczenie, śmierć
kontra wykrwawienie, potwierdzone fabularne wyłączenie, przeciwnik przejęty
kontrolą umysłu, przeciwnik przywołany i z posiłków, opcjonalny cel, ratunek
cywila, późne włączenie F8 i urwany log. Brak danych nie może dawać pozornie
pełnego wyniku ani zaliczać wszystkich celów na podstawie zwycięstwa.

### Oficjalny wynik Legacy

Przy każdej misji zapisuj osobno: wynik, numer etapu, tury, zgony, wyłączenia
i rany, oficjalny wynik punktowy misji oraz skumulowany, ewentualne restarty
i ręczne działania. Medal zapisuj, gdy został faktycznie przyznany; SDK
porównuje skumulowany wynik z progami po zakończeniu całej drabinki.

Punkty zależą m.in. od celów, przeciwników, tur, obrażeń i przeżycia oddziału.
Leczenie nie odtwarza utraconej premii za brak obrażeń. Fabularna jednostka
pozostająca żywa po wyłączeniu może ponieść karę punktową jak za utratę.
Nie należy odtwarzać wyniku tylko z końcowego HP i liczby zabitych.

V15 dodaje `mission_points`, `mission_points_known` i `mission_final`.
Do oceny próby potrzebny jest znany końcowy wkład bieżącej misji, po
zatwierdzonym zakończeniu i nadrobieniu historii. Odczyt nie obiecuje nagród,
które gra może zapisać później; porównaj go z ekranem podsumowania.

V9 zapisuje odczyty `game_score.cumulative_score` tylko dla właściwego etapu.
`recording_delta` obejmuje okres od pierwszego do ostatniego odczytu, nie
gwarantuje punktów całej misji. Sprawdź przejście do kolejnego etapu: nie wolno
przypisać jego wyniku poprzedniej misji. Końcowe premie po zamknięciu rejestracji
mogą wymagać porównania z ekranem podsumowania.

`score` w `APXREC` oznacza wewnętrzną ocenę rozkazu. `MaxScore` w tabelach
`XCom_Challenge` oznacza początkową maksymalną pulę. Żadne z tych pól nie jest
potwierdzeniem zdobytej punktacji. Przy braku oficjalnej liczby wpisuj
**NIEZAREJESTROWANY**, bez wyliczania medalu z przybliżeń.

## Warunki awaryjne

Brak planu ma zatrzymać automat, a nie przepuszczać dowolnie wiele tur. Odrzucona akcja zatrzymuje go bez pętli ponawiania. Limit działań zabezpiecza nietypowe darmowe zdolności. Wyjście z misji usuwa aktora kontrolera i odnośniki do ekranów. Rozgrywka multiplayer, replay i samouczek mają odrzucić włączenie.
