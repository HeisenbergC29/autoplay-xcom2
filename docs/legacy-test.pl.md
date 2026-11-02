# Kolejna próba „Blast From the Past” — mission-report-v6

Źródła kontynuują commit `ed74176`. Najnowszy przesłany raport już zawiera
pierwszą misję `ChallengeAbductionGasStation` na v5, zakończoną porażką.
V6 ujednolica ocenę ostrzału za przeszkodą przy ruchu i obronie oraz dodaje
dokładniejsze dane o zagrożeniach. [Analiza poprzedniej próby](report-2026-11-02-legacy.pl.md).
Nie ma jeszcze kompilacji Windows ani wyniku v6 w grze.

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

1. Uruchom WOTC z oficjalnymi DLC i tylko AutoplayXCom2. Otwórz pierwszą misję
   Legacy Operations „Blast From the Past”. Zachowaj ustawienia poprzedniej
   próby; w jej logu `difficulty=2` (Dowódca). Jeśli masz zapis sprzed pierwszego
   kontaktu z tej próby, użyj go do porównania.
2. Po uzyskaniu sterowania włącz autoplay klawiszem F8. W `Launch.log` sprawdź
   `revision=mission-report-v6`; obecność v5 oznacza uruchomienie starszego kodu.
3. Pozwól misji dojść do wyniku. Jeśli potrzebna będzie ręczna interwencja,
   zapisz jej moment i powód. Raport po zwycięstwie jest równie przydatny.
4. Po misji, przed ponownym uruchomieniem gry, otwórz PowerShell w folderze
   `XComGame\Mods\AutoplayXCom2\Diagnostics` i zbierz raport:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Collect-MissionRecording.ps1
```

Raport trafia do `<Dokumenty>\AutoplayXCom2-Reports`. Dołącz ZIP, wynik misji,
straty i informację o ręcznych działaniach. Zbieranie raportu działa po usunięciu
pobranych źródeł moda.

## Co porównać w raporcie

- Aid Protocol przy wrogu zasłoniętym przeszkodą: na lokalnych danych decyzji 5
  z v5 jego ocena spada z 32.8 do 21.88, poniżej odwrotu ocenionego na 26.
  Inny przebieg misji może dać inne akcje i wartości.
- Ruchy Centrala: `move_threat_preview` podaje osobno `melee_only`, dystans
  i wkład każdego wroga. Sprawdź, czy odwrót oddala od Faceless i czy pozostaje
  możliwość skutecznego ataku. Samo dojście do osłony nie chroni przed pazurami.
- Granaty: dotychczas odrzucały je zasięg i bezpieczeństwo. Te ograniczenia
  pozostają aktywne; zero granatów samo nie wskazuje błędu punktacji.

Próg 12 pól w ocenie ryzyka wręcz pozostaje heurystyką. V6 nie przewiduje
pełnej trasy i obszaru ataku Faceless ani nie gwarantuje zwycięstwa.
