# Próba Legacy i licznika punktów — v10

Pierwsza misja `ChallengeAbductionGasStation` została wcześniej ukończona
zwycięstwem na v8: Dowódca, 14 tur, dwóch poległych.
[Raport zwycięstwa](report-2026-11-03-legacy-v8-win.pl.md).
Najnowszy raport obejmuje ponowną próbę GasStation na v9: porażkę w turze 7,
ratunek snajpera oraz natywny wynik −10000 przy maksymalnej puli 46000.
[Raport v9](report-2026-11-03-legacy-v9.pl.md).

Do kolejnej próby **zbuduj i zainstaluj v10**. Dodaje nad przyciskiem licznik
punktów bieżącej misji i jej maksymalnej puli.
[Zasady działania i granice licznika](score-display-v10.pl.md).
Pełne źródła SDK z przesłanego `Development.rar` pozostają dostępne do kontroli zgodności.
Do kontroli źródeł i kontraktów SDK nie potrzeba kolejnych plików.

## Zbudowanie na zachowanym SDK

Rozpakuj nowy ZIP źródeł i otwórz PowerShell w katalogu z `README.md` oraz `tools`.
Podstaw własne ścieżki SDK i gry w poniższym poleceniu:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build.ps1 `
  -SdkPath 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK' `
  -GamePath 'D:\SteamLibrary\steamapps\common\XCOM 2\XCom2-WarOfTheChosen'
```

Pomiń `-BuildBase`, jeśli bazowe pakiety SDK są już zbudowane. Instalowany wynik
to świeże `dist\AutoplayXCom2.zip`; stara paczka z `release` nie zawiera zmian.
Przy błędzie kompilacji zachowaj `.build\mod-make.log`. Po udanej instalacji
uruchom grę ponownie. Źródła możesz później usunąć; SDK zachowaj.

## Przebieg porównawczy

1. Uruchom wybrany zapis Legacy Operations „Blast From the Past” na nowej
   v10. Dla kontynuacji wcześniejszego zwycięstwa oczekiwany jest
   `ChallengeAbductionCemetery`, etap 2; ponowienie najnowszej przegranej
   dotyczy `ChallengeAbductionGasStation`, etap 1. Zapisz etap i trudność.
2. Po uzyskaniu sterowania, przed F8, sprawdź licznik nad przyciskiem.
   Powinien działać przy wyłączonym autoplay, używać tej samej wielkości
   czcionki i przepuszczać kliknięcia mapy. Maksimum nie powinno maleć po
   zabiciach; w drugim etapie licznik nie może doliczać punktów poprzedniej misji.
3. Włącz autoplay klawiszem F8. Automat startuje wyłączony po zmianie misji.
   W `Launch.log` sprawdź `revision=mission-report-v10`; inna rewizja oznacza
   uruchomienie starszego kodu. Pozwól misji dojść do wyniku; zapisz ewentualne
   ręczne działania, ich moment i powód.
4. Po misji, przed ponownym uruchomieniem gry, otwórz PowerShell w folderze
   `XComGame\Mods\AutoplayXCom2\Diagnostics` i zbierz raport:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Collect-MissionRecording.ps1
```

Raport trafia do `<Dokumenty>\AutoplayXCom2-Reports`. Do ZIP-a dopisz wynik,
tury, straty, oficjalne punkty za misję i wynik skumulowany z ekranu podsumowania,
jeśli są dostępne, oraz restarty i ręczne działania. Jeśli ekran pokazuje medal,
zapisz go osobno. V9 odczytuje oficjalne `CumulativeScore` bieżącego etapu;
zmiana między odczytami obejmuje okres rejestracji od F8, który może być krótszy
od całej misji. Pole `score` w decyzjach jest oceną planera. Przy braku odczytu
oficjalnego wpisujemy „niezarejestrowana”, bez utożsamiania z `MaxScore`.
Analizator stosuje ponadto stały profil porównawczy `wotc_legacy_observed_v1`
do każdej misji, także niepunktowanej w grze. Niepełne obserwacje pozostają
oznaczone jako częściowe; wartości podane wcześniej ręcznie nie są regułami.
Zbieranie raportu działa po usunięciu pobranych źródeł moda.

## Co obserwować w następnym etapie

- Ratunek: przy wykrwawieniu sprawdź podejście żołnierza z gotową stabilizacją
  i zachowanie AP, a następnie natywną legalną stabilizację. Ostatnia tura
  wykrwawiania wymaga osiągnięcia zasięgu od razu. Przeszkody i brak ładunku
  nie mogą powodować nielegalnego leczenia. Stabilizacja zatrzymuje
  wykrwawianie; nie przywraca przytomności.
- Łup: dostępne `Loot` powinno działać zwykłą darmową zdolnością gry.
  Podejście jest ograniczone do widocznego łupu po walce, bez aktywnego
  terminu misji, wykrwawiającego się sojusznika ani pilnej ewakuacji.
  Zapisz przypadek pozostawienia łupu wraz z sytuacją taktyczną.
- Cele misji i przejścia: czy oddział wykonuje jawnie oznaczone cele,
  odnajduje pozostałych przeciwników i dochodzi do właściwego zakończenia.
  Zapisz dialog, ekran lub czynność wymagającą ręcznej interwencji.
- Wsparcie oddziału: czy szarże nie odrywają pojedynczej jednostki od reszty,
  a ruch nie powoduje pętli ani utknięcia przy nieznanym celu.
- Ruch snajpera: porównaj wycenę ataku przed ruchem i przy pozostałych AP.
  Pola `best_attack_now`, `best_attack_after_move_ap`, `potential_attack_loss`
  pokazują porównanie tego samego bieżącego zestawu celów przy obu budżetach AP.
  Zwykły strzał wymagający 1 AP, brak celu i awaryjny odwrót rannego powinny
  zachować dotychczasowe możliwości.
- `move_threat_preview` nadal podaje `melee_only`, dystans i wkład każdego
  widocznego wroga. Nowe `melee_threat_reach` pokazuje rozpoznany zasięg
  ruchu i ataku. Odwrót wewnątrz niego powinien zachować wysokie zagrożenie
  wręcz. Ocena AP nie przewiduje nowego LOS ani pewnego trafienia.
- Jeśli sektoid lub inny widoczny przeciwnik ma aktywne więzi do zombie lub
  kontrolowanego członka oddziału, sprawdź `known_released_allies` oraz
  `known_linked_enemies` przy kandydatach ataków. Premia rośnie z szansą
  dobicia źródła; samo istnienie więzi nie gwarantuje wyboru tego celu.
- Granaty: dotychczas odrzucały je zasięg i bezpieczeństwo. Te ograniczenia
  pozostają aktywne. `pair_offset_centers` pokazuje nowe propozycje dla pary,
  a `blast_blocker_*` oraz `blast_safe_radius_units` wyjaśniają ostatnią
  blokadę. Zero granatów samo nie wskazuje błędu punktacji.
- Jakość wyniku: zwycięstwo, liczba tur, rany, zgony/wyłączenia, oficjalne
  punkty, wynik skumulowany i zakres braków punktacji porównawczej.
  Zwycięstwo pierwszej misji potwierdza postęp,
  a dwóch poległych pozostaje kosztem do uwzględnienia w ocenie jakości.

Nowy zasięg wręcz jest geometrycznym przybliżeniem możliwego ataku, bez
planowania rzeczywistej przyszłej trasy. Nieznane style zachowują poprzednią
heurystykę. V10 nie gwarantuje zwycięstwa ani bezpiecznej reakcji łańcuchowej.
