# Autoplay XCOM 2 — War of the Chosen

Mod w UnrealScript automatyzujący działania oddziału w misji. Docelowy profil użytkownika: **aktualne XCOM 2 Collection ze Steam na Windows, uruchamiane jako War of the Chosen, z oficjalnymi dodatkami i wyłącznie tym modem**. Nie wymaga Highlandera ani innych modów. Nie jest przeznaczony dla podstawowego XCOM 2 bez WOTC ani trybu wieloosobowego. [Szczegóły zgodności](docs/COMPATIBILITY.pl.md).

**Stan: wersja testowa alpha z potwierdzoną kompilacją i sprawdzoną paczką instalacyjną.** Przesłany plik `.u` i konfigurację zweryfikowano; importy binarne prowadzą tylko do standardowych pakietów `Core`, `Engine`, `XComGame`. Paczka do instalacji jest w katalogu [release](release/README.pl.md). Repozytorium nie zawiera SDK ani plików gry. **Nie uruchomiono jeszcze testów w grze i nie potwierdzono pełnego ukończenia wszystkich misji DLC.** Szczegóły: [wyniki kontroli SDK i kompilacji](docs/SDK-AUDIT.pl.md).

## Instalacja gotowej paczki

Pobierz [AutoplayXCom2-WOTC-0.1.0-alpha.zip](release/AutoplayXCom2-WOTC-0.1.0-alpha.zip) i użyj dołączonego `INSTALL.pl.md`. To skompilowana wersja testowa; nie wymaga SDK ani ponownego budowania. GitHub „Download ZIP” nadal pobiera całe repozytorium źródeł, a nie samą paczkę instalacyjną.

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
| Wsparcie | Leczenie i stabilizacja, przeładowanie, overwatch, hunker down |
| Ruch | Legalne niebieskie ruchy, trasowanie A*, ocena osłon względem widocznych wrogów, kontrola ognia/kwasu i innych zagrożeń na trasie |
| Eksploracja | Gdy brak znanych celów i przydatnych akcji: ograniczone obliczeniowo próbkowanie niezbadanych pól mapy i podział celów między żołnierzy; bez odczytu pozycji ukrytych wrogów |
| Cele | Rozpoznawane interakcje: ładunki, skrzynie, dowody, obiekty misji, oznaczanie zasobów, wybrane obiekty fabularne, przenoszenie VIP-a i podejście do cywilów |
| Hakowanie | Wyłącznie ekran wywołany własnym rozkazem; wybór dostępnej nagrody z najwyższą pokazywaną szansą, zwykły rzut gry, zamknięcie po zakończeniu animacji |
| Ewakuacja | Istniejąca strefa, kontrolowani cywile / niesiony VIP albo ukończony jawnie oznaczony cel strategiczny; wyznaczenie nowej strefy zwykłą zdolnością `PlaceEvacZone` po ukończeniu celu, z natywną kontrolą miejsca i widoczności |

Mod nie dodaje punktów akcji, nie zmienia trafień, nie zabija wrogów komendą i nie wywołuje sztucznego zwycięstwa. Wybór przeciwników korzysta z widoczności gracza, w tym legalnego squadsight. Znane pozycje oznaczonych celów misji służą do nawigacji.

## Granice tej wersji

To **nie jest jeszcze pełny autopilot wszystkich misji**. Do ukończenia wymagania potrzebne są kompilacja, testy i dopracowanie zachowania na konkretnych mapach:

- Planer obszarowy obsługuje wyłącznie zwykłe granaty Frag/Alien i domyślnie wymaga dwóch widocznych przeciwników. Broń ciężka, stożki, ogień, kwas, EMP, dym i pozostałe efekty trwałe wymagają osobnych reguł. Pełne skutki zawalania konstrukcji wymagają testów w grze.
- Brak planowania zasadzki całego oddziału, oszczędzania zasobów na kolejne etapy i pełnego wykorzystania każdej umiejętności DLC. Listy obsługiwanych umiejętności są jawne w `Config/XComAutoplayXCom2.ini`.
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

## Weryfikacja

Wykonano kontrolę oryginalnych źródeł SDK przesłanych przez użytkownika, składni PowerShell oraz testy zabezpieczeń plikowych, zawartości paczki i konwersji polskiej lokalizacji. Po przeniesieniu ustawień do INI logi Windows potwierdzają **0 błędów i 8 ostrzeżeń SDK**, zarówno dla bazy, jak i moda. Przesłany ZIP ma kompletną konfigurację, 27 nazw zdolności, obie lokalizacje i prawidłowy `.u`. Jego 464 importy prowadzą tylko do trzech standardowych pakietów; dziewięć klas moda jest obecnych. **Testy w grze pozostają wymagane.** Lokalne środowisko ma źródła SDK, logi i skompilowaną paczkę, ale nie uruchomioną grę.

```powershell
# Przenośne testy ochrony istniejących plików SDK (bez kompilatora):
pwsh -NoProfile -File .\tests\Test-BuildHelpers.ps1
pwsh -NoProfile -File .\tests\Test-CollectSdkSources.ps1

# Opcjonalna kontrola nazw klas i zdolności w lokalnym SDK (nie kompilacja):
python .\tools\check-sdk-references.py --sdk 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK'
python .\tools\check-compiled-package.py .\release\AutoplayXCom2-WOTC-0.1.0-alpha.zip
python -m unittest discover -s tests -p 'test_*.py' -v
```

Lista wymaganych prób w grze: [docs/TESTING.pl.md](docs/TESTING.pl.md). Pliki potrzebne do dalszej weryfikacji i sposób ich przekazania: [docs/SDK-FILES.pl.md](docs/SDK-FILES.pl.md).

## Źródła techniczne

Implementacja jest własna; repozytorium nie rozprowadza SDK. Sygnatury sprawdzano w publicznym [X2WOTCCommunityHighlander](https://github.com/X2CommunityCore/X2WOTCCommunityHighlander/tree/384e5d261d6437d7ed9c19491e4d16d6689f10a3), szczególnie `XComGameStateContext_Ability`, `XComTacticalController`, `XGAIBehavior`, `UIHackingScreen`, `UIPanel` i `UIButton`. Wywołania kompilatora oparto na [X2ModBuildCommon](https://github.com/X2CommunityCore/X2ModBuildCommon). Mod nie wymaga klas Highlandera; zgodność z czystym SDK WOTC musi potwierdzić kompilacja.
