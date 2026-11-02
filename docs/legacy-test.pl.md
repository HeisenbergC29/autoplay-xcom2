# Kolejna próba „Blast From the Past” — mission-report-v7

Źródła kontynuują commit `ed74176` oraz v6. Najnowszy przesłany raport zawiera
próbę `ChallengeAbductionGasStation` na v6, zakończoną porażką w turze 5.
V7 obejmuje ograniczenia wsparcia i bezpieczeństwa trasy przy ruchu do ataku
wręcz oraz koszt utraty dostępnego ataku przez wydanie AP na niebieski ruch.
[Analiza poprzedniej próby](report-2026-11-02-legacy-v6.pl.md).
Nie ma jeszcze kompilacji Windows ani wyniku v7 w grze. Pełne źródła SDK
z przesłanego `Development.rar` pozostają dostępne do kontroli zgodności.
Kontrola v7: 189 testów Python zaliczonych bez pominięć oraz poprawny audyt
odwołań do SDK. Do tej kontroli nie potrzeba kolejnych plików.

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
   `revision=mission-report-v7`; obecność v5/v6 oznacza uruchomienie starszego kodu.
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

- Szarża Centrala: poprzednia trasa kończyła się ponad 10 pól od najbliższego
  sojusznika, przy początkowym dystansie 1 pola. Taki atak powinien zostać
  odrzucony przez te same ograniczenia wsparcia co zwykły ruch. Nadal możliwy
  jest wspierany, bezpieczny atak wręcz.
- Ruch snajpera: w poprzedniej decyzji 6 zużywał AP potrzebne do strzału
  karabinem. Porównaj wycenę ataku przed ruchem i przy pozostałych AP.
  Pola `best_attack_now`, `best_attack_after_move_ap`, `potential_attack_loss`
  pokazują porównanie tego samego bieżącego zestawu celów przy obu budżetach AP.
  Zwykły strzał wymagający 1 AP, brak celu i awaryjny odwrót rannego powinny
  zachować dotychczasowe możliwości.
- `move_threat_preview` nadal podaje `melee_only`, dystans i wkład każdego
  widocznego wroga. Ocena AP nie przewiduje nowego LOS ani pewnego trafienia.
- Granaty: dotychczas odrzucały je zasięg i bezpieczeństwo. Te ograniczenia
  pozostają aktywne; zero granatów samo nie wskazuje błędu punktacji.

Próg 12 pól w ocenie ryzyka wręcz pozostaje heurystyką. V7 nie przewiduje
pełnej trasy i obszaru ataku Faceless ani nie gwarantuje zwycięstwa.
