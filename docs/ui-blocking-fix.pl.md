# Poprawka: „Paused: screen / menu” i brak rozkazów

W paczce `0.1.0-alpha` kontroler błędnie wymagał, żeby główny HUD był najwyższym ekranem interfejsu. W zwykłym WOTC nad nim działają również nakładki tury i celu misji. Mod rozpoznawał je jako menu i nie dochodził do wydawania rozkazów. To błąd moda.

Poprawka w źródłach rozpoznaje standardowe nakładki HUD-u. Nadal czeka na zamknięcie rzeczywistego menu lub dialogu i zakończenie ręcznego celowania. Status pod przyciskiem rozróżnia także pauzę gry, blokadę sterowania i oczekiwanie na HUD. Zmiany przyczyny oczekiwania są zapisywane w `Launch.log`.

**Stary ZIP `AutoplayXCom2-WOTC-0.1.0-alpha.zip` nie zawiera poprawki.** Potrzebna jest nowa kompilacja pliku `AutoplayXCom2.u`. Kontrola źródeł i testy regresji nie zastępują kompilacji SDK ani próby w grze; tych dwóch kroków nie można wykonać w obecnym środowisku Linux.

## 1. Zaktualizuj źródła na swoim komputerze

Zamknij grę i launcher. Zachowaj ewentualne własne zmiany konfiguracji.

1. Pobierz [aktualne źródła z GitHuba](https://github.com/HeisenbergC29/autoplay-xcom2/archive/refs/heads/main.zip).
2. Rozpakuj ZIP. Otwórz rozpakowany folder `autoplay-xcom2-main`.
3. Skopiuj **jego zawartość** do istniejącego `C:\XCOM2-Autoplay`, potwierdzając zastąpienie plików. Nie kopiuj samego folderu `autoplay-xcom2-main` jako podfolderu.
4. Sprawdź, że istnieją `C:\XCOM2-Autoplay\tools\build.ps1` i `C:\XCOM2-Autoplay\AutoplayXCom2\Src\AutoplayXCom2\Classes\APX_Controller.uc`.

## 2. Zbuduj mod ponownie

Otwórz PowerShell i wklej:

```powershell
Set-Location 'C:\XCOM2-Autoplay'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\build.ps1' -SdkPath 'C:\Program Files (x86)\Steam\steamapps\common\XCOM 2 War of the Chosen SDK'
```

Jeżeli SDK masz na innym dysku, zmień tylko ścieżkę po `-SdkPath`. To katalog SDK, zawierający `Binaries\Win64\XComGame.com`, a nie katalog zwykłej gry. `-ExecutionPolicy Bypass` dotyczy tylko uruchamianego procesu i pozwala wykonać niepodpisany skrypt; nie zmienia trwale ustawień PowerShell.

Ponieważ wcześniej udało się zbudować bazę SDK, teraz **nie dodawaj `-BuildBase`**. Jeśli przeniosłeś się na nową instalację SDK i skrypt zgłosi brak pakietów bazowych, dopiero wtedy uruchom polecenie ponownie z `-BuildBase`.

Po sukcesie nowa paczka będzie tutaj:

```text
C:\XCOM2-Autoplay\dist\AutoplayXCom2.zip
```

Jeśli kompilacja zgłosi błąd, prześlij tutaj nowy `C:\XCOM2-Autoplay\.build\mod-make.log`. Nie instaluj wtedy wcześniejszego ZIP-a jako poprawionej wersji.

## 3. Zastąp mod w grze

1. Otwórz katalog modów WOTC, zwykle:

   ```text
   C:\Program Files (x86)\Steam\steamapps\common\XCOM 2\XCom2-WarOfTheChosen\XComGame\Mods
   ```

2. Przenieś dotychczasowy folder `AutoplayXCom2` poza katalog `Mods`, żeby zachować kopię.
3. Wypakuj **nowy** `C:\XCOM2-Autoplay\dist\AutoplayXCom2.zip` do katalogu `Mods`.
4. Sprawdź końcową ścieżkę:

   ```text
   ...\XComGame\Mods\AutoplayXCom2\Script\AutoplayXCom2.u
   ```

   Nie może być dodatkowego poziomu `AutoplayXCom2\AutoplayXCom2`.

5. Uruchom ponownie **War of the Chosen**, z włączonym modem. Nie trzeba zaczynać nowej kampanii.

## 4. Sprawdź działanie

Wczytaj osobny zapis zwykłej misji, poza samouczkiem. W turze gracza, z jednostkami mającymi punkty akcji, zamknij menu i anuluj ewentualne ręczne celowanie. Włącz autoplay. Zwykłe nakładki tury i celu misji nie powinny już powodować stałego statusu „PAUSED: SCREEN / MENU”.

Jeśli jednostki nadal nie reagują, podaj dokładny nowy status i prześlij tutaj plik:

```text
<Dokumenty>\My Games\XCOM2 War of the Chosen\XComGame\Logs\Launch.log
```

`<Dokumenty>` oznacza faktyczny folder Dokumenty Windows, także jeśli jest przeniesiony do OneDrive. W logu będą wpisy kategorii `AutoplayXCom2`, m.in. `Waiting:`, `UI stack:` i informacja o gotowości do rozkazów. Nie potrzeba teraz kolejnych plików źródeł gry.
