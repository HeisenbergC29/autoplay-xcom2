# Instalacja Autoplay XCOM 2

Ta instrukcja dotyczy paczki **zawierającej `Script\AutoplayXCom2.u`**. Skompilowana paczka testowa jest przygotowana do instalacji. Archiwum źródeł pobrane przez GitHub „Download ZIP” nadal wymaga kompilacji opisanej w README repozytorium.

## Wymagania

- Docelowo: aktualna wersja **XCOM 2 Collection ze Steam na Windows**, uruchamiana jako **War of the Chosen**, z oficjalnymi dodatkami z kolekcji.
- Autoplay jest jedynym modem. Nie wymaga Community Highlandera, Mod Config Menu ani innych dodatków z Workshop.
- Włącz mod w launcherze obsługującym WOTC lub przez natywny plik konfiguracji opisany poniżej. Alternative Mod Launcher jest opcjonalnym launcherem, nie zależnością moda.
- SDK jest potrzebne wyłącznie do budowania; do instalacji gotowej paczki z `.u` nie jest wymagane.

## Instalacja paczki po kompilacji

1. Zamknij grę i launcher.
2. Rozpakuj `AutoplayXCom2-WOTC-0.1.0-alpha.zip` (albo własny zbudowany `AutoplayXCom2.zip`) do:

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

3. Uruchom launcher dla **War of the Chosen**, zaznacz **Autoplay XCOM 2** i uruchom WOTC. Collection to zestaw produktów; przy uruchomieniu należy wybrać dodatek War of the Chosen. Konsola deweloperska nie jest potrzebna.
4. Jeżeli używasz AML, odśwież listę modów; jeśli lokalny mod nie jest wykrywany, dodaj powyższy folder `XComGame\Mods` do katalogów modów w ustawieniach AML. Nie instaluj żadnego drugiego moda jako zależności.
5. Wczytaj misję. Automat zaczyna wyłączony. Na pierwszą próbę użyj osobnego zapisu testowego i wykonaj próby opisane w `docs/TESTING.pl.md` repozytorium.

## Włączenie przez konfigurację gry

Jeśli nie masz w launcherze listy modów, oryginalny WOTC obsługuje tablicę `ActiveMods` w klasie `Engine.XComModOptions`.

1. Uruchom raz War of the Chosen i zamknij grę.
2. Otwórz plik poniżej (w razie potrzeby utwórz go jako plik `.ini`, bez końcówki `.txt`):

```text
<Dokumenty>\My Games\XCOM2 War of the Chosen\XComGame\Config\XComModOptions.ini
```

3. W sekcji `[Engine.XComModOptions]` dodaj poniższy wpis. Dla konfiguracji z jednym modem powinna istnieć jedna aktywna pozycja `ActiveMods`:

```ini
[Engine.XComModOptions]
ActiveMods="AutoplayXCom2"
```

4. Uruchom War of the Chosen przez Steam. Jeśli launcher nadpisze tę listę, użyj jego wyboru modów albo opcjonalnego AML. To natywna ścieżka konfiguracji potwierdzona w SDK; zachowanie konkretnego launchera wymaga sprawdzenia na Twojej instalacji.

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

Kompilację potwierdzono, a zawartość paczki i zależności binarne sprawdzono. Ta wersja **alpha nie ma jeszcze testów w działającej grze**. Nie potwierdzono pełnej obsługi każdej skryptowanej misji DLC ani konkretnego najnowszego numeru builda Steam. Stan weryfikacji opisuje README repozytorium.
