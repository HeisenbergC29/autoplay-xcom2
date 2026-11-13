# SDK: duplikaty TLE w DLC_3

Kompilacja moda po poprawce nawiasu zakończyła się PASS: 0 błędów i 12 ostrzeżeń.
Pełne SDK usunęło siedem brakujących odwołań do zasobów, zachowało jedno
ostrzeżenie Day0 i ujawniło 11 zduplikowanych klas: 8 − 7 + 11 = 12.
Użytkownik potwierdził instalację Steam i identyczne cztery kopie przykładowej
X2Ability_TLE_Abilities.uc w Src/SrcOrig oraz DLC_3/TLE. Hash odpowiada też
plikowi TLE we wcześniej przekazanym SDK. Pochodzenie kopii pozostaje nieustalone.

## Zakres narzędzia

tools/repair-sdk-tle-duplicates.ps1 domyślnie tylko raportuje plan. Jawne
-Apply przenosi do unikalnej kopii zapasowej poza SDK wyłącznie zgłoszone
11 nazw klas z DLC_3/Classes w obu drzewach. Każda kopia musi mieć identyczny
SHA-256 jak odpowiednik TLE w tym samym drzewie; różnica zatrzymuje całą
operację przed przeniesieniem plików. Pozostałe pliki DLC_3 i wszystkie
właściwe pliki TLE są zachowane. Przy pełnym zestawie to 22 kopie źródeł.

Przy naprawie narzędzie zachowuje także stare SDK XComGame/Script/DLC_3.u
i TLE.u w backupie, aby następny build bazy nie użył poprzednich definicji.
Manifest lokalny zawiera ścieżki, hashe i stan operacji. Narzędzie nie uruchamia
kompilatora, gry ani nie modyfikuje instalacji gry. Przy błędzie próbuje cofnąć
ukończone przeniesienia; manifest podaje ewentualny stan RollbackIncomplete.
Backup zawiera prywatne pliki SDK i nie powinien trafiać do repozytorium.

## Uruchomienie w Windows

Zamknąć ModBuddy i procesy SDK korzystające z pakietów. W PowerShellu,
z katalogu projektu zawierającego tools, ustawić własną ścieżkę SDK:

```powershell
$sdk = 'C:/.../XCOM 2 War of the Chosen SDK'
$backup = Join-Path $env:USERPROFILE 'AutoplayXCom2-SdkBackups'
./tools/repair-sdk-tle-duplicates.ps1 -SdkPath $sdk
./tools/repair-sdk-tle-duplicates.ps1 -SdkPath $sdk -BackupRoot $backup -Apply
```

Pierwsza komenda pokazuje plan bez zmian. Druga sprawdza wszystkie pary
i zapisuje wynik z BackupPath. Brak duplikatów oznacza NoChanges, bez
nowego backupu lub przenoszenia pakietów. Niepewne wersje wymagają porównania,
nie automatycznego wybierania pliku do zachowania.

Następnie przebudować bazę SDK i mod. Dla repozytoryjnego budowania:

```powershell
./tools/build.ps1 -SdkPath $sdk -BuildBase
```

Zachować zwykle używane argumenty instalacji, np. GamePath, jeśli były
stosowane. Bez GamePath skrypt przygotowuje paczkę w dist; do gry trzeba
wdrożyć wynik zgodnie z dotychczasowym sposobem instalacji. Przekazać wynik
nowego builda. Właściwą naprawę konkretnego SDK i nowy wynik ostrzeżeń
potwierdzi dopiero ta próba użytkownika. Ostrzeżenie Day0 jest osobne.

## Przywrócenie

Zachować BackupPath i manifest.json. Przed przywracaniem zamknąć SDK;
manifest wskazuje RelativePath każdego pliku względem SDK. Przenieść pliki
z backupu z powrotem do tych lokalizacji po porównaniu hashy. Jeśli build
utworzył nową wersję pod daną ścieżką, najpierw zachować ją osobno, zamiast
nadpisywać. Częściowe automatyczne wycofanie opisuje stan manifestu.

## Weryfikacja i granice

Testy PowerShell używają wyłącznie sztucznych katalogów i plików. Obejmują
tryb raportu, poprawną naprawę i backup, zachowanie TLE/innych klas,
odmowę przy różnicy hashy, brak zmian po ponownym uruchomieniu i niebezpieczne
ścieżki. CI wykonuje je w PowerShell 7 oraz Windows PowerShell 5.1.
To test narzędzia plikowego, bez prawdziwego SDK lub kompilatora WOTC.
Runtime i źródła UC moda pozostają v32; aktualizacja narzędzi nie wymaga
nowej wersji taktyki. [Dowód kompilacji](build-2026-11-13-v32.pl.md),
[koordynacja #73](https://github.com/HeisenbergC29/autoplay-xcom2/issues/73).
