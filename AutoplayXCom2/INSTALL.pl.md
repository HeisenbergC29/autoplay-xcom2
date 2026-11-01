# Instalacja Autoplay XCOM 2

Ta instrukcja dotyczy paczki **zawierającej `Script\AutoplayXCom2.u`**. Archiwum źródeł pobrane przez GitHub „Download ZIP” wymaga najpierw kompilacji opisanej w README repozytorium. Nie jest gotowym modem.

## Wymagania

- XCOM 2: War of the Chosen na Windows. Mod jest przygotowywany dla gry z oficjalnymi dodatkami.
- Launcher pozwalający włączać mody WOTC, np. Alternative Mod Launcher.
- SDK jest potrzebne wyłącznie do budowania; do instalacji gotowej paczki z `.u` nie jest wymagane.

## Instalacja paczki po kompilacji

1. Zamknij grę i launcher.
2. Rozpakuj `AutoplayXCom2.zip` do:

```text
<SteamLibrary>\steamapps\common\XCOM 2\XCom2-WarOfTheChosen\XComGame\Mods\
```

Po rozpakowaniu układ musi wyglądać tak:

```text
Mods\AutoplayXCom2\AutoplayXCom2.XComMod
Mods\AutoplayXCom2\Script\AutoplayXCom2.u
Mods\AutoplayXCom2\Config\XComEngine.ini
Mods\AutoplayXCom2\Config\XComGame.ini
Mods\AutoplayXCom2\Config\XComAutoplayXCom2.ini
Mods\AutoplayXCom2\Localization\AutoplayXCom2.pol
Mods\AutoplayXCom2\Localization\AutoplayXCom2.int
```

Nie twórz podwójnego katalogu `AutoplayXCom2\AutoplayXCom2`. Jeśli aktualizujesz ręcznie, zachowaj własne zmiany konfiguracji i zastąp katalog poprzedniej wersji, aby nie pozostawić starego `.u`.

3. Uruchom launcher dla **War of the Chosen**. W AML odśwież listę modów; jeśli katalog lokalnych modów nie jest wykrywany, dodaj powyższy folder `XComGame\Mods` do katalogów modów w ustawieniach AML.
4. Zaznacz **Autoplay XCOM 2** i uruchom WOTC. Nie trzeba włączać konsoli deweloperskiej.
5. Wczytaj misję. Automat zaczyna wyłączony. Na pierwszą próbę użyj osobnego zapisu testowego i wykonaj próby opisane w `docs/TESTING.pl.md` repozytorium.

## Użycie

- Najedź na subtelny znacznik przy środku prawej krawędzi ekranu, aby odsłonić przycisk.
- Kliknij „WŁĄCZ AUTOPLAY”; ponowne kliknięcie zatrzymuje automat.
- **F8** przełącza automat, również gdy gra ukrywa HUD podczas tury przeciwnika. Sekwencja przechwytująca wejście może opóźnić obsługę klawisza.
- **Escape** zatrzymuje automat i zachowuje zwykłe działanie pauzy.
- Zatrzymanie blokuje następny rozkaz. Trwający strzał, ruch lub inna akcja kończy się zgodnie z silnikiem gry.
- Po wczytaniu zapisu lub zmianie misji automat pozostaje wyłączony. Nie zamyka samodzielnie nieznanych dialogów fabularnych.
- Podczas ręcznego celowania automat czeka. Zakończ lub anuluj celowanie, aby mógł kontynuować; rozpoczęcie własnego ruchu przez automat usuwa stare punkty ręcznej trasy.

## Ustawienia

Domyślne ustawienia znajdują się w `Config\XComAutoplayXCom2.ini` w katalogu moda. Własne nadpisania gry mogą znajdować się w:

```text
<Dokumenty>\My Games\XCOM2 War of the Chosen\XComGame\Config\XComAutoplayXCom2.ini
```

Najważniejsze opcje:

```ini
[AutoplayXCom2.APX_Controller]
ToggleKey=F8
DecisionInterval=0.75
AutoEndTurn=true
AutoCompleteOwnedHacks=true
ExploreUnseenMap=true
AutoPlaceEvac=true
UseExplosiveGrenades=true

[AutoplayXCom2.APX_UITacticalControl]
OffsetX=-220.0
OffsetY=-27.0
CollapseDelaySeconds=2.0
IndicatorAlpha=35.0
```

Położenie jest liczone od środka prawej krawędzi. Bardziej ujemne `OffsetX` przesuwa panel w lewo; dodatnie `OffsetY` w dół. Pozwala to usunąć kolizję z innymi modami HUD. Zmiany wprowadzaj przy zamkniętej grze.

## Diagnoza

- Brak przycisku: sprawdź, czy uruchomiono WOTC, mod jest zaznaczony, istnieje plik `.u` i nie ma podwójnego katalogu.
- Status „STOP”: automat oddał sterowanie z powodu braku planu, odrzuconej akcji lub limitu. Przyczyna jest zapisywana pod znacznikiem `AutoplayXCom2` w `Launch.log`.
- Log gry: `<Dokumenty>\My Games\XCOM2 War of the Chosen\XComGame\Logs\Launch.log`. Do zgłoszenia dołącz typ misji, etap i listę pozostałych modów.
- Wyłączenie moda: odznacz go w launcherze. Bieżące włączenie autoplaya nie jest zapisywane w kampanii.

Ta wersja wymaga kompilacji i prób w grze. Obecność paczki instalacyjnej nie jest potwierdzeniem pełnej obsługi każdej skryptowanej misji DLC; stan weryfikacji opisuje README repozytorium.
