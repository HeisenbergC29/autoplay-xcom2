# Paczka do instalacji — 0.1.0 alpha

**Znany błąd tej paczki:** po włączeniu autoplay zwykły HUD może powodować stały status `PAUSED: SCREEN / MENU` i brak rozkazów. Ta paczka nie zawiera poprawki. Poprawka jest dostępna w źródłach i wymaga nowej kompilacji w SDK WOTC; [instrukcja aktualizacji](../docs/ui-blocking-fix.pl.md). Działanie poprawki w grze pozostaje do potwierdzenia.

Dotychczasowe archiwum [AutoplayXCom2-WOTC-0.1.0-alpha.zip](AutoplayXCom2-WOTC-0.1.0-alpha.zip) zachowano do porównania. Zawarty w nim katalog `AutoplayXCom2` jest przeznaczony do:

```text
<SteamLibrary>\steamapps\common\XCOM 2\XCom2-WarOfTheChosen\XComGame\Mods\
```

W archiwum jest skompilowany `Script/AutoplayXCom2.u`, komplet konfiguracji, napisy PL/EN i instrukcja `INSTALL.pl.md`. Do instalacji tej paczki nie potrzeba SDK ani kompilacji.

Docelowo: **XCOM 2 Collection ze Steam, Windows, uruchomione jako War of the Chosen, oficjalne dodatki i tylko ten mod**. Binarne importy wymagają wyłącznie standardowych pakietów `Core`, `Engine`, `XComGame`; nie ma zależności od Highlandera ani innych modów. [Szczegóły zgodności](../docs/COMPATIBILITY.pl.md).

To **wersja testowa alpha**. Kompilacja i zawartość paczki są sprawdzone. Pierwsza próba użytkownika w grze potwierdziła widoczny, klikalny przycisk, ale ujawniła opisaną wyżej blokadę. Nie potwierdzono pełnej zgodności z konkretnym najnowszym buildem Steam ani ukończenia każdej misji. Poprawkę sprawdź na osobnym zapisie zwykłej misji kampanii, poza samouczkiem.

Plik `.u` jest identyczny z plikiem przesłanym przez użytkownika po poprawnej kompilacji. Przy pakowaniu zaktualizowano instrukcję, znormalizowano separatory ZIP i dodano `BUILD-INFO.json`. Konfiguracja oraz napisy pozostały niezmienione.

SHA-256 plików jest w [SHA256SUMS](SHA256SUMS).
