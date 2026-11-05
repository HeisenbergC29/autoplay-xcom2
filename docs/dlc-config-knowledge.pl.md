# Uzupełnienie katalogu o konfiguracje dodatków z gry

Pięć nowych archiwów pochodzi z gry. Uzupełniają wcześniejszy katalog
o konfiguracje Alien Hunters, Shen’s Last Gift, Tactical Legacy Pack
oraz pozostałych przesłanych dodatków. Folder konfiguracji DLC w SDK
nie jest potrzebny.

Po uzupełnieniu katalog obejmuje 196 sekcji bazowych statystyk i 177
zestawów wyposażenia. Rozwiązano 684 odwołania parametrów broni:
682 z konfiguracji i 2 z domyślnych właściwości w źródłach. Pozostały
2 nierozwiązane odwołania opisane poniżej. Indeks AI obejmuje 28 jawnych
korzeni i 166 dopasowań według grupy postaci; razem 194 wpisy.

Aktualizacja dotyczy [katalogu jednostek](../data/unit-catalog.json)
i narzędzi jego odtwarzania. Kod działający w grze zachowuje rewizję
`mission-report-v14`; samo uzupełnienie katalogu nie wymaga ponownego
budowania już zainstalowanego v14. Skuteczność wcześniejszej zmiany Marked
nadal wymaga próby opisanej w [scenariuszach v14](config-knowledge-v14.pl.md).

## Otrzymane pliki i sposób łączenia

| Dodatek | Pliki INI | Bajty |
| --- | ---: | ---: |
| `DLC_1` | 3 | 100574 |
| `DLC_2` | 27 | 169823 |
| `DLC_3` | 26 | 110968 |
| `TLE` | 20 | 409790 |
| `XCom_DLC_Day0` | 3 | 5097 |
| Razem | 79 | 796252 |

Archiwa rozpakowano poza repozytorium po sprawdzeniu ścieżek i typów wpisów.
Pełne INI i źródła SDK pozostają prywatnymi wejściami; publikowane są
pochodne wartości, odwołania do pliku i linii oraz skróty kontrolne.

Pliki `XCom*.ini` z katalogów dodatków gry są konfiguracją tych dodatków.
Ich nazwa nie oznacza, że należy potraktować je jak wygenerowane ustawienia
SDK. Porównanie siedmiu głównych plików Default gry i SDK pozostaje osobne.

Audyt zapisuje jawną kolejność składania dostarczonego zestawu:
główne Default gry, `DLC_1`, `DLC_2`, `DLC_3`, `TLE`, `XCom_DLC_Day0`.
W tym zestawie `DLC_3` poprawia cztery węzły AI wprowadzone przez `DLC_2`,
dlatego ta zależność kolejności jest istotna. Pełna natywna kolejność
ładowania nie została potwierdzona: enumeracja i instalowanie konfiguracji
DLC są funkcjami natywnymi silnika.

Operatory `+`, `.`, `-` i `!` działają na uporządkowanych wpisach ze wszystkich
warstw, z zachowaniem pochodzenia. Usunięcie `-stary` musi móc usunąć wpis
poprzedniej warstwy przed dodaniem `+nowy`. W otrzymanych plikach nie wykryto
sprzecznych przypisań liczbowych `CharacterBaseStats` ani powielonych nazw
zestawów wyposażenia między warstwami. `DLC_1` i `XCom_DLC_Day0` zawierają
tylko rodziny Content, Engine i Game, poza siedmioma rodzinami tego audytu.

## Przykładowe uzupełnione wartości

Statystyki poniżej łączą bazową sekcję z częściowym wariantem `_Diff_3`.
Pochodzą z `DLC_2/Config/XComGameData_CharacterStats.ini`
lub odpowiedniego pliku w `DLC_3`.

| Szablon | HP | Celność | Mobilność | Pancerz |
| --- | ---: | ---: | ---: | ---: |
| `ViperKing` | 69 | 75 | 14 | 3 |
| `BerserkerQueen` | 100 | 75 | 14 | 4 |
| `ArchonKing` | 120 | 75 | 14 | 5 |
| `SparkSoldier` | 10 | 70 | 12 | 1 |
| `LostTowersSpark` | 10 | 65 | 12 | 1 |
| `Sectopod_Markov` | 100 | 65 | 16 | 7 |
| `FeralMEC_M1` | 4 | 65 | 14 | 3 |
| `ViperNeonate` | 2 | 60 | 17 | 0 |

Sekcje SPARK-a mają klasę `X2SparkCharacterTemplate_DLC_3`; wyszukiwanie
wyłącznie `X2CharacterTemplate` pomijałoby te dane. TLE definiuje osobno
`PsiZombieCivilian` oraz `NeonateChryssalid`: oba mają bazowo 4 HP,
celność 75, mobilność 12 i pancerz 0; neonate dodatkowo unik 10.

Parametry broni DLC obejmują między innymi bazowe obrażenia ViperKing 5,
ArchonKing 8 oraz SparkRifle CV/MG/BM odpowiednio 5/7/9. Są to wartości
konfiguracji przed spreadem, premiami i innymi zmianami. W grze pierwszeństwo
mają załadowany szablon, bieżące statystyki widocznego kontaktu oraz natywny
podgląd ataku.

Źródła opisują u władców reakcje na aktywację zdolności; przyznawanie punktu
reakcji uwzględnia między innymi Stunned i Freeze. Przerwanie King Bind
oraz Icarus Drop ma osobne parametry. Są to ustalenia do dalszego rozwijania
taktyki; to uzupełnienie katalogu nie dodaje nowego planera reakcji władców.

## Co pozostało nierozwiązane

Nowe konfiguracje zawierają 55 z 57 wcześniej nierozwiązanych pól broni DLC.
Dwa wpisy kategorii Medikit/NanoMedikit można rozwiązać z już posiadanych
źródeł: `MedikitCat="medikit"` w domyślnych właściwościach klasy.
Wymagało to rozszerzenia odczytu źródeł, a nie nowych plików użytkownika.

W otrzymanych konfiguracjach nadal nie znaleziono wartości:

- `FERALMEC_M2_PROXY_WPN_BASEDAMAGE`;
- `FERALMEC_M3_PROXY_WPN_BASEDAMAGE`.

Źródła deklarują te bronie i odwołania, lecz nie znaleziono ich przypisań
w konfiguracjach wyposażenia. Nie przypisujemy im obrażeń wariantu M1.
Nie ma podstaw do proszenia o kolejne archiwa wyłącznie z powodu tych dwóch
odwołań.

Brak własnej sekcji statystyk, zestawu wyposażenia lub przedmiotu zbroi
nie dowodzi braku danych o całej jednostce. Część wartości jest zapisana
w kodzie lub dziedziczona; katalog obejmuje również cywilów, mówców i aliasy.
Pancerz może być statystyką jednostki bez osobnego przedmiotu.

## Odtwarzanie katalogu

Opcję `--game-dlc NAZWA=KATALOG` można podać wielokrotnie, w jawnej kolejności
składania danych. Przykład dla lokalnie rozpakowanych wejść:

```powershell
python .\tools\audit-unit-definitions.py `
  --sdk 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK' `
  --game-config 'D:\pliki-do-audytu\gra\Config' `
  --sdk-config 'D:\pliki-do-audytu\sdk\Config' `
  --game-dlc 'DLC_1=D:\pliki-do-audytu\gra\DLC\DLC_1\Config' `
  --game-dlc 'DLC_2=D:\pliki-do-audytu\gra\DLC\DLC_2\Config' `
  --game-dlc 'DLC_3=D:\pliki-do-audytu\gra\DLC\DLC_3\Config' `
  --game-dlc 'TLE=D:\pliki-do-audytu\gra\DLC\TLE\Config' `
  --game-dlc 'XCom_DLC_Day0=D:\pliki-do-audytu\gra\DLC\XCom_DLC_Day0\Config' `
  --json '.\unit-catalog-dlc-local.json'
```

Wskaż nowy plik wynikowy; narzędzie zachowuje istniejące wyniki.
`--game-dlc` wymaga głównego `--game-config`. Konfiguracja SDK służy
porównaniu i nie nadpisuje danych gry ani dodatków.
