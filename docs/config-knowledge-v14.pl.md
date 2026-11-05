# Konfiguracje jednostek i oznaczenie celu — v14

V14 uzupełnia [katalog jednostek](../data/unit-catalog.json) o wartości
z przekazanych archiwów `Config.rar` (gra) i `Config sdk.rar` (SDK).
Pierwszą zmianą decyzji wynikającą z tej kontroli jest uwzględnienie aktywnego
Marked na własnym żołnierzu przy ocenie zagrożenia. Kompilacja Windows
i skuteczność tych decyzji w grze pozostają do sprawdzenia.

Późniejsze [uzupełnienie konfiguracji DLC](dlc-config-knowledge.pl.md)
korzysta z pięciu dodatkowych archiwów pochodzących z gry. Rozszerza katalog
i narzędzia analizy bez zmiany kodu działającego w grze ani rewizji v14.

## Zakres i pochodzenie danych

Archiwum gry zawiera 49 plików INI, a archiwum SDK 114: 98 w głównym
katalogu i 16 w podkatalogach. Siedem istotnych plików `Default` jest
bajtowo identycznych między grą i SDK:

- `DefaultGameData_CharacterStats.ini` — statystyki i warianty trudności;
- `DefaultGameData_WeaponData.ini` — liczbowe parametry broni;
- `DefaultGameData_SoldierSkills.ini` — parametry zdolności;
- `DefaultGameData.ini` — między innymi zestawy wyposażenia;
- `DefaultGameCore.ini` — efekty i inne reguły;
- `DefaultAI.ini` — definicje zachowań;
- `DefaultWeaponTuning.ini` — parametry dostrajania broni.

Katalog korzysta z przekazanych domyślnych plików gry. Domyślne pliki SDK
służą porównaniu; wygenerowane pliki `XCom*.ini` z SDK nie nadpisują danych
gry. To zapis dostarczonych plików, bez odtworzenia pełnej kolejności
ładowania konfiguracji, modyfikacji innych modów ani natywnych zmian silnika.
Załadowany szablon i bieżące statystyki widocznego kontaktu nadal są
rozstrzygające podczas gry.

Źródłowa część katalogu obejmuje 253 rejestracje i rozpoznane nazwy,
171 fabryk i 208 definicji broni w 196 plikach źródłowych. Zawiera również
żołnierzy, cywilów, jednostki MP i mówców: **253 nie oznacza 253 wrogów**.
Pola `config_values` dodają dane konfiguracji obok dotychczasowych faktów
ze źródeł, a `configuration_audit` zachowuje metadane porównania.
Nie publikujemy pełnych źródeł SDK ani surowych plików INI z archiwów.

Pierwotny katalog v14, bez konfiguracji DLC, uzupełnił 178 sekcji bazowych statystyk, 165 zestawów
wyposażenia i 627 odwołań do parametrów broni. Dalszych 59 odwołań broni
pozostawało nierozwiązanych. Ówczesny indeks AI obejmował 23 jawnie zadeklarowane
korzenie oraz 165 dopasowań według grupy postaci; te ostatnie są oznaczone
`indexed_by_convention` i nie dowodzą, że gra wykonała dane drzewo.
Aktualne uzupełnienie i pozostałe konkretne luki opisuje
[analiza konfiguracji DLC](dlc-config-knowledge.pl.md).

## Co wynika z konfiguracji

Wariant `_Diff_3` jest częściową zmianą bazowej sekcji jednostki. Należy
połączyć oba zestawy pól; brak wpisu w wariancie nie zeruje wartości bazowej.
Dla przekazanych plików daje to następujące przykłady na Legendzie:

| Szablon | HP | Celność | Mobilność | Wybrane dodatkowe dane |
| --- | ---: | ---: | ---: | --- |
| `AdvTrooperM1` | 4 | 65 | 12 | zestaw z karabinem |
| `AdvCaptainM1` | 7 | 75 | 12 | karabin i `AdventCaptainMk1Grenade` |
| `Sectoid` | 10 | 75 | 12 | psionika 90, wola 100 |
| `PsiZombie` | 8 | 75 | 15 | broń `PsiZombie_MeleeAttack` |
| `Faceless` | 12 | 75 | 14 | odrębny typ ataku wręcz |
| `Viper` | 10 | 75 | 15 | unik 33; karabin, trucizna i język |

Statystyki pochodzą z sekcji o nazwie jednostki i jej wariantu w
`DefaultGameData_CharacterStats.ini`; zestawy z `DefaultGameData.ini`.
Mobilność jest wartością statystyki gry, a nie gwarantowanym zasięgiem
przyszłego ruchu po rzeczywistej mapie.

Broń przypisana zombie ma bazowe `Damage=4`, `Spread=1`, `PlusOne=0`
(`DefaultGameData_WeaponData.ini:574`). Sam podobny symbol konfiguracji
nie dowodzi, że jest używany przez jego wyposażenie. Planer nadal odczytuje
rzeczywistą broń załadowaną na widocznym przeciwniku.

`DefaultGameData_SoldierSkills.ini:413` ustawia `BIND_FRAGILE_AMOUNT=1`.
Źródła zdolności wiążą tę wartość z przerwaniem Bind po odpowiednich
obrażeniach; zabicie Vipera nie jest jedyną możliwością uwolnienia celu.
V14 dokumentuje to ustalenie, ale nie dodaje osobnego planera przerywania
Bind. Podatność sektoida na melee jest już uwzględniana w natywnym podglądzie
obrażeń; nie należy dodawać jej ponownie do wyniku tego podglądu.

Drzewo AI opisuje warunki i kolejność prób, a nie pewną następną akcję.
Przykładowo sektoid może preferować strzał z flanki przed zdolnością psi;
`Mindspin` może spowodować panikę zamiast przejęcia kontroli. Samo istnienie
granatu w wyposażeniu kapitana nie dowodzi, że użyje go przy każdej okazji.
Katalog nie odczytuje ukrytego zamiaru, aktualnych AP, amunicji ani cooldownów.

## Zmiana oceny ryzyka

`DefaultGameCore.ini:1852` definiuje sekcję `XComGame.X2Effect_Marked`:
premia celności wynosi 10, premia szansy krytycznej i obrażeń krytycznych 0.
Nie należy przypisywać oznaczeniu premii z sąsiedniej sekcji innego efektu.

`APX_EnemyKnowledge.KnownMarkedAimBonus` sprawdza jawny efekt Marked na
własnej jednostce i odczytuje wartość z załadowanej klasy `X2Effect_Marked`.
Wspólne ryzyko pola jest mnożone przez ograniczoną wagę
`1 + clamp(bonus, 0, 50) / 100`: dla przekazanych ustawień jest to 1,10,
bez oznaczenia 1,00. Obejmuje ryzyko od wszystkich widocznych kontaktów,
także innych niż kapitan, oraz obie gałęzie modelu: strzelecką i melee.
To heurystyka planera, a nie dokładna szansa trafienia lub obietnica
dziesięcioprocentowego wzrostu otrzymanych obrażeń.

Ta sama funkcja ryzyka jest używana przy ruchu i ocenie obrony.
`move_threat_preview` zapisuje `marked_aim_bonus` i `target_status_weight`
obok ocen bieżącego i proponowanego pola. Wraca do 1 po wygaśnięciu efektu;
nie jest trwałą cechą żołnierza ani dodatkową karą punktową.
Reguły punktacji `wotc_legacy_observed_v2` pozostają bez zmian i zaczynają
ocenę porównawczą od zera.

## Braki i odtwarzanie

Brak sekcji lub pola pozostaje brakiem danych, a nie wartością zero.
Pancerz może być statystyką jednostki bez osobnego przedmiotu zbroi.
W samych głównych plikach nie ma między innymi sekcji statystyk
`ViperKing`, `BerserkerQueen`, `ArchonKing` i `SparkSoldier`.
Te dane zostały później otrzymane w konfiguracjach dodatków z gry
i są uwzględniane przez [rozszerzenie audytu DLC](dlc-config-knowledge.pl.md).
Brak własnej sekcji INI nie oznacza również, że cały szablon nie ma znanych
statystyk: katalog zachowuje osobno jawne przypisania ze źródeł.

Poniższe polecenie odtwarza zakres głównych konfiguracji z Pythonem 3,
wskazując nowy plik wynikowy i katalogi zawierające pliki `Default*.ini`.
Pełny aktualny katalog wymaga również opcji `--game-dlc` z
[instrukcji uzupełnienia DLC](dlc-config-knowledge.pl.md).

```powershell
python .\tools\audit-unit-definitions.py `
  --sdk 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK' `
  --game-config 'D:\pliki-do-audytu\gra\Config' `
  --sdk-config 'D:\pliki-do-audytu\sdk\Config' `
  --json '.\unit-catalog-config-local.json'
```

Bez `--game-config` narzędzie nadal tworzy katalog samych źródeł.
`--sdk-config` wymaga `--game-config`; dane SDK nie są traktowane jako
poprawki konfiguracji gry. Parser zachowuje kolejność powtarzanych wpisów,
operatory tablic INI i odwołania do pochodzenia wartości.

Do następnej próby zbuduj i zainstaluj v14. W raporcie sprawdź
`revision=mission-report-v14`, aktywne Marked z innym strzelcem w polu
widzenia oraz wygaśnięcie efektu. Dla dostarczonych ustawień oczekiwane są
wartości 10/1,10 podczas oznaczenia i 0/1,00 po nim. Porównaj decyzje
ruchu, obrony i rzeczywiste skutki przy podobnej geometrii.
[Przebieg i zbieranie raportu](legacy-test.pl.md) ·
[Lista prób](TESTING.pl.md) · [Mechaniki zachowane z v13](enemy-knowledge-v13.pl.md).
