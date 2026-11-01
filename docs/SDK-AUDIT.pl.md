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
