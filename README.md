# Autoplay XCOM 2 — War of the Chosen

Mod w UnrealScript automatyzujący działania oddziału w misji. Docelowa platforma: **Windows, XCOM 2: War of the Chosen z oficjalnymi dodatkami** (także Alien Hunters, Shen’s Last Gift i Tactical Legacy Pack). Nie jest przeznaczony dla podstawowego XCOM 2 bez WOTC ani trybu wieloosobowego.

**Stan: niekompilowana wersja rozwojowa, nie gotowe wydanie do grania.** Repozytorium zawiera własne źródła moda i narzędzia budowania. Nie zawiera plików gry, SDK ani gotowego `.u`. Nie potwierdzono działania w grze ani pełnego ukończenia wszystkich typów misji. Sama obecność dodatków nie oznacza obsługi wszystkich ich skryptowanych etapów.

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
| Wsparcie | Leczenie i stabilizacja, przeładowanie, overwatch, hunker down |
| Ruch | Legalne niebieskie ruchy, trasowanie A*, ocena osłon względem widocznych wrogów, kontrola ognia/kwasu i innych zagrożeń na trasie |
| Cele | Rozpoznawane interakcje: ładunki, skrzynie, dowody, obiekty misji, oznaczanie zasobów, wybrane obiekty fabularne, przenoszenie VIP-a i podejście do cywilów |
| Hakowanie | Wyłącznie ekran wywołany własnym rozkazem; wybór dostępnej nagrody z najwyższą pokazywaną szansą, zwykły rzut gry, zamknięcie po zakończeniu animacji |
| Ewakuacja | Istniejąca strefa, kontrolowani cywile / niesiony VIP albo ukończony jawnie oznaczony cel strategiczny; brak wymuszania zwycięstwa |

Mod nie dodaje punktów akcji, nie zmienia trafień, nie zabija wrogów komendą i nie wywołuje sztucznego zwycięstwa. Wybór przeciwników korzysta z widoczności gracza, w tym legalnego squadsight. Znane pozycje oznaczonych celów misji służą do nawigacji.

## Granice tej wersji

To **nie jest jeszcze pełny autopilot wszystkich misji**. Do ukończenia wymagania potrzebne są kompilacja, testy i dopracowanie zachowania na konkretnych mapach:

- Brak taktycznego planera granatów, broni ciężkiej i dowolnych ataków obszarowych wymagających celowania w teren. Nie są automatycznie używane, aby nie wykonywać ich bez sprawdzenia trafianych sojuszników i obiektów.
- Brak planowania zasadzki całego oddziału, oszczędzania zasobów na kolejne etapy i pełnego wykorzystania każdej umiejętności DLC. Listy obsługiwanych umiejętności są jawne w `APX_CombatPlanner.uc`.
- Brak eksploracji całej mapy w poszukiwaniu ostatniego nieodkrytego wroga. Gdy kończą się widoczne cele i znane punkty misji, mod oddaje sterowanie.
- Nietypowe cele Kismet, wieloetapowe Lost Towers / Alien Nest, twierdze Wybranych, obrona Avengera, finał i wyzwania Legacy **nie mają potwierdzonej obsługi końca do końca**. Może być potrzebne ręczne przejście etapu lub ewakuacja.
- Mod nie wyznacza samodzielnie nowej strefy ewakuacji, nie wybiera ścieżek dialogowych i nie zamyka ogólnych komunikatów. Nie uznaje pustej listy celów za powód do opuszczenia misji.
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

Alternatywnie otwórz `AutoplayXCom2.XCOM_sln` w ModBuddy WOTC. Źródła lokalizacji w Git są UTF-8; zalecaną ścieżką pakowania jest skrypt, który konwertuje je na format gry.

Po skompilowaniu włącz mod w launcherze WOTC (np. Alternative Mod Launcher). Dla instalacji ręcznej wypakuj katalog `AutoplayXCom2` do `XCOM 2\XCom2-WarOfTheChosen\XComGame\Mods`. Nie kopiuj samych plików `.uc` do instalacji gry.

## Weryfikacja

Wykonano kontrolę dostępnych publicznych deklaracji API oraz składni PowerShell i testy zabezpieczeń operacji plikowych narzędzia budowania. **Nie wykonano kompilacji UnrealScript ani testów w grze**: środowisko robocze jest linuksowe, bez SDK i gry.

```powershell
# Przenośne testy ochrony istniejących plików SDK (bez kompilatora):
pwsh -NoProfile -File .\tests\Test-BuildHelpers.ps1
pwsh -NoProfile -File .\tests\Test-CollectSdkSources.ps1
```

Lista wymaganych prób w grze: [docs/TESTING.pl.md](docs/TESTING.pl.md). Pliki potrzebne do dalszej weryfikacji i sposób ich przekazania: [docs/SDK-FILES.pl.md](docs/SDK-FILES.pl.md).

## Źródła techniczne

Implementacja jest własna; repozytorium nie rozprowadza SDK. Sygnatury sprawdzano w publicznym [X2WOTCCommunityHighlander](https://github.com/X2CommunityCore/X2WOTCCommunityHighlander/tree/384e5d261d6437d7ed9c19491e4d16d6689f10a3), szczególnie `XComGameStateContext_Ability`, `XComTacticalController`, `XGAIBehavior`, `UIHackingScreen`, `UIPanel` i `UIButton`. Wywołania kompilatora oparto na [X2ModBuildCommon](https://github.com/X2CommunityCore/X2ModBuildCommon). Mod nie wymaga klas Highlandera; zgodność z czystym SDK WOTC musi potwierdzić kompilacja.
