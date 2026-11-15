# Wspólny odbiór v43 — jedna kompilacja i runda gry

Ta paczka łączy bieżące prace z [kolejki #86](https://github.com/HeisenbergC29/autoplay-xcom2/issues/86),
w tym medyczny [PR #98](https://github.com/HeisenbergC29/autoplay-xcom2/pull/98).
Dokładny końcowy commit i link do ZIP-a publikuje LEAD w
[#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
Pierwsza kompilacja źródeł `1191871`: **FAIL: 1 błąd / 1 ostrzeżenie**.
[Poprawka #99](fix-99-v43-compiler.pl.md) zachowuje marker v43. Pobierz nowy
dokładny ZIP z #4; kompilacja poprawionej paczki i gra v43: **NOT RUN**.

## Zakres źródeł

- Podejście medyka do pilnego leczenia/detoksu, także pacjenta bez bleeding.
  Potrzeba, własna zdolność, jej zasięg, ładunki i AP są sprawdzane przed
  bezpiecznym ruchem blue; po ruchu wymagany jest świeży natywny cel/akcja.
  Gotowe pilne leczenie ma pierwszeństwo, pacjenci usunięci z gry odpadają,
  a inspekcje medyczne mają wspólne ograniczone budżety decyzji.
- Detoks pełnozdrowego pacjenta tylko dla faktycznie usuwalnego efektu tej
  zdolności; opuszczenie chmury nie oznacza usunięcia nałożonej trucizny.
- Dwa osobne natywne ruchy blue z ponowną oceną po pierwszym oraz miękka
  pamięć tras. Kara nie zabrania jedynej legalnej drogi powrotnej, także SPARK-owi.
- Ograniczone przygotowanie zasadzki i OW, kierunkowa osłona, odstępy pod AoE,
  aktualne waypointy i jawna niepewność. Timer, ratunek i ewakuacja zachowują priorytet.
- Natywne X4/plant anchor/relay/Sweep, ochrona odzyskiwalnego sojusznika i
  preferencja potwierdzonego źródła kontroli umysłu; wąskie Faceoff i istniejące granaty.
- Native-first HUD oraz osobne proweniencje runtime observed_v3 i archiwalnego v2.
  Nie dodano premii początkowych ani fikcyjnych punktów za leczenie/cele.

To zakres implementacji, nie potwierdzenie wygranej lub wszystkich reakcji w silniku.
Pełna przyszła trasa patrolu/nieobsługiwany footprint, ogólny pojedynczy dash,
pozostałe rodziny AoE i prognoza łańcucha zawaleń pozostają jawnie nieobsługiwane
lub Unknown. Pełna mapa nie nadaje natywnych targetów/AP; `EnableFullIntel=false`
zachowuje wiedzę opartą na widoczności. Nie wymuszamy trafień ani zwycięstwa; nie odczytujemy przyszłego RNG.

## Walidacja i identyfikacja paczki

Sprawdzony źródłowy head przed poprawką kompilacji: `9771d7cb60d57163e488033e210f2c23871b4ad5`.
**876 prywatnych testów PASS/0skip**, SDK30 klas/31 nazw i niezależne review PASS;
[CI373](https://github.com/HeisenbergC29/autoplay-xcom2/actions/runs/43658871509):
876 run =791 PASS/85 SKIP oraz6 kroków PowerShell PASS. Testy medyczne obejmują
rzeczywiste helpery UC, a checker instalatora fixture wszystkich30 klas.
Końcowe publiczne SHA i pobrany ZIP (CRC, SHA256, zgodność każdego pliku z Git)
są zapisane w #4; nie umieszczamy hashów archiwum wewnątrz samego archiwum.
Zielone kontrole źródeł i parsera nie są kompilacją Windows ani testem misji.

## Zbudowanie i instalacja

1. Pobierz **jeden dokładny ZIP źródeł wskazany w #4**, rozpakuj cały projekt.
   Nie kompiluj kolejno pośrednich v33–v42. Stary ZIP `release/AutoplayXCom2-WOTC-0.1.0-alpha.zip`
   jest historyczną binarką; nie zastępuje aktualnych źródeł.
2. Użyj zachowanego SDK WOTC i dotychczasowej ścieżki SDK. Z katalogu projektu:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\build.ps1 -SdkPath '<katalog SDK WOTC>'
```

3. Podstaw właściwy katalog zamiast tekstu w nawiasach. Przy już przygotowanych
   pakietach bazowych pomiń `-BuildBase`; nie zmieniaj ponownie TLE/Day0 bez nowego błędu.
   Opcjonalne `-GamePath '<katalog XCom2-WarOfTheChosen>'` instaluje wynik do gry.
4. Wynik to `dist/AutoplayXCom2.zip`, świeży `Script/AutoplayXCom2.u` i log
   `.build/mod-make.log`. Zainstaluj wynik kompilacji i uruchom grę ponownie.
   Log startu ma wskazywać **`mission-report-v43`**. Zapisz liczbę błędów i ostrzeżeń;
   wcześniejsze poprawne make nie potwierdza kompilacji tej paczki.

## Jedna wspólna runda

Nie potrzeba osobnej kompilacji do każdego wiersza. Użyj dotychczasowej trudności
i zapisów, bez ręcznych rozkazów w próbach autonomii.

| Próba | Co sprawdzić i zachować w raporcie |
| --- | --- |
| GasStation / ludzka drużyna | Ruch i brak pętli, zasadzka/OW gdy wystąpi okazja, granaty/Faceoff przy legalnych celach, HUD i pewny wynik końcowy bieżącej misji. |
| SabotageCC | Autonomiczne podejście i zaakceptowane `Interact_PlantBomb`, bez ręcznego X4; native end, dostępna proweniencja punktów. Nie oczekiwać wymyślonych 5000 za cel z konfiguracją 0. |
| Blood Killer / SabotageTransmitter | Legalne ciosy MP/relay, timer/X4, Sweep, źródło MC i odzyskanie sojusznika, jeśli taki efekt rzeczywiście wystąpi; HP/straty i native outcome/final score. |
| Realna okazja medyczna w jednej z misji albo krótki istniejący zapis | Pilne niskie HP lub usuwalny poison poza chmurą: zaakceptowany ruch, następnie świeża legalna akcja leczenia i rzeczywista zmiana HP/statusu. Sam `medical_approach_candidate` nie potwierdza wykonania. |

Gdy skład nie ma medyka lub nie pojawi się odpowiednia okazja OW/Faceoff/drugiego
blue, oznacz **NOT EXERCISED**, nie PASS/FAIL. Nie trzeba sztucznie tworzyć wszystkich
przypadków testowych ani powtarzać pełnej misji dla każdego z nich. Ręczny test
diagnostyczny można opisać osobno; nie certyfikuje autonomicznego wyniku misji.

PASS projektu wymaga autonomicznego native victory oraz znanych końcowych
punktów bieżącej misji **>0**. Zero/ujemny wynik, dodatnie punkty przy LOSS lub
assisted WIN nie wystarczają. Przy `~...`/partial można potwierdzić funkcję,
ale nie pełny benchmark. Zgodna z Legacy punktacja moda może być oficjalna;
bieżące partial v3 i archiwalne v2 nie stają się pełnym wynikiem automatycznie.

## Raport po próbie

Zachowaj `.build/mod-make.log`, a ZIP misji zbierz **przed kolejnym uruchomieniem gry**.
W zainstalowanym `AutoplayXCom2/Diagnostics` uruchom:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Collect-MissionRecording.ps1
```

Kolektor poda ZIP w Dokumenty/AutoplayXCom2-Reports; niczego sam nie wysyła.
Przekaż go z trudnością, wynikiem, stratami i informacją o ręcznych działaniach.
Nie trzeba ponownie przesyłać SDK/configów. Pełne instrukcje:
[budowanie](../README.md#budowanie-na-windows), [raport](mission-recording.pl.md).
