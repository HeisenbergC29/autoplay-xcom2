# Autoplay XCOM 2 — War of the Chosen

Mod w UnrealScript automatyzujący działania oddziału w misji. Docelowy profil użytkownika: **aktualne XCOM 2 Collection ze Steam na Windows, uruchamiane jako War of the Chosen, z oficjalnymi dodatkami i wyłącznie tym modem**. Nie wymaga Highlandera ani innych modów. Nie jest przeznaczony dla podstawowego XCOM 2 bez WOTC ani trybu wieloosobowego. [Szczegóły zgodności](docs/COMPATIBILITY.pl.md).

**Cel projektu:** jeden autoplay wszystkich misji taktycznych tego profilu,
obejmujący walkę, cele, interakcje, kolejne etapy i ewakuację, prowadzący do
legalnego zwycięstwa. Próby Gatecrashera i Legacy rozwijają wspólny mod.
Wyjątek dla scenariusza obiektywnie niemożliwego wymaga uzasadnienia stanem
misji; sama porażka aktualnego planera tego nie dowodzi. Postęp mierzymy
pełnymi misjami ukończonymi w grze. Od obecnej serii prób sukces wymaga
zwycięstwa i wyniku misji większego od zera; zero lub wynik ujemny nie zalicza
próby. Niepełna punktacja pozostawia ocenę niepotwierdzoną. Obecna alpha
nie realizuje jeszcze całości.

**Nowa wersja do prób Gatecrashera:** poprawiona ocena overwatch i przyczajenia,
Aid Protocol, ostrożniejsze flankowanie oraz rejestr decyzji i wyników misji.
[Jak zebrać raport po grze](docs/mission-recording.pl.md). Skrypt zbierający raport
jest instalowany z modem i działa po usunięciu pobranych źródeł. Zwycięstwo na
Commanderze lub Legendzie w Gatecrasherze nie jest jeszcze potwierdzone.

[Pierwszy raport z gry](docs/report-2026-11-02.pl.md) ujawnił utratę pamięci
kontaktu, zbyt wysoką ocenę ruchu na dach i brak propozycji granatów. Bieżący
`main` zawiera poprawki tych mechanizmów oraz dokładniejsze dane diagnostyczne;
wymaga nowej kompilacji i porównawczej próby w grze.

[Drugi raport](docs/report-2026-11-02-second.pl.md) potwierdził kolejną porażkę
i ujawnił koszt odwrotów ostatnim AP, pamiętanie potwierdzonych zabitych oraz
brak punktów celowania granatem przy krawędzi zasięgu. Poprawki weszły do
rewizji `mission-report-v3`.

[Trzeci raport](docs/report-2026-11-02-third.pl.md) ponownie zakończył się porażką.
Pokazał strzał z ukrycia przed przygotowaniem reszty oddziału oraz odrzucanie
sensownego granatu na pojedynczy cel. Bieżąca rewizja `mission-report-v4` dodaje
koordynację otwarcia zasadzki i ostrożny wyjątek dla takiego granatu.
[Analiza wykorzystania AI przeciwników i zakres nowego planera](docs/native-ai-and-ambush.pl.md).
Po zgłoszonym błędzie `Unparsed class ... DependsOn ... APX_Controller` usunięto
nową zależność kompilacji między kontrolerem a strukturą planera zasadzki.
Poprawione źródła wymagają ponownego zbudowania na Windows.

[Czwarty raport](docs/report-2026-11-02-fourth.pl.md) potwierdza działanie zasadzki,
trafiony overwatch i użycie granatu w `mission-report-v4`; misja nadal została
przegrana. Źródła `mission-report-v5` dopuszczają bezpieczne dogonienie
strzelca otwierającego przed ujawnieniem i zapisują podgląd konkretnych celów
wybranego granatu oraz geometrycznej osłony i LOS przy ruchu.

[Próba pierwszej misji Legacy Operations „Blast From the Past”](docs/report-2026-11-02-legacy.pl.md)
na `mission-report-v5` także zakończyła się porażką. Źródła
`mission-report-v6` ujednolicają ocenę zagrożeń za przeszkodami przy ruchu,
Aid Protocol, hunker i overwatch oraz zapisują wkład ryzyka każdego widocznego
przeciwnika. [Instrukcja kolejnej próby Legacy](docs/legacy-test.pl.md).
V6 zostało uruchomione w kolejnej próbie opisanej poniżej.

[Próba v6](docs/report-2026-11-02-legacy-v6.pl.md) potwierdziła działanie nowej
ochrony i diagnostyki, ale skończyła się porażką. `mission-report-v7`
stosuje ograniczenia wsparcia i trasy również do szarż wręcz oraz uwzględnia
utratę możliwości ataku po ruchu, np. strzału karabinem wymagającego dwóch AP.
[Próba v7](docs/report-2026-11-02-legacy-v7.pl.md) zakończyła się porażką
w turze 3, potwierdzając działanie kontroli szarży i kosztu AP.

Wersja **`mission-report-v8`** dodała wycenę znanych skutków zabicia źródła
kontroli umysłu lub psi zombie, alternatywne punkty granatu dla pary wrogów
oraz bardziej zachowawczą ocenę odwrotu w zasięgu wręcz.
[Opis zmian i ocena sugestii taktycznych](docs/tactics-v8.pl.md).
[Raport v8](docs/report-2026-11-03-legacy-v8-win.pl.md) potwierdza pierwsze
zwycięstwo: `ChallengeAbductionGasStation`, pierwsza misja „Blast From the Past”,
Dowódca, 14 tur i dwóch poległych. W logu widać załadowanie kolejnej misji
`ChallengeAbductionCemetery`; jej próba autoplaya pozostaje do wykonania.
Wersja **`mission-report-v9`** dodała podejście do wykrwawiającego się
żołnierza przed stabilizacją, legalne zbieranie łupu i rejestrację punktacji.
[Raport v9](docs/report-2026-11-03-legacy-v9.pl.md) potwierdza
podejście i stabilizację snajpera, ale ponowna próba GasStation skończyła się
porażką w turze 7, z wynikiem gry −10000. Ten sam raport zawiera też wygraną
v8 w `SabotageCC` na trudności 3.
[Zakres zmian, reguły punktacji i ograniczenia v9](docs/tactics-v9.pl.md).

Wersja **`mission-report-v14`** uzupełnia katalog o przekazane konfiguracje
gry, porównane z SDK: statystyki bazowe i warianty trudności, wyposażenie, parametry broni
oraz odwołania do AI. Zachowuje pochodzenie i jawne braki danych.
We wspólnej ocenie ryzyka uwzględnia też aktywne oznaczenie własnego żołnierza
przez kapitana. W dostarczonej konfiguracji Marked daje przeciwnikom +10 do
celności przeciw temu żołnierzowi; planer stosuje ograniczoną wagę ryzyka.
[Konfiguracje, ustalenia i scenariusze v14](docs/config-knowledge-v14.pl.md).
[Mechaniki broni, melee i zasadzki z v13](docs/enemy-knowledge-v13.pl.md)
pozostają w użyciu. Dane załadowane przez grę mają pierwszeństwo przed
statycznym katalogiem; katalog nie zastępuje natywnego podglądu ataku.

[Uzupełnienie katalogu o konfiguracje DLC](docs/dlc-config-knowledge.pl.md)
korzysta z pięciu nowych archiwów pochodzących wyłącznie z gry: `DLC_1`,
`DLC_2`, `DLC_3`, `TLE` i `XCom_DLC_Day0`. Nie wymaga folderu DLC w SDK.
Dodaje między innymi parametry władców obcych, SPARK-a i jednostek Legacy.
Tamta aktualizacja dotyczyła narzędzi analizy i katalogu; nie zmieniała kodu
działającego w grze ani rewizji `mission-report-v14`.

[Najnowszy raport v14](docs/report-2026-11-04-v14-poison.pl.md) zawiera trzy
próby zakończone porażką. Ostatnie GasStation kończy się w turze 9 z natywnym
odczytem −15100; stabilizacja jest potwierdzona. Raport wskazuje na potrzebę
rozróżnienia chmur trucizny od trwającego zatrucia i oceny ruchu przed słabym
strzałem przy zachowaniu AP.

Bieżące **`mission-report-v15`** dodaje jawną kontrolę chmur i bezpieczne
wyjście z nich oraz ograniczoną ocenę niebieskiego ruchu z zachowaniem
podstawowego strzału. Ocenia też wsparcie lub leczenie z zachowaniem
aktualnie legalnego ataku, respektując rzeczywiste typy i koszty AP.
Projekcja poprawy trafienia jest heurystyką; po ruchu
atak ponownie sprawdza gra. Analizator osobno ocenia zwycięstwo z dodatnim
wynikiem misji. [Zakres v15 i kolejna próba](docs/tactics-v15.pl.md).
Nowy kod wymaga kompilacji na Windows i sprawdzenia w grze.

Ocena porównawcza nadal używa profilu `wotc_legacy_observed_v2` od `~0/—`;
reguły punktacji nie zostały zmienione przez v15. Zmieniło się kryterium
zaliczenia próby, nie sposób naliczania punktów.
[Zasady licznika](docs/score-display-v10.pl.md).

**Stan: alpha; historyczne v8 wygrało pierwszą misję Legacy na Dowódcy.**
To oficjalne zwycięstwo nie potwierdza jeszcze nowego wymogu dodatniego wyniku.
Pełna drabinka Legacy, wygrana Gatecrashera i wszystkie pozostałe rodzaje misji
nadal wymagają osobnych prób. Każdy nowy raport otrzymuje porównawczą punktację
według wspólnego profilu reguł odczytanych z gry, także poza Legacy. Oficjalny
wynik Legacy pozostaje osobnym odczytem; niepełne dane dają częściową ocenę.
Pole `score` w rejestrze decyzji nadal jest oceną planera.
[Instrukcja następnej próby](docs/legacy-test.pl.md).

Dotychczasowy plik `.u` i konfigurację zweryfikowano; importy binarne prowadzą tylko do standardowych pakietów `Core`, `Engine`, `XComGame`. Repozytorium nie zawiera SDK ani plików gry. Szczegóły: [wyniki kontroli SDK i kompilacji](docs/SDK-AUDIT.pl.md).

## Instalacja gotowej paczki

Archiwum [AutoplayXCom2-WOTC-0.1.0-alpha.zip](release/AutoplayXCom2-WOTC-0.1.0-alpha.zip) zawiera skompilowaną wersję testową oraz `INSTALL.pl.md`, ale **nadal ma opisaną wyżej blokadę HUD-u i nie zawiera poprawki**. Do sprawdzenia poprawki użyj [instrukcji aktualizacji i budowania](docs/ui-blocking-fix.pl.md). GitHub „Download ZIP” pobiera całe repozytorium źródeł, a nie zaktualizowaną paczkę instalacyjną.

## Sterowanie

- W misji najedź na wąski znacznik przy prawej krawędzi, mniej więcej na środku ekranu. Pojawi się standardowy przycisk XCOM; po odejściu myszą zaniknie po dwóch sekundach.
- Zielony znacznik oznacza aktywny autoplay, jasnoniebieski — wyłączony. Przycisk pokazuje status i polecenie włączenia/zatrzymania.
- **F8** przełącza autoplay również wtedy, gdy taktyczny HUD jest ukryty. **Escape** zatrzymuje go i zachowuje zwykłe działanie pauzy gry. Klawisz można zmienić w konfiguracji.
- Wyłączenie blokuje następny rozkaz. Rozkazu już przyjętego przez silnik, np. strzału lub ruchu, nie cofa i nie przerywa w połowie.
- Po wczytaniu zapisu i po zmianie misji autoplay jest wyłączony. Menu oraz obce ekrany zatrzymują podejmowanie decyzji. Sekwencje przechwytujące wejście mogą opóźnić reakcję na skrót.

Przycisk używa oryginalnych elementów UI, bez zastępowania plików Flash. Położenie jest regulowane w `AutoplayXCom2/Config/XComAutoplayXCom2.ini`. Wybrano środek prawej krawędzi, z dala od dolnego paska akcji i górnego przycisku ewakuacji; wymaga to jeszcze sprawdzenia w różnych rozdzielczościach. Nie można zagwarantować braku kolizji z dowolnym innym modem HUD.

## Co jest zaimplementowane

| Obszar | Aktualna implementacja (wymaga testu w grze) |
| --- | --- |
| Sterowanie | Jedna decyzja naraz, tylko lokalna tura XCOM, sprawdzanie gotowości zasad i wizualizacji; zatrzymanie bez kolejkowania kolejnych rozkazów |
| Walka | Dozwolone przez grę strzały i wybrane umiejętności żołnierzy, SPARK-ów oraz frakcji WOTC; wycena szans trafienia, obrażeń i dobicia |
| Walka wręcz | Wybrane ataki Rangera, Templariusza i Renegata, z trasą wyznaczaną przez silnik |
| Niszczenie celów | Zwykłe strzały do widocznych obiektów oznaczonych przez grę jako wrogie cele misji, np. przekaźniki; bez atakowania neutralnej scenerii |
| Granaty | Frag/Alien rzucane i wystrzeliwane, natywna trajektoria i promień wybuchu, ocena grup widocznych wrogów; kontrola sojuszników, cywilów, celów misji i niebezpiecznych obiektów na trasie i w wybuchu |
| Wsparcie | Leczenie i stabilizacja; podejście ratownika do wykrwawiającego się sojusznika z zachowaniem AP na stabilizację; przeładowanie, overwatch, hunker down |
| Łup | Natywne darmowe `Loot`; krótkie bezpieczne podejście do widocznego łupu po walce, gdy nie koliduje z ratunkiem, ewakuacją, celem ani aktywnym terminem |
| Zasadzka | Przed atakiem z ukrycia: zachowanie strzelca otwierającego, krótkie ruchy pozostałych do linii ostrzału i legalny overwatch; ograniczony budżet przygotowań |
| Ruch | Legalne niebieskie ruchy, trasowanie A*, kierunkowe osłony i wsparcie; ograniczony wariant ruchu przed podstawowym strzałem; kontrola zagrożeń i wyjście z jawnej chmury trucizny |
| Eksploracja | Gdy brak znanych celów i przydatnych akcji: ograniczone obliczeniowo próbkowanie niezbadanych pól mapy i podział celów między żołnierzy; bez odczytu pozycji ukrytych wrogów |
| Cele | Rozpoznawane interakcje: ładunki, skrzynie, dowody, obiekty misji, oznaczanie zasobów, wybrane obiekty fabularne, przenoszenie VIP-a i podejście do cywilów |
| Hakowanie | Wyłącznie ekran wywołany własnym rozkazem; wybór dostępnej nagrody z najwyższą pokazywaną szansą, zwykły rzut gry, zamknięcie po zakończeniu animacji |
| Ewakuacja | Istniejąca strefa, kontrolowani cywile / niesiony VIP albo ukończony jawnie oznaczony cel strategiczny; wyznaczenie nowej strefy zwykłą zdolnością `PlaceEvacZone` po ukończeniu celu, z natywną kontrolą miejsca i widoczności |

Nowe oceny uwzględniają najsłabiej osłonięty kierunek, rannych żołnierzy, pancerz
i szansę dobicia, potencjalną flankę oraz wsparcie i odstępy oddziału. Ruch
ofensywny i eksploracja zachowują AP; ostatni AP w walce może posłużyć do
wyraźnie bezpieczniejszego odwrotu. Geometryczna ocena flanki nie przewiduje
pewnie widoczności po ruchu. [Szczegóły i ograniczenia](docs/tactics-update.pl.md).

Mod nie dodaje punktów akcji, nie zmienia trafień, nie zabija wrogów komendą i nie wywołuje sztucznego zwycięstwa. Wybór przeciwników korzysta z widoczności gracza, w tym legalnego squadsight. Znane pozycje oznaczonych celów misji służą do nawigacji.

## Granice tej wersji

To **nie jest jeszcze pełny autopilot wszystkich misji**. Do ukończenia wymagania potrzebne są kompilacja, testy i dopracowanie zachowania na konkretnych mapach:

- Planer obszarowy obsługuje wyłącznie zwykłe granaty Frag/Alien. Domyślnie wymaga dwóch widocznych przeciwników. Pojedynczy cel dopuszcza przy gwarantowanym dobiciu albo wyraźnej przewadze nad zwykłym strzałem: duże pewne obrażenia z szansą zabicia lub dostępne, sprawdzone dobicie przez sojusznika. Broń ciężka, stożki, ogień, kwas, EMP, dym i pozostałe efekty trwałe wymagają osobnych reguł. Pełne skutki zawalania konstrukcji wymagają testów w grze.
- Planer zasadzki przygotowuje otwarcie w bieżącej turze, gdy cały zdolny do walki oddział zachowuje ukrycie drużynowe. Dopuszcza też bezpieczne dogonienie strzelca przez tył oddziału, gdy jeden ruch nie wystarcza do uzyskania linii ostrzału. Nie planuje wielu tur, tras patroli ani oszczędzania zasobów na kolejne etapy. Nie przewiduje ukrytych wrogów i nie gwarantuje odpalenia każdej reakcji. [Dokładny zakres i ustawienia](docs/native-ai-and-ambush.pl.md).
- Pełne wykorzystanie każdej umiejętności DLC wymaga osobnych planerów i testów. Listy obsługiwanych umiejętności są jawne w `Config/XComAutoplayXCom2.ini`.
- Eksploracja używa próbkowania siatki mapy. Nie gwarantuje odwiedzenia każdego małego pomieszczenia ani znalezienia wroga, który przemieścił się na wcześniej odwiedzony teren. Gdy nie znajduje osiągalnego celu, automat oddaje sterowanie.
- Nietypowe cele Kismet, wieloetapowe Lost Towers / Alien Nest, twierdze Wybranych, obrona Avengera, finał i wyzwania Legacy **nie mają potwierdzonej obsługi końca do końca**. Może być potrzebne ręczne przejście etapu lub ewakuacja.
- Wyznaczanie ewakuacji wymaga istniejącego, ukończonego celu strategicznego i dostępnej zwykłej zdolności gry. Mod nie wybiera ścieżek dialogowych i nie zamyka ogólnych komunikatów. Nie uznaje pustej listy celów za powód do opuszczenia misji.
- Samouczek, replay i multiplayer są wyłączone. Nie deklarujemy zgodności z Long War of the Chosen ani innymi zmianami zasad.

Brak sensownego planu, odrzucony rozkaz lub limit działań zatrzymuje automat. Gracz może przejąć kontrolę, wykonać brakującą czynność i ponownie go włączyć.

## Budowanie na Windows

1. W Steam zainstaluj **XCOM 2 War of the Chosen Development Tools** (SDK WOTC, nie SDK podstawowej gry). W razie brakujących źródeł zweryfikuj instalację SDK. Źródła SDK zwykle znajdują się w `Development\SrcOrig`.
2. Pobierz to repozytorium. Uruchom PowerShell w jego głównym katalogu:

```powershell
.\tools\build.ps1 -SdkPath 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK' -BuildBase
```

`-BuildBase` jawnie uruchamia kompilację bazowych skryptów SDK. Po przygotowaniu tych pakietów pomiń tę opcję przy kolejnych kompilacjach. Nie uruchamiaj równolegle innych kompilacji na tym samym SDK. Skrypt uzupełnia tylko brakujące pliki `.uc`/`.uci` z `SrcOrig`, zachowuje istniejące poprawki SDK i zastępuje wyłącznie oznaczone, własne katalogi moda. Zastany katalog moda bez znacznika powoduje przerwanie — najpierw zachowaj jego zawartość.

```powershell
# Opcjonalna instalacja zbudowanego moda do gry:
.\tools\build.ps1 -SdkPath 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK' `
  -GamePath 'D:\SteamLibrary\steamapps\common\XCOM 2\XCom2-WarOfTheChosen'
```

Wynik: `dist\AutoplayXCom2.zip`, pakiet `Script\AutoplayXCom2.u` i lokalizacje PL/EN w UTF-16LE. Logi: `.build\base-make.log` oraz `.build\mod-make.log`. Sukces budowania wymaga nowego, niepustego `.u`; stary pakiet nie może udawać poprawnej kompilacji.

Alternatywnie otwórz `AutoplayXCom2.XCOM_sln` w ModBuddy WOTC jako projekt edytora. Źródła lokalizacji w Git są UTF-8; zalecaną ścieżką pakowania jest skrypt, który konwertuje je na format gry.

Po skompilowaniu użyj [instrukcji instalacji](AutoplayXCom2/INSTALL.pl.md), dołączanej również do wynikowego ZIP-a. Włącz mod w launcherze WOTC (np. Alternative Mod Launcher). Dla instalacji ręcznej wypakuj katalog `AutoplayXCom2` do `XCOM 2\XCom2-WarOfTheChosen\XComGame\Mods`. Nie kopiuj samych plików `.uc` do instalacji gry.

Możesz usunąć pobrany katalog źródeł po zainstalowaniu wyniku lub zachowaniu
ZIP-a poza nim. SDK i jego pakiety bazowe zachowaj do kolejnych kompilacji;
nie wymagają ponownego budowania z `-BuildBase` przy każdej aktualizacji.

## Weryfikacja

Archiwalna kontrola źródeł SDK i logów Windows po przeniesieniu ustawień do INI
potwierdziła **0 błędów i 8 ostrzeżeń SDK**, zarówno dla bazy, jak i moda.
Dotyczy to wcześniejszej kompilacji. Przechowywany ZIP ma kompletną konfigurację,
27 nazw zdolności, obie lokalizacje i prawidłowy `.u`; jego 464 importy prowadzą
tylko do `Core`, `Engine` i `XComGame`, a dziewięć klas moda jest obecnych.
Najnowszy raport potwierdza uruchomienie v14 oraz trzy porażki, w tym
GasStation w turze 9 z natywnym odczytem −15100. Zmiany taktyczne v15
wymagają nowej kompilacji i sprawdzenia w grze. Obecne
środowisko Linux pozwala uruchamiać testy Python i PowerShell, ale nie zawiera
SDK Windows ani działającej gry.

```powershell
# Przenośne testy ochrony istniejących plików SDK (bez kompilatora):
pwsh -NoProfile -File .\tests\Test-BuildHelpers.ps1
pwsh -NoProfile -File .\tests\Test-CollectSdkSources.ps1
pwsh -NoProfile -File .\tests\Test-CollectMissionRecording.ps1

# Opcjonalna kontrola nazw klas i zdolności w lokalnym SDK (nie kompilacja):
python .\tools\check-sdk-references.py --sdk 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK'
python .\tools\check-compiled-package.py .\release\AutoplayXCom2-WOTC-0.1.0-alpha.zip
python -m unittest discover -s tests -p 'test_*.py' -v
```

Lista wymaganych prób w grze: [docs/TESTING.pl.md](docs/TESTING.pl.md). Pliki potrzebne do dalszej weryfikacji i sposób ich przekazania: [docs/SDK-FILES.pl.md](docs/SDK-FILES.pl.md).

Aktualne zmiany taktyki mają testy scenariuszy numerycznych wykonywane na funkcjach
odczytanych z UnrealScript; nie zastępują one kompilacji ani gry.

## Źródła techniczne

Implementacja jest własna; repozytorium nie rozprowadza SDK. Sygnatury sprawdzano w publicznym [X2WOTCCommunityHighlander](https://github.com/X2CommunityCore/X2WOTCCommunityHighlander/tree/384e5d261d6437d7ed9c19491e4d16d6689f10a3), szczególnie `XComGameStateContext_Ability`, `XComTacticalController`, `XGAIBehavior`, `UIHackingScreen`, `UIPanel` i `UIButton`. Wywołania kompilatora oparto na [X2ModBuildCommon](https://github.com/X2CommunityCore/X2ModBuildCommon). Mod nie wymaga klas Highlandera; zgodność z czystym SDK WOTC musi potwierdzić kompilacja.
