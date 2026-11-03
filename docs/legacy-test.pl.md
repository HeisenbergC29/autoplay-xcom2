# Kolejna misja „Blast From the Past” — v9

Pierwsza misja `ChallengeAbductionGasStation` została ukończona zwycięstwem
na v8: Dowódca, 14 tur, dwóch poległych. Potwierdzają to użytkownik i końcowy
rekord `outcome=win`. [Raport zwycięskiej próby](report-2026-11-03-legacy-v8-win.pl.md).
Log pokazuje też wczytanie drugiego etapu `ChallengeAbductionCemetery`.

Do następnej próby **zbuduj i zainstaluj v9**. Dodaje podejście ratownika do
wykrwawiającego się żołnierza, zbieranie łupu oraz dane punktacji.
Poprzednie zwycięstwo pozostaje wynikiem v8, commitu `3859882`.
[Opis nowych zasad i granic](tactics-v9.pl.md).
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

1. Uruchom następny etap Legacy Operations „Blast From the Past” na nowej
   v9. Oczekiwany typ to `ChallengeAbductionCemetery`, etap 2; zachowaj
   ustawienia trudności i ciągłość punktacji z poprzedniej misji.
2. Po uzyskaniu sterowania włącz autoplay klawiszem F8. Automat startuje
   wyłączony po zmianie misji. W `Launch.log` sprawdź
   `revision=mission-report-v9`; inna rewizja oznacza uruchomienie starszego kodu.
3. Pozwól misji dojść do wyniku; zapisz ewentualne ręczne działania,
   ich moment i powód.
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
heurystykę. V9 nie gwarantuje zwycięstwa ani bezpiecznej reakcji łańcuchowej.
