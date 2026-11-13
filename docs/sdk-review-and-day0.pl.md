# Aktualna migawka SDK i ostatnie ostrzeżenie Day0

## Co potwierdziły nowe logi

Po uporządkowaniu duplikatów TLE baza i mod skompilowały się z wynikiem
PASS, każdy z 0 błędów i 1 ostrzeżeniem. Pozostało wyszukiwanie UC pustego
XCom_DLC_Day0, wymienionego na liście kompilacji SDK. Gra v32 pozostaje
NOT RUN; pojedyncze ostrzeżenie nie zatrzymuje kompilacji.

## Opcjonalne pominięcie pustego pakietu

Najpierw sprawdzić, czy Development/Src/XCom_DLC_Day0 oraz
Development/SrcOrig/XCom_DLC_Day0 nie zawierają żadnych plików .uc,
także w podkatalogach. Jeśli istnieją, należy ustalić błędną ścieżkę;
poniższy wariant dotyczy wyłącznie pustego lub nieistniejącego źródła.
Wcześniej dostarczone źródła SDK nie zawierały Day0.

Zachować kopie obu poniższych plików SDK. W ich sekcji
[UnrealEd.EditorEngine] skomentować tylko następujące wpisy:

| Plik w katalogu SDK | Wpis po zmianie |
| --- | --- |
| XComGame/Config/DefaultEngine.ini | ;+EditPackages=XCom_DLC_Day0 |
| XComGame/Config/XComEngine.ini | ;EditPackages=XCom_DLC_Day0 |

Zmiana dotyczy listy pakietów kompilatora SDK. Zachować foldery i gotowe
pakiety DLC oraz konfigurację zainstalowanej gry. Nie tworzyć fikcyjnego UC.
DefaultEngine jest źródłem ustawień, XComEngine konfiguracją wygenerowaną;
sama edycja pliku wygenerowanego mogłaby zostać cofnięta przy regeneracji.
Po zmianie wykonać normalny build i sprawdzić nowy log. **Tej edycji i make
po niej LEAD nie wykonał na rzeczywistym SDK użytkownika.**

## Jakie nowe pliki warto przekazać

Przydatna jest aktualna migawka roboczego Development/Src, z którego SDK
rzeczywiście kompiluje: wyłącznie .uc i .uci. Dwa pliki konfiguracji powyżej
pomogą potwierdzić bieżącą listę pakietów. Manifest względnych ścieżek,
rozmiarów i SHA-256 umożliwi LEAD i HELPEROWI porównanie nowego SDK
z wcześniejszym i wykorzystanie tylko nowych lub zmienionych definicji.

Kolektor zachowuje domyślne Auto (preferuje SrcOrig, potem Src).
Jawne SourceTree=Src wybiera drzewo robocze bez cichego fallbacku;
IncludeBuildConfig dodaje tylko DefaultEngine.ini i XComEngine.ini.

Z katalogu projektu zawierającego tools, po ustawieniu własnej ścieżki SDK:

```powershell
$sdk = 'C:/.../XCOM 2 War of the Chosen SDK'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./tools/collect-sdk-sources.ps1 -SdkPath $sdk -SourceTree Src -IncludeBuildConfig -OutputPath ./sdk-current-for-review.zip
```

Powstały ZIP przekazać prywatnie LEAD i HELPEROWI; nie umieszczać go
w publicznym repozytorium. Kolektor kopiuje dane do archiwum, nie zmienia
SDK i odmawia nadpisania istniejącego ZIP. Zasoby Content, Binaries,
gotowe .u/.upk i PDB nie są potrzebne do tego porównania.

To narzędzia i dokumentacja; źródła UC/config moda nadal odpowiadają v32.
Przesłanie SDK nie zastępuje testu misji i końcowego wyniku gry.
