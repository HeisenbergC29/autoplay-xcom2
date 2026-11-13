# Aktualna migawka SDK i ostatnie ostrzeżenie Day0

## Co potwierdziły nowe logi

Po uporządkowaniu duplikatów TLE baza i mod skompilowały się z wynikiem
PASS, każdy z 0 błędów i 1 ostrzeżeniem. Pozostało wyszukiwanie UC pustego
XCom_DLC_Day0, wymienionego na liście kompilacji SDK. Najnowszy mod-make
również kończy się 0/1. [Raport gry v32](report-2026-11-13-v32.pl.md)
jest już dostępny; pojedyncze ostrzeżenie nie zatrzymuje kompilacji.

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

Samo rozszerzenie kolektora nie zmienia kodu moda. Dostarczona migawka
dotyczy v32; nowa polityka X4 ma osobną rewizję v33.
Przesłanie SDK nie zastępuje testu misji i końcowego wyniku gry.

## Otrzymana migawka — niezależny audyt LEAD

Sdk-current-for-review.zip przesłano obu agentom. CRC i wszystkie 4170
rozmiarów/SHA-256 manifestu PASS, bez dodatkowych plików:
4161 UC, 7 UCI, 2 INI. Po wyłączeniu 24 UC moda pozostają 4144 źródła gry,
każde bajtowo identyczne z poprzednim Development/SrcOrig, 15 pakietów.
Nie ma nowych, zmienionych ani usuniętych definicji do importowania.
Nie ponawiamy generowania katalogu jednostek dla identycznych wejść.
Wszystkie 24 UC moda odpowiadają main a4b0b1cd; nie utożsamiać migawki
źródeł z potwierdzeniem hash skompilowanego pakietu.

Oba INI również odpowiadają poprzednim konfiguracjom SDK. Nadal mają
aktywne wpisy Day0 opisane powyżej, a pakiet nie ma źródeł UC.
Nowy log nie potwierdza wykonania opcjonalnej edycji ani wyniku 0/0.
Archiwum SDK ma SHA-256
f4c75dce0d4a412b0221e9af9e365b9b268109124b643986eca9b5f28a71790a.
SDK i oba INI pozostają prywatne; publikujemy tylko ten wyciąg.
