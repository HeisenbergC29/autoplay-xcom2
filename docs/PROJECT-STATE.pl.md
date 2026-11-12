# Stan przekazania projektu — 12 listopada 2026

To punkt startowy po pierwszym przeglądzie importu pomocnika. Bieżące issue i PR-y mogą zawierać nowsze
ustalenia; po integracji aktualizuj ten dokument, gdy zmienia się baza lub
poziom potwierdzenia działania.

## Baza kodu

- Bieżąca rewizja przygotowywanych źródeł: `mission-report-v26`, obsługa
  natywnych ofert DevastatingPunchMP przeciw potwierdzonemu przekaźnikowi
  SabotageTransmitter (#46 / PR #51). Zachowuje pełne kontrole ścieżki,
  limituje priorytet poniżej gotowego PlantBomb/pilnej pomocy i kończy
  preferencję po natywnym ukończeniu X4. Profil radialnych zdarzeń pozostaje
  konserwatywną blokadą; nie ma solvera wybuchów wtórnych.
  [Zakres przekaźników](experiment-46-relay-melee.pl.md). #29 dodaje rzeczywiste
  pole interakcji: aktor PlantBomb, natywne punkty, footprint dużej jednostki
  i osiągalna kotwica z ograniczonym wyszukiwaniem. Marker pozostaje jawnie
  niepotwierdzonym fallbackiem, a Sweep wymaga native bCompleted.
  [Zakres podejścia](experiment-29-native-plant-goal.pl.md).
  Windows/game v26: **NOT RUN**; końcowy SHA wskazuje LEAD w #4.
- Baza v25: `eae4db165f679d6cac56d6e207900106c4ed3f55`, obserwacyjny
  heartbeat długiego oczekiwania (#40 / PR #50), rozróżnienie krytycznych
  zdarzeń porażki od checkboxów UI oraz diagnostyka obiektów przekaźników
  (#46 / PR #47) oraz zatwierdzony przez użytkownika odczyt bieżącego
  zapisanego celu patrolu (#48 / PR #49, tylko przy pełnym rozpoznaniu).
  Nie dodaje jeszcze planu zasadzki i nie naprawia zawieszenia/PlantBomb.
  [Heartbeat](experiment-40-wait-heartbeat.pl.md),
  [nieudane cele i przekaźniki](experiment-46-critical-objective-relays.pl.md).
  [Aktualny punkt grupy](experiment-48-patrol-waypoint.pl.md).
  [Raport v25](report-2026-11-12-v25.pl.md) potwierdza grę tej rewizji,
  bez dokładnego SHA/logu kompilacji: GasStation loss z −21200 końcowymi
  punktami; Blood Killer ręczny OFF, dwa nieudane cele UI i brak native end
  lub końcowego score. Telemetria działa i pokazuje postęp historii.
  PR #43 zamknięto bez scalenia. Zgoda na aktualny punkt z 11 XI nie
  obejmuje prywatnej wiedzy IsEngaged/HasAbsoluteKnowledge; te odczyty
  usunięto. Punkt ma nieznane przyszłe użycie i nie jest całą trasą.
- Baza v24: `defdcee43945a0755de6d069d7690cd215c83c63`, kontrola
  ekspozycji wczesnej trasy, miękka kara samotnego otwarcia walki,
  wiedza o zdolnościach w wagach zagrożeń i ograniczona ocena wybuchowych
  osłon (#31 / PR #44), a także rzeczywista geometria chronionych obiektów
  przy pustym obrysie granatu (#38 / PR #45). Zachowuje concealment v23, formację AoE v22,
  politykę PlantBomb, ostatni AP i limity ryzyka v21 oraz pełne rozpoznanie v20.
  PR #43 pozostaje poza integracją: wyjątek ostatniego AP omijał zabezpieczenia.
  [Zakres ruchu i otwarcia](experiment-31-safe-opening.pl.md),
  [geometria granatu](experiment-38-launcher-geometry.pl.md).
  [Raport v24](report-2026-11-11-v24.pl.md) potwierdza uruchomienie rewizji
  w grze, bez dokładnego SHA i osobnego logu kompilacji: SabotageCC native
  win, lecz +6800 HUD / +11800 rekonstrukcji tylko częściowo; GasStation
  loss z −10700 końcowymi punktami; Blood Killer ręczny OFF bez wyniku.
  Późniejszy napis timera nie identyfikuje sam krytycznej porażki celu.
- Baza v23 po porządkowaniu ostrzeżeń: `64c28e76b035bcda92a0ecc902f38ed5c889f88e`.
  [Raport v23 z 11 XI](report-2026-11-11-v23.pl.md): SabotageCC loss
  z częściowymi punktami, GasStation loss z natywnym −10600 finalnym,
  Blood Killer przerwane ręcznie bez wyniku. Kompilacja wcześniejszego v23
  zakończyła się bez błędów i z 10 ostrzeżeniami; nie jest dowodem kompilacji v24.
- Baza v22: `75a83365dc9f862080dc3e8bab22399c1f875a29`. [Nowy raport](report-2026-11-07-v22.pl.md)
  potwierdza v22 i parametry formacji w trzech sesjach: SabotageCC loss,
  GasStation loss z −10600 finalnymi punktami oraz potwierdzone przez
  użytkownika zawieszenie Blood Killer bez końcowego wyniku. Osobny log
  jest identyczny z najnowszym w ZIP-ie; backupów nie doliczać do v22.
- Baza integracji narzędzi v21: `e81ae2969ed122549be3188ef5c7b2cc9149ac24`.
  PR #35 i #36 dodają pewność punktów/diagnostykę analizatora oraz macierz
  misji; nie zmieniają rozgrywki. Baza runtime v21 po poprawce kompilacji:
  `d84a849b13743e5a66718709c2610d14b35a985a`.
- Próba kompilacji v21 ujawniła jeden błąd: zbędne `string(sType)` w
  APX_MissionPlanner.uc. Poprawka #33 usuwa rzutowanie pola, które już ma
  typ string, bez zmiany taktyki i rewizji v21. [Nowszy raport v21](report-2026-11-07-v21.pl.md)
  potwierdza trzy uruchomione, zakończone misje i brak reprodukcji awarii;
  nie zapisuje dokładnego SHA kompilacji.
- Baza v20: `dc0ea3a3eecff3b85169128786bb5a51983ce76e`. [Nowy raport](report-2026-11-06-v20.pl.md)
  potwierdza dwie sesje v20: GasStation loss z natywnym −7600 oraz Blood Killer
  zakończony awarią bez wyniku. Brak nowego folderu crasha/dumpa jest potwierdzony
  przez użytkownika. To nie dowód wyeliminowania wcześniejszych problemów.
- Baza v19: `5e9d9eacbe1bfd9ea3f6c178c697065b0a7cbc0c`. Zachowuje cache
  tekstu HUD z PR #22 i integrację #24.
- Historyczny eksperyment HUD porównywał v18
  `e30bf6a18ac6a35a4644e7b09a91157d85c0f518` z v19
  `5e9d9eacbe1bfd9ea3f6c178c697065b0a7cbc0c`. V20 jest osobnym etapem.
- Baza porównawcza v17: `ba4550a8495c5c7d504eca681a6465b2c433ae37`.
  PR #16 scalono jako `42b36d4`; kolejne gałęzie zaczynaj od aktualnego
  `main`, uwzględniając późniejsze integracje.
- Zachowany bazowy commit v16: `9458b185e6602a07d448010c45bc5aeb74fd8d80`.
- Opublikowany kod v15 do porównania:
  `9832d72d14b75adb110a1d5ac74a32e290306b0e`. Dokładną bazę swojego
  repozytorium pomocnik podaje w inwentaryzacji; nie zakładamy jej bez SHA.
- Przed integracją organizacji `main` pozostawał na `ed74176`; historię
  opublikowanych prac scalono przez PR #5 (`dfd9b27`). Historyczna gałąź
  `codex/legacy-v6-threat-estimates` nie jest osobnym projektem ani nową bazą
  dla kolejnych zmian. Po opublikowaniu organizacji zaczynaj od `main`.
- Przygotowanie współpracy i CI nie zmieniło rewizji v16; v17 identyfikuje
  późniejszą integrację zachowań z PR #7 i #9.

## Co już istnieje

Kontroler legalnych akcji, cele/interakcje i ewakuacja, eksploracja, zasadzka,
podglądy granatów z ochroną sojuszników/celów, ratowanie wykrwawiających się,
zbieranie łupu, HUD punktów i rejestrator misji. Nie wszystkie misje lub
zdolności są obsłużone do końca.

V13–v15 wprowadziły wiedzę o widocznych szablonach/broni, rozpoznane melee,
kontrolę kontry, status Marked, chmury trucizny, ograniczoną prognozę ruchu
przed strzałem oraz Aid Protocol/medyczną czynność przed zachowanym atakiem.
Prognozy pozostają heurystyką, a kontroler ponownie sprawdza stan po akcji.

V16 zachowuje kontrolę granatu przed aktywacją, lecz odrzucony podgląd
powoduje ograniczone ponowne planowanie zamiast globalnego OFF. Koniec tury
potwierdza historią/zmianą gracza, ponieważ stockowe API może zwracać false
także po wysłaniu żądania. Tych poprawek nie należy utracić przy imporcie.
[Szczegóły v16](tactics-v16.pl.md).

V17 dodaje do planera `DevastatingPunch` i `DevastatingPunchMP` Berserkera
sterowanego przez gracza, używając istniejących natywnych kontroli melee.
Chroni również odzyskiwalnego własnego żołnierza z rozpoznanym aktywnym
efektem kontroli umysłu przed atakiem i granatem. Poprawki v16 pozostają.
[Zakres, źródła i próby v17](tactics-v17.pl.md).

V18 dodaje tylko flagi ukrywania nieudanego wyniku wizualizacji obrażeń
w rozpoznanym szablonie `DevastatingPunchMP` oraz startupowe podsumowanie.
Nie zmienia rozgrywki, taktyki, HUD ani punktacji. Przyczyna późniejszej
awarii pozostaje niepotwierdzona.
[Zakres i próba A/B v18](experiment-15-berserker-mp-visualization.pl.md).

V19 buforuje wyłącznie tekst punktów HUD. Status pozostaje odświeżany
co około 0,25 s, a tekst przy zmianie historii i okresowo co około 1 s
przy stabilnej historii, także przy OFF. Końcowy odczyt natywny pozostaje
niezbuforowany. Nie obejmuje nowych zmian taktyki ani punktacji.
[Zakres i porównanie v18/v19](experiment-17-hud-polling.pl.md).

V20 domyślnie włącza `EnableFullIntel=true`: lokalny XCOM może znać teren
i pozycje żywych, aktywnych wrogów poza LOS. To potwierdzona 6 listopada
zmiana zasad. Wiedza o dalekim celu pomaga planować, ale nie nadaje mu
automatycznie priorytetu lokalnej walki ani legalnego celu ataku.
Natywne akcje, AP, RNG i punktacja pozostają rozstrzygające. Odkrycie terenu
przez SDK nie gwarantuje ujawnienia modeli przeciwników.
[Zakres, ograniczenia i próba v20](experiment-25-full-intel.pl.md).

V21 preferuje podejście do PlantBomb tylko dla BerserkerMP w nieukończonej
SabotageTransmitter. Zachowuje native AP/interakcje, legalne trasy, hazardy
i wsparcie. LEAD ograniczył wyjątek ruchu do >=2 AP i domknął wspólny limit
ryzyka prefixu oraz fallbacku. Wybór glint/markera jest heurystyką podejścia;
nie gwarantuje dostępności właściwego punktu interakcji. Awaria pozostaje
osobnym problemem. [Zakres i próba v21](experiment-29-berserker-blood-killer.pl.md).

V22 nakłada dodatkowe, ograniczone koszty wspólnego obszaru: para −6,
trójka −18, czwórka −36, maksymalnie −48. Sprawdza środki między żołnierzami,
uwzględnia żywych nieprzytomnych jako możliwe ofiary, nie używa ich do wsparcia.
Brak twardego zakazu ruchu. Promień 3 jest heurystyką, nie natywną gwarancją
trafienia. [Zakres i próba v22](experiment-20-area-formation.pl.md).

V23 wydziela wspólny obserwacyjny assessor concealment, z natywną detekcją
cywilów/jednostek, widocznymi urządzeniami i wyjątkami Challenge/Infiltration.
LEAD poprawił priorytet podejścia przy ukrytym oddziale, współdzielony
budżet inspekcji przez całą decyzję oraz fallback lokalnych legalnych ruchów.
Kara za ukrycie nie nadaje nowej nielegalności ścieżce. [Zakres v23](experiment-32-concealment-route.pl.md).

Otwarte osobne zadania: przyczyna zawieszenia i próba diagnostyki #40,
#29 prawdziwe pole/obiekt PlantBomb, #28 pilne leczenie,
#31b izolowanie grup i #38 pozostałe ofensywne AoE. V25 nie naprawia
zawieszenia ani nie potwierdza PlantBomb w Blood Killer. Kary osłon i concealment
zachowują konstruktywną legalną trasę awaryjną; sześć inspekcji osłon
jest współdzielone przez całą decyzję. Brak czytania prywatnej wiedzy AI.

Wcześniejszy [raport GasStation v19](report-2026-11-06-v19-gasstation.pl.md):
porażka, 40 przyjętych rozkazów, normalne zamknięcie gry. Ostatni natywny
odczyt −20100 pozostaje częściowy: 18 klatek historii nie zostało zapisanych,
`mission_final=False`. Ta pojedyncza próba Legacy nie weryfikuje wcześniejszego
zawieszenia Challenge, odczytów `GetTotalScore` ani wizualizacji ciosu MP.

Według analizy HELPER w [#21](https://github.com/HeisenbergC29/autoplay-xcom2/issues/21)
v18 zastosowało poprawkę MP i wykonało dwa ciosy bez dawnego redscreen,
ale później nastąpiło zawieszenie. Nie ustalono przyczyny ani nowego
wyjątku ACCESS_VIOLATION. To przekazanie pomocnika, bez niezależnej analizy
nowego surowego logu przez LEAD. #20 (skupienie pod AoE) pozostaje osobnym
tematem; stary PR #11 zamknięto bez scalenia, a pomysł #10 pozostaje do przebudowy.

## Pierwszy przegląd importu

Źródło pomocnika:
[xcom2-autoplay-alternative](https://github.com/HeisenbergC29/xcom2-autoplay-alternative),
`main` na `c63d8d917be368dbee76b66ce3b7911b866f0f5e`.
Historie Git są niezależne; importowany stan początkowy odpowiadał zawartości
v15, co nie oznacza wspólnego przodka commitów.

| Temat | Decyzja prowadzącego |
| --- | --- |
| Ataki Berserkera, PR #7 | scalone; sprawdzony HEAD `5d485ad09616c224a7c7f1a2663c6dd576982bc6` |
| Ochrona kontrolowanego sojusznika, PR #9 | scalone; sprawdzony HEAD `89ebd569d546e3a695927aecab372a4aaa84b31d` |
| Pamięć marszu między turami, PR #11 | wymaga poprawek; nie wchodzi do v17 |
| Ukryta zasadzka, issue #12 | osobny temat do dalszej pracy |

## Potwierdzenie i ograniczenia

V26 po PR #51 wymaga nowej kompilacji
Windows WOTC SDK oraz próby w grze: **NOT RUN**. Dokładny SHA, wyniki
kontroli i decyzje przeglądu zapisuje LEAD w PR i issue #4.

V25: GasStation naliczyło cztery kary DeadSoldier, lecz trzy jednostki
faktycznie zginęły, a jedna pozostała żywa i nieprzytomna. Granaty gracza
mają zapisane tylko wrogie ofiary. Pięć ofert ciosu w relay474 nie dawało
kandydatury z powodu filtra MovingMelee/ProvidesPath, mimo prawidłowej
flagi objective. [Pełny wyciąg](report-2026-11-12-v25.pl.md).

V24 zachowuje potwierdzone zwycięstwo w SabotageCC, lecz częściowe
punkty nie certyfikują zaliczenia projektu. GasStation −10700 jest FAIL;
Blood Killer pozostaje UNKNOWN, bez końcowego wyniku. Przekazanie HELPER-a
o CRITICAL FAIL na podstawie samego napisu timera było zbyt mocne.

Historyczny SHA v23, kontrole i decyzja są zapisane w PR #39.
Kompilację v23 potwierdził osobny log (0 błędów, 10 ostrzeżeń), a późniejszy
raport gry zawiera dwie porażki i ręczne zatrzymanie Blood Killer bez wyniku.
Nie potwierdza wygranej ani naprawy zawieszenia.

Historyczne kontrole v22 są zapisane w PR #37 dotyczącym #20.
Kod v22 zaliczył **566 testów z prywatnymi wejściami, bez pominięć**,
oraz audyt **18 klas / 31 nazw zdolności PASS**. Geometria i zgodność
źródłowa nie zastępują natywnej kompilacji i listy faktycznych trafień.
Nowszy raport potwierdza uruchomienie v22, bez dokładnego SHA kompilacji.
GasStation −10600 pozostaje porażką. SabotageCC ma częściowy HUD około
−12100 i osobną częściową rekonstrukcję −18100; końcowy wynik nieznany.
Blood Killer ma +700 częściowo i HANG potwierdzony przez użytkownika,
bez Crash Detected. Żadna z trzech prób nie jest PASS projektu.
PoisonSpit trafia tylko jedną zapisaną własną jednostkę w v22, lecz po
wcześniejszych zgonach dwóch i utracie przytomności trzeciej; nie stanowi
to dowodu skuteczności rozstawienia. Własny granat w SabotageCC trafia
dwóch wrogów za łączne 6 obrażeń zgodnie z podglądem.

Kod v21 po poprawkach przeglądu LEAD zaliczył **547 testów z prywatnymi
wejściami, bez pominięć**, oraz audyt **18 klas / 31 nazw zdolności PASS**.
Końcowy SHA, publiczne CI i decyzja o scaleniu są zapisane w PR #30.
Pierwsza kompilacja Windows WOTC SDK v21: **FAILED**, jeden błąd
zbędnego rzutowania typu string; poprawka #33. Nowszy raport potwierdza
grę v21, bez logu i dokładnego SHA kompilacji.
Źródła nie stanowią potwierdzonej naprawy awarii ani zwycięstwa.

Po poprawkach przeglądu kod v20 zaliczył **539 testów z prywatnymi wejściami
bez pominięć** oraz audyt **18 klas / 31 nazw zdolności PASS**. Kod:
`e8aa70bef727a6a7672d400156f225896cdec1c6`. Końcowe publiczne CI i decyzja
są zapisane w PR #26 i issue #27. Późniejszy raport potwierdza uruchomienie
v20 w grze, ale nie dokładny SHA kompilacji. Zmiana pełnej wiedzy nie jest potwierdzoną naprawą awarii
ani dowodem, że każdą misję można ukończyć.

Historyczny PR #22 oraz kod integracji v19 zaliczyły **524 testy z prywatnymi
wejściami bez pominięć** i audyt **17 klas / 31 nazw zdolności PASS**.
Publiczne CI PR #22: 464 PASS / 60 SKIP oraz trzy zestawy PowerShell PASS.
Końcowe CI v19 jest śledzone w [PR #24](https://github.com/HeisenbergC29/autoplay-xcom2/pull/24).
Nowy raport potwierdza uruchomienie rewizji v19, ale nie dokładny SHA
kompilacji ani zaliczenie wersji. Samo scalenie nie potwierdza naprawy
zawieszenia; najnowsza porażka nie jest dowodem niemożności GasStation.

Historyczna integracja v18: 518 testów z prywatnymi wejściami bez pominięć,
audyt 17 klas / 31 zdolności; publiczne CI śledzone w PR #19. Raporty
pomocnika potwierdzają uruchomienie rewizji v18, ale nie dokładny SHA
kompilacji ani zaliczenie wersji.

| Dowód | Historyczna baza v17 |
| --- | --- |
| Testy Python z prywatnym SDK i configami | 513 zaliczonych, bez pominięć |
| Audyt referencji | 17 klas moda, 31 skonfigurowanych nazw zdolności |
| Pomocnicy budowania, zbierania SDK i raportów | trzy zestawy PowerShell zaliczone lokalnie w PowerShell 7.6.9 |
| Publiczny zestaw bez prywatnych wejść | 455 zaliczonych, 58 pominiętych; [CI kodu v17](https://github.com/HeisenbergC29/autoplay-xcom2/actions/runs/42021235262) |
| Pomocnicy PowerShell na Windows | trzy zestawy zaliczone w tym samym CI; to nie kompilacja WOTC |
| Kompilacja v17 w Windows WOTC SDK | brak logu kompilacji i dokładnego SHA |
| Próby z rewizją v17 w grze | dwie porażki i awaria, bez odbioru wersji |

Nowy raport v17 opisano w [issue #15](https://github.com/HeisenbergC29/autoplay-xcom2/issues/15).
Rewizja logu potwierdza uruchomienie moda, ale nie dokładny commit
zbudowanych źródeł. Potwierdzone końce tury i przyjęte ciosy są dowodem
tych obserwacji, nie skuteczności całej misji ani usunięcia awarii.

Liczby historycznej bazy v16: 505 testów z prywatnymi wejściami bez pominięć,
17 klas i 29 nazw zdolności; publicznie 450 zaliczonych i 55 pominiętych.
Scalenie źródeł i zielone kontrole nie są potwierdzeniem kompilacji moda
ani zaliczenia misji. [Osobna próba użytkownika #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).

Ostatni [raport v15](report-2026-11-04-v15-stops.pl.md): SabotageCC,
trudność 3, porażka w turze 18, częściowa ocena −17500. Trzy zatrzymania
dotyczyły tego samego podglądu granatu; przyczyna konkretnej niezgodności
nie była rejestrowana wystarczająco dokładnie. V16 dodaje diagnostykę.
Jeden ruch v15 dał przewidziane 47→68%, potwierdzone kolejnym odczytem gry.
Ta próba nie weryfikowała chmur trucizny ani kombinacji medycznej/Aid Protocol.

Historycznie v8 wygrało pierwszą misję Legacy na Dowódcy i jedną próbę
SabotageCC. To pozostaje oficjalnym wynikiem dawnych prób, ale nie potwierdza
nowego kryterium ani wygranej całej drabinki czy wszystkich misji.

## Dane i punktacja

Aktualny katalog zawiera 253 rejestracje szablonów, w tym cywilów, aliasy
i żołnierzy — nie 253 wrogów. Konfiguracja uzupełnia 196 sekcji statystyk,
177 zestawów wyposażenia i 684 odwołania parametrów broni. Dwa symbole
obrażeń proxy Feral MEC M2/M3 pozostają nierozwiązane; nie znaleziono ich
wartości, nie kopiujemy danych M1 i nie żądamy z tego powodu kolejnych archiwów.
[Źródła katalogu DLC](dlc-config-knowledge.pl.md).

Próba jest zaliczona tylko przy zwycięstwie i pewnych punktach misji > 0.
Wynik natywny i porównawczy pozostają rozdzielone; porównanie v2 startuje od
zera i jest oznaczane jako częściowe, gdy brakuje obserwacji. Nie zmieniaj
tych zasad przy przenoszeniu taktyki z osobnego repozytorium.

Inwentaryzację i dalsze przekazania zapisujemy w
[issue #1](https://github.com/HeisenbergC29/autoplay-xcom2/issues/1), zgodnie z
[procedurą importu](TEAM.pl.md#import-z-osobnego-repozytorium).
