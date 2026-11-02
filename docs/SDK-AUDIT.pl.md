# Sprawdzenie źródeł SDK — 31.10.2026

Przeanalizowano przesłane przez użytkownika archiwum `SrcOrig.rar` (7 661 577 bajtów):

```text
SHA-256: 8c298bd0dab3382c931f7cfb2500175da3d586d4b81d3e18f0548b4b3bcbb83e
```

Archiwum zawiera 4137 plików `.uc` i 7 plików `.uci`, w tym pakiety `XComGame`, `DLC_1`, `DLC_2`, `DLC_3` i `TLE`. Obecność klas Reapera, Templariusza, Skirmishera i Wybranych potwierdza źródła WOTC. Na podstawie samego archiwum nie przypisujemy konkretnego numeru wersji binarnej gry.

Źródła rozpakowano poza repozytorium. Nie są publikowane na GitHub i nie wchodzą do paczki moda.

## Wynik ręcznej kontroli

Sprawdzono deklaracje używanych funkcji i pól w rzeczywistym SDK: pamięć dostępnych akcji, aktywacja zdolności, własność jednostek, gotowość zasad i wizualizacji, ścieżki i osiągalne pola, widoczność, obrażenia, cele interaktywne, strefa ewakuacji, ekran hakowania, przyciski i zdarzenia UI.

Poprawki wynikające z kontroli:

- Usunięto cztery nieistniejące aliasy umiejętności: `PistolStandardShot_Secondary`, `SparkStandardShot`, `SparkReload`, `SparkOverwatch`. SPARK korzysta z `StandardShot`, `Reload`, `Overwatch`, co potwierdzają źródła broni DLC_3.
- Nokaut ograniczono do jednostki `HostileVIPCivilian`, aby nie próbować obezwładniać dowolnego cywila oznaczonego jako cel.
- Wrogi cel bojowy nie jest traktowany jak VIP wymagający podejścia z bliska.
- Kontroler respektuje `XComTacticalController.IsBusy()`, również dla modalnych komunikatów prezentacji niebędących osobnym ekranem na stosie.
- Wyłączenie i ponowne włączenie w trakcie własnego hakowania zachowuje dokładny kontekst rozpoczętej akcji. Tożsamość kontekstu chroni przed przejęciem późniejszego ręcznego hacka tą samą zdolnością.

Nowe planery eksploracji, zwykłych granatów wybuchowych i wyznaczania ewakuacji korzystają z interfejsów sprawdzonych w tym SDK. Każdy nadal wymaga prób w działającej grze.

## Powtarzalna kontrola odwołań

Opcjonalnie, z Pythonem 3:

```powershell
python .\tools\check-sdk-references.py --sdk 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK'
```

Narzędzie sprawdza obecność dosłownych odwołań do klas, skonfigurowanych nazw umiejętności oraz znaczników WOTC. Nie sprawdza sygnatur metod ani zasad natywnych i nie zastępuje kompilatora.

## Co pozostaje wymagane

Archiwum zawiera źródła, bez kompilatora i silnika. W lokalnym środowisku nie uruchomiono kompilatora ani gry. Testy PowerShell dotyczą rzeczywistych operacji plikowych narzędzi, a nie zachowania gry.

Następny krok na Windows: pobrać aktualne repozytorium i wykonać `tools\build.ps1` z poprawną ścieżką SDK. Log `.build\mod-make.log` pozwoli naprawić błędy, których ręczne sprawdzenie źródeł nie wykrywa. Następnie konieczna jest lista prób z `TESTING.pl.md`.

## Otrzymane logi pierwszej próby budowania

`base-make.log` zakończył się `Success - 0 error(s), 1739 warning(s)`: przygotowanie bazowych pakietów SDK powiodło się. Ostrzeżenia dotyczą między innymi zasobów edytora i DLC; nie zatrzymały tej kompilacji.

`mod-make.log` zakończył się `Failure - 1 error(s), 8 warning(s)`. Pierwszy błąd w `APX_MissionPlanner.uc` brzmiał `Booleans may not be out parameters`. Wszystkie trzy bezpośrednie parametry wyjściowe typu `bool` w dwóch funkcjach zastąpiono jedną strukturą `MissionGoal`; jej pola logiczne zachowują dotychczasowy wybór celu. To ograniczenie języka dodano również do narzędzia kontroli oraz czterech testów regresji.

Po tej poprawce zalecono ponowienie kompilacji moda **bez `-BuildBase`**, wykorzystując już zbudowane pakiety bazowe. Na tym etapie sukces nie był jeszcze potwierdzony.

## Druga próba — 01.11.2026

Kolejny przesłany `mod-make.log` nie zgłasza poprzedniego problemu parametrów. Kompilacja zatrzymała się na trzech niekwalifikowanych wywołaniach `Stop(...)` w `APX_Controller.uc`, z komunikatem `'Stop' is not allowed here`.

UnrealScript interpretuje taki zapis w treści funkcji jako specjalne polecenie `Stop` używane w stanach. Nie oznacza to zakazu natywnych metod `Stop` w SDK: kwalifikowane wywołania, takie jak `Audio.Stop()`, są prawidłowe. Nazwę własnej metody zmieniono na `StopAutoplay`, zarówno w kontrolerze, jak i panelu UI, i dodano cztery testy dla tego przypadku. Łącznie osiem testów preflight przechodzi; nie zastępują kompilatora ani testów w grze.

Do kolejnej próby trzeba zaktualizować oba pliki: `APX_Controller.uc` oraz `APX_UITacticalControl.uc`. Poprawiony wcześniej `APX_MissionPlanner.uc` również musi pozostać aktualny. Bazowych pakietów SDK nie trzeba przebudowywać.

## Trzecia próba — kompilacja zakończona, konfiguracja do poprawy

Następny `mod-make.log` potwierdza zapis `AutoplayXCom2.u` i wynik `Success - 0 error(s), 67 warning(s)`. Najnowszy log bazy ma `Success - 0 error(s), 8 warning(s)`.

67 unikalnych ostrzeżeń moda składa się z:

- 8 ostrzeżeń dotyczących zasobów narracji, materiałów i modeli SDK/DLC oraz starego katalogu `XCom_DLC_Day0`. Pakowanie rozprowadza tylko własny `.u`, nie przebudowane biblioteki SDK.
- 59 ostrzeżeń `Import failed ... property is config` w naszych klasach: Combat 29, Controller 9, Exploration 8, UI 6, Area 3, Mission 2, Evac 1, DLCInfo 1.

Druga grupa ma znaczenie funkcjonalne. Kompilator pomija przypisania pól `config` w `defaultproperties`. Dotychczas listy umiejętności istniały tylko w odrzucanych przypisaniach, więc planer mógł mieć puste listy ataków, leczenia, przeładowania i overwatch.

Poprawka usuwa wszystkie takie przypisania z kodu. Wartości liczbowe i wszystkie 27 nazw umiejętności znajdują się w `XComAutoplayXCom2.ini`; dziedziczony `DLCIdentifier` jest w `XComGame.ini`, zgodnie z bazową klasą `config(Game)`. Pozostałe właściwości aktorów i UI zostają w `defaultproperties`, ponieważ nie są polami konfiguracji.

Kontrola sprawdza obecność wartości dla każdego zadeklarowanego pola `config`, zachowanie list oraz odrzucane przypisania, również dziedziczone z SDK. Poprawka wymaga ponownej kompilacji. Nie potwierdzono jeszcze odczytu konfiguracji ani działania autoplaya w grze.

## Czwarta próba — kompilacja po migracji konfiguracji potwierdzona

Kolejne logi otrzymane 01.11.2026 potwierdzają wynik `Success - 0 error(s), 8 warning(s)` zarówno dla bazowych bibliotek, jak i kompilacji moda. `mod-make.log` zawiera jawny zapis pakietu `AutoplayXCom2.u`.

Wszystkie pozostałe ostrzeżenia dotyczą bibliotek SDK/DLC: jednego starego katalogu źródeł i siedmiu odwołań do zasobów narracji/modeli. Nie ma ostrzeżeń dla klas `AutoplayXCom2` ani `property is config`. Poprzednie 59 odrzuconych ustawień zniknęło.

To potwierdzenie kompilacji kodu, nie wykonania dalszych kroków skryptu pakującego. Do sprawdzenia pozostają zawartość `dist/AutoplayXCom2.zip`, odczyt konfiguracji przez uruchomioną grę oraz próby misji z `TESTING.pl.md`. Nie ma potrzeby ponownego budowania tylko z powodu tych ośmiu znanych ostrzeżeń bibliotek SDK.

## Otrzymana i sprawdzona paczka instalacyjna

Następnie otrzymano `AutoplayXCom2.zip` o rozmiarze 66 360 bajtów. CRC archiwum jest poprawne. Jest jeden katalog `AutoplayXCom2`, własny `.u`, trzy pliki konfiguracji, manifest `RequiresXPACK=true`, obie lokalizacje w UTF-16LE z BOM, instrukcja oraz znacznik narzędzia budowania. Konfiguracja, manifest i teksty odpowiadają źródłom repozytorium; listy zawierają wszystkie 27 zdolności.

Statyczna kontrola `.u` potwierdziła 786 nazw, 464 importy i 773 eksporty, spójne zakresy tabel oraz dziewięć klas moda z oryginalnymi klasami bazowymi. Importy prowadzą wyłącznie do `Core`, `Engine`, `XComGame`; nie stwierdzono zależności od innych modów. Wszystkie importowane klasy są w przesłanym oryginalnym SDK lub należą do standardowych typów Core.

Na tej podstawie przygotowano paczkę `release/AutoplayXCom2-WOTC-0.1.0-alpha.zip`. Zachowuje ona identyczny `.u`, konfigurację i napisy; zawiera uaktualnioną instrukcję oraz `BUILD-INFO.json`. [Profil zgodności i granice tego potwierdzenia](COMPATIBILITY.pl.md).

Można powtórzyć kontrolę bez uruchamiania gry:

```powershell
python .\tools\check-compiled-package.py .\release\AutoplayXCom2-WOTC-0.1.0-alpha.zip
```

Ta kontrola oraz 14 testów parsera dotyczą struktury pliku, ścieżek ZIP, zależności i spójności hashy, nie wykonywania bytecode. Sprawdzenie paczki **nie potwierdza konkretnego numeru builda Steam, uruchomienia moda ani wykonania misji**. Następny etap to próba na docelowym czystym WOTC użytkownika.

## Uzupełnienie SDK w nowym środowisku — 02.11.2026

Po odtworzeniu commitu `ed74176` i przygotowaniu `mission-report-v6` otrzymano
`Development.rar` (15 468 196 bajtów), SHA-256:

```text
04ad9ed9c7296dd04f390c67e5dec5dfa89337800af1d3cc1915d9890ad6fb43
```

Archiwum rozpakowano poza repozytorium, po sprawdzeniu ścieżek i typów wpisów.
`SrcOrig` zawiera 4144 pliki źródłowe SDK. Wszystkie odpowiadające im pliki
w `Src` są bajtowo identyczne. Dodatkowe pliki w `Src` to znacznik narzędzia
budowania i 11 klas AutoplayXCom2; wszystkie te klasy odpowiadają commitowi
`ed74176`, a rejestrator deklaruje `mission-report-v5`. Potwierdza to wersję
źródeł pozostawionych w SDK przy poprzednim budowaniu.

Kontrola bieżących źródeł v6 z `APX_SDK_SOURCE_ROOT` wskazującym przesłany
`Development/SrcOrig` zakończyła się wynikiem **176 testów Python zaliczonych,
0 pominiętych**. Wcześniejsze 7 pominięć z braku SDK zostało usunięte.
`check-sdk-references.py` potwierdził 11 klas moda, obecność odwołań do klas
SDK, 29 skonfigurowanych nazw zdolności i znaczniki WOTC, bez zgłoszonych
niezgodności. Wszystkie trzy zestawy PowerShell przeszły wcześniej dla v6.

Ręcznie sprawdzono sygnatury `GetCoverTypeForTarget`, `CanSeeTileToTile`
i deklarację `GameRulesCache_VisibilityInfo` używane przez wspólną funkcję
ryzyka v6. Argumenty i istniejące zależności klas są zgodne. Źródła potwierdzają
także klasyfikację Faceless jako jednostki walczącej wyłącznie wręcz;
nie ma podstaw do dodawania wyjątku zastępującego tę klasyfikację.

Do tej weryfikacji nie brakuje kolejnych źródeł SDK. Pliki SDK pozostają
poza repozytorium i paczką moda. Kompilacja Windows i próba v6 w grze nadal
wymagają uruchomienia na komputerze z SDK WOTC i grą.
