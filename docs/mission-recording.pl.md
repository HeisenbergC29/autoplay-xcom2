# Rejestr misji i obrona oddziału

Ta wersja dodaje zapis decyzji do logu gry. To rejestr diagnostyczny, nie film
ani odtwarzalny replay silnika. Ma pokazać, jakie akcje były dostępne, co wybrał
automat i co rzeczywiście wydarzyło się po rozkazach.

[Analiza pierwszego raportu z Gatecrashera i wynikające z niej poprawki](report-2026-11-02.pl.md).
[Analiza drugiej próby i rewizja `mission-report-v3`](report-2026-11-02-second.pl.md).
[Analiza trzeciej próby i rewizja `mission-report-v4`](report-2026-11-02-third.pl.md).

## Co się zmieniło w taktyce

- Overwatch konkuruje ze słabymi strzałami, zamiast zawsze otrzymywać minimalną
  ocenę. Obsługiwany jest też wariant `LongWatch` snajpera.
- Hunker Down jest oceniany według ran i zagrożenia ostrzałem. Może być
  priorytetem przy podpaleniu, ponieważ standardowa zdolność usuwa Burning.
  Nie jest traktowany jak ochrona przed bliską walką wręcz.
- `AidProtocol` specjalisty może osłaniać zagrożonego sojusznika. Automat
  respektuje dostępność, koszt i warunki gry, w tym już działający efekt.
- Flankowanie wymaga potencjalnej linii widzenia sprawdzonej przez silnik.
  Ruch w walce odrzuca nieodkryte pola na całej trasie; to ogranicza ryzyko
  wejścia w kolejną grupę podczas trwającej walki, ale nie gwarantuje jego braku.
- Podczas marszu do celu i eksploracji brana jest pod uwagę osłona na końcu
  ruchu. Zachowane są ograniczenia AP, wsparcia i niebezpiecznych pól.
- Po utracie widoczności niedawni przeciwnicy są pamiętani przez dwie tury.
  Poszukiwanie ich ostatniej widocznej pozycji odbywa się krótkimi krokami;
  częściowe przeładowanie nie wypiera wtedy overwatch. Ocena spekulacyjnego
  ruchu została ograniczona, aby nie wypierała dobrego strzału.
- Przy ukrytym oddziale atak może zostać poprzedzony przygotowaniem pozycji
  pozostałych żołnierzy i overwatch. Strzelec otwierający zachowuje akcję;
  przygotowanie ma limit sześciu poleceń na turę.
- Bezpieczny granat na pojedynczy cel może konkurować ze słabym strzałem,
  jeśli ma duże obrażenia z szansą zabicia albo sprawdzone dobicie sojusznika.

Przycisk Skyranger oznacza wezwanie ewakuacji, jeśli misja na nią pozwala.
Ewakuacja nie oznacza zwycięstwa w Gatecrasherze. Automat korzysta ze strefy
ewakuacji oraz jej wyznaczania zgodnie z dotychczasowymi regułami misji; nie
przerywa sam Gatecrashera tylko dlatego, że walka idzie źle.

Nie każda zdolność gracza ma automatyczny planer. Obsługiwane są skonfigurowane
ataki, leczenie, stabilizacja, przeładowanie, overwatch, hunker, Aid Protocol,
zwykłe granaty Frag/Alien oraz rozpoznane akcje celu i ewakuacji. Pozostałych
zdolności automat nie uruchamia bez rozpoznania sposobu celowania i skutków.
Rejestr pokazuje także dostępne polecenia bez planera, żeby kolejne zmiany
wynikały z konkretnej misji.

## Zbudowanie i pierwsza próba

1. Pobierz aktualny `main`, rozpakuj źródła i zbuduj jak poprzednio na zachowanym
   SDK WOTC. Bez `-BuildBase`, jeśli pakiety bazowe są już przygotowane.
2. Zainstaluj nowy `dist\AutoplayXCom2.zip` i uruchom grę ponownie. Stara paczka
   z `release` nie zawiera rejestratora.
3. Wczytaj osobny zapis Gatecrashera na Commanderze albo Legendzie. Włącz
   autoplay. Rejestr rozpoczyna się przy pierwszym włączeniu i obejmuje też tury
   przeciwnika oraz późniejsze ręczne działania po zatrzymaniu autoplaya.
4. Po wyniku misji zbierz raport **przed ponownym uruchomieniem gry**, ponieważ
   następne uruchomienie zmienia pliki logów.

## Jak zebrać raport po misji

Możesz wcześniej usunąć pobrane źródła — skrypt jest instalowany razem z modem.
Otwórz w Eksploratorze folder:

```text
<SteamLibrary>\steamapps\common\XCOM 2\XCom2-WarOfTheChosen\XComGame\Mods\AutoplayXCom2\Diagnostics
```

Wpisz `powershell` w pasku adresu i naciśnij Enter. W otwartym oknie uruchom:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\Collect-MissionRecording.ps1'
```

Skrypt poda ścieżkę do nowego ZIP-a w:

```text
<Dokumenty>\AutoplayXCom2-Reports\
```

Załącz ten ZIP do rozmowy i dopisz poziom trudności, wynik, straty oraz czy
wydawałeś rozkazy ręcznie. Skrypt kopiuje `Launch.log` i do trzech najnowszych
kopii logu; nie zmienia ich i niczego nie wysyła samodzielnie.

Jeśli zachowałeś źródła, odpowiednikiem jest uruchomienie z ich katalogu:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\collect-mission-recording.ps1'
```

Możesz opcjonalnie dołączyć konkretny zapis taktyczny sprzed złej decyzji:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\Collect-MissionRecording.ps1' -SavePath 'D:\Zapisy\PrzedDecyzja.XComSave'
```

Zapis jest dołączany wyłącznie po podaniu `-SavePath`. Skrypt nie zbiera gry
ani SDK. W przypadku innej lokalizacji Dokumentów można podać `-LogDirectory`.

## Zawartość i ograniczenia rejestru

Wpisy `APXREC` zawierają identyfikator sesji, turę i zespół wykonujący ruch,
pozycje i stan własnego oddziału, kontakty widoczne dla gracza, dostępność
zdolności, najlepsze kandydatury z każdego planera, wybraną akcję i ocenę,
podgląd trafienia i surowych obrażeń oraz rzeczywiste wyniki akcji z historii.
Śledzone są także pauzy, odrzucenie rozkazu i koniec obserwacji.
Rewizja `mission-report-v4` dodaje znaczniki `ambush_setup` i `ambush_opening`.
Podsumowania `grenade_scan` rozróżniają dopuszczone i odrzucone okazje na
pojedynczy cel (`single_opportunities`, `single_rejected`) oraz ostatnie minimalne
i maksymalne obrażenia, HP celu i ocenę dostępnego zwykłego strzału. Liczniki
dotyczą sprawdzanych punktów w kolejnych decyzjach, a nie liczby rzuconych granatów.

Podgląd nie przewiduje ukrytego losowania. Zniknięcie przeciwnika z pola widzenia
nie jest uznawane za zabicie. Brak końcowego wpisu albo osiągnięcie limitu
oznacza niepełne dane, a nie domyślnie wygraną lub przegraną. Rejestr nie
wykorzystuje ukrytych pozycji do wybierania akcji.

Do lokalnego podsumowania na komputerze z Pythonem służy:

```powershell
python .\tools\analyze-mission-log.py 'D:\Raporty\AutoplayXCom2-raport.zip' --json 'D:\Raporty\analiza.json'
```

Ustawienia w `Config\XComAutoplayXCom2.ini`:

```ini
[AutoplayXCom2.APX_Controller]
EnableMissionRecording=true
RecordCandidateScores=true
RecordingInterval=1.0
ContactMemoryTurns=2
ContactSearchDistance=4.0
CoordinateConcealedAmbush=true

[AutoplayXCom2.APX_SquadPlanner]
MaxCandidateTiles=64
MaxPreparationActionsPerTurn=6

[AutoplayXCom2.APX_MissionRecorder]
MaxRecords=20000
MaxHistoryFramesPerObserve=128
```

Zmiany wprowadzaj przy zamkniętej grze. Raport pozwala analizować decyzje,
ale nie potwierdza, że nowa wersja wygrywa misję. Kompilacja Windows i rzeczywisty
Gatecrasher nadal wymagają sprawdzenia w grze.
