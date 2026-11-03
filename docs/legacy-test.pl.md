# Kolejna misja „Blast From the Past” — ta sama v8

Pierwsza misja `ChallengeAbductionGasStation` została ukończona zwycięstwem
na v8: Dowódca, 14 tur, dwóch poległych. Potwierdzają to użytkownik i końcowy
rekord `outcome=win`. [Raport zwycięskiej próby](report-2026-11-03-legacy-v8-win.pl.md).
Log pokazuje też wczytanie drugiego etapu `ChallengeAbductionCemetery`.

Do następnej próby użyj **tej samej zainstalowanej v8**. Zmienia się etap
testu i zakres zbieranych wyników; nowa kompilacja nie jest potrzebna.
Źródłowy punkt odniesienia kodu to commit `3859882`.
[Opis nowych zasad i granic](tactics-v8.pl.md).
Pełne źródła SDK z przesłanego `Development.rar` pozostają dostępne do kontroli zgodności.
Kontrola v8: 218 testów Python zaliczonych bez pominięć oraz poprawny audyt
odwołań do SDK. Do tej kontroli nie potrzeba kolejnych plików.

## Zbudowanie na zachowanym SDK — tylko przy ponownej instalacji

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

1. Uruchom następny etap Legacy Operations „Blast From the Past” na tej samej
   v8. Oczekiwany typ to `ChallengeAbductionCemetery`, etap 2; zachowaj
   ustawienia trudności i ciągłość punktacji z poprzedniej misji.
2. Po uzyskaniu sterowania włącz autoplay klawiszem F8. Automat startuje
   wyłączony po zmianie misji. W `Launch.log` sprawdź
   `revision=mission-report-v8`; obecność v5/v6/v7 oznacza uruchomienie starszego kodu.
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
zapisz go osobno. Obecny rejestrator nie zapisuje oficjalnej punktacji Legacy;
pole `score` w decyzjach jest oceną planera. Przy braku liczby wpisujemy
„niezarejestrowana”, bez utożsamiania z `MaxScore` z tabel startowych.
Zbieranie raportu działa po usunięciu pobranych źródeł moda.

## Co obserwować w następnym etapie

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
  punkty i wynik skumulowany. Zwycięstwo pierwszej misji potwierdza postęp,
  a dwóch poległych pozostaje kosztem do uwzględnienia w ocenie jakości.

Nowy zasięg wręcz jest geometrycznym przybliżeniem możliwego ataku, bez
planowania rzeczywistej przyszłej trasy. Nieznane style zachowują poprzednią
heurystykę. V8 nie gwarantuje zwycięstwa ani bezpiecznej reakcji łańcuchowej.
