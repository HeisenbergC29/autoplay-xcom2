# Sprawdzenie źródeł SDK — 31.10.2026

Przeanalizowano przesłane przez użytkownika archiwum `SrcOrig.rar` (7 661 577 bajtów):

```text
SHA-256: 8c298bd0dab3382c931f7cfb2500175da3d586d4b81d3e18f0548b4b3bcbb83e
```

Archiwum zawiera 4137 plików `.uc` i 7 plików `.uci`, w tym pakiety `XComGame`, `DLC_1`, `DLC_2`, `DLC_3` i `TLE`. Obecność klas Reapera, Templariusza, Skirmishera i Wybranych potwierdza źródła WOTC. Na podstawie samego archiwum nie przypisujemy konkretnego numeru wersji binarnej gry.

Źródła rozpakowano poza repozytorium. Nie są publikowane na GitHub i nie wchodzą do paczki moda.

## Wynik ręcznej kontroli

Sprawdzono deklaracje używanych funkcji i pól w rzeczywistym SDK: pamięć dostępnych akcji, aktywacja zdolności, własność jednostek, gotowość zasad i wizualizacji, ścieżki i osiągalne pola, widoczność, obrażenia, cele interaktywne, strefa ewakuacji, ekran hakowania, przyciski i zdarzenia UI.

Poprawki wynikające z kontroli:

- Usunięto cztery nieistniejące aliasy umiejętności: `PistolStandardShot_Secondary`, `SparkStandardShot`, `SparkReload`, `SparkOverwatch`. SPARK korzysta z `StandardShot`, `Reload`, `Overwatch`, co potwierdzają źródła broni DLC_3.
- Nokaut ograniczono do jednostki `HostileVIPCivilian`, aby nie próbować obezwładniać dowolnego cywila oznaczonego jako cel.
- Wrogi cel bojowy nie jest traktowany jak VIP wymagający podejścia z bliska.
- Kontroler respektuje `XComTacticalController.IsBusy()`, również dla modalnych komunikatów prezentacji niebędących osobnym ekranem na stosie.
- Wyłączenie i ponowne włączenie w trakcie własnego hakowania zachowuje dokładny kontekst rozpoczętej akcji. Tożsamość kontekstu chroni przed przejęciem późniejszego ręcznego hacka tą samą zdolnością.

Nowe planery eksploracji, zwykłych granatów wybuchowych i wyznaczania ewakuacji korzystają z interfejsów sprawdzonych w tym SDK. Każdy nadal wymaga prób w działającej grze.

## Powtarzalna kontrola odwołań

Opcjonalnie, z Pythonem 3:

```powershell
python .\tools\check-sdk-references.py --sdk 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK'
```

Narzędzie sprawdza obecność dosłownych odwołań do klas, skonfigurowanych nazw umiejętności oraz znaczników WOTC. Nie sprawdza sygnatur metod ani zasad natywnych i nie zastępuje kompilatora.

## Co pozostaje wymagane

Archiwum zawiera źródła, bez kompilatora i silnika. W lokalnym środowisku nie uruchomiono kompilatora ani gry. Testy PowerShell dotyczą rzeczywistych operacji plikowych narzędzi, a nie zachowania gry.

Następny krok na Windows: pobrać aktualne repozytorium i wykonać `tools\build.ps1` z poprawną ścieżką SDK. Log `.build\mod-make.log` pozwoli naprawić błędy, których ręczne sprawdzenie źródeł nie wykrywa. Następnie konieczna jest lista prób z `TESTING.pl.md`.

## Otrzymane logi pierwszej próby budowania

`base-make.log` zakończył się `Success - 0 error(s), 1739 warning(s)`: przygotowanie bazowych pakietów SDK powiodło się. Ostrzeżenia dotyczą między innymi zasobów edytora i DLC; nie zatrzymały tej kompilacji.

`mod-make.log` zakończył się `Failure - 1 error(s), 8 warning(s)`. Pierwszy błąd w `APX_MissionPlanner.uc` brzmiał `Booleans may not be out parameters`. Wszystkie trzy bezpośrednie parametry wyjściowe typu `bool` w dwóch funkcjach zastąpiono jedną strukturą `MissionGoal`; jej pola logiczne zachowują dotychczasowy wybór celu. To ograniczenie języka dodano również do narzędzia kontroli oraz czterech testów regresji.

Po tej poprawce zalecono ponowienie kompilacji moda **bez `-BuildBase`**, wykorzystując już zbudowane pakiety bazowe. Na tym etapie sukces nie był jeszcze potwierdzony.

## Druga próba — 01.11.2026

Kolejny przesłany `mod-make.log` nie zgłasza poprzedniego problemu parametrów. Kompilacja zatrzymała się na trzech niekwalifikowanych wywołaniach `Stop(...)` w `APX_Controller.uc`, z komunikatem `'Stop' is not allowed here`.

UnrealScript interpretuje taki zapis w treści funkcji jako specjalne polecenie `Stop` używane w stanach. Nie oznacza to zakazu natywnych metod `Stop` w SDK: kwalifikowane wywołania, takie jak `Audio.Stop()`, są prawidłowe. Nazwę własnej metody zmieniono na `StopAutoplay`, zarówno w kontrolerze, jak i panelu UI, i dodano cztery testy dla tego przypadku. Łącznie osiem testów preflight przechodzi; nie zastępują kompilatora ani testów w grze.

Do kolejnej próby trzeba zaktualizować oba pliki: `APX_Controller.uc` oraz `APX_UITacticalControl.uc`. Poprawiony wcześniej `APX_MissionPlanner.uc` również musi pozostać aktualny. Bazowych pakietów SDK nie trzeba przebudowywać.

## Trzecia próba — kompilacja zakończona, konfiguracja do poprawy

Następny `mod-make.log` potwierdza zapis `AutoplayXCom2.u` i wynik `Success - 0 error(s), 67 warning(s)`. Najnowszy log bazy ma `Success - 0 error(s), 8 warning(s)`.

67 unikalnych ostrzeżeń moda składa się z:

- 8 ostrzeżeń dotyczących zasobów narracji, materiałów i modeli SDK/DLC oraz starego katalogu `XCom_DLC_Day0`. Pakowanie rozprowadza tylko własny `.u`, nie przebudowane biblioteki SDK.
- 59 ostrzeżeń `Import failed ... property is config` w naszych klasach: Combat 29, Controller 9, Exploration 8, UI 6, Area 3, Mission 2, Evac 1, DLCInfo 1.

Druga grupa ma znaczenie funkcjonalne. Kompilator pomija przypisania pól `config` w `defaultproperties`. Dotychczas listy umiejętności istniały tylko w odrzucanych przypisaniach, więc planer mógł mieć puste listy ataków, leczenia, przeładowania i overwatch.

Poprawka usuwa wszystkie takie przypisania z kodu. Wartości liczbowe i wszystkie 27 nazw umiejętności znajdują się w `XComAutoplayXCom2.ini`; dziedziczony `DLCIdentifier` jest w `XComGame.ini`, zgodnie z bazową klasą `config(Game)`. Pozostałe właściwości aktorów i UI zostają w `defaultproperties`, ponieważ nie są polami konfiguracji.

Kontrola sprawdza obecność wartości dla każdego zadeklarowanego pola `config`, zachowanie list oraz odrzucane przypisania, również dziedziczone z SDK. Poprawka wymaga ponownej kompilacji. Nie potwierdzono jeszcze odczytu konfiguracji ani działania autoplaya w grze.

## Czwarta próba — kompilacja po migracji konfiguracji potwierdzona

Kolejne logi otrzymane 01.11.2026 potwierdzają wynik `Success - 0 error(s), 8 warning(s)` zarówno dla bazowych bibliotek, jak i kompilacji moda. `mod-make.log` zawiera jawny zapis pakietu `AutoplayXCom2.u`.

Wszystkie pozostałe ostrzeżenia dotyczą bibliotek SDK/DLC: jednego starego katalogu źródeł i siedmiu odwołań do zasobów narracji/modeli. Nie ma ostrzeżeń dla klas `AutoplayXCom2` ani `property is config`. Poprzednie 59 odrzuconych ustawień zniknęło.

To potwierdzenie kompilacji kodu, nie wykonania dalszych kroków skryptu pakującego. Do sprawdzenia pozostają zawartość `dist/AutoplayXCom2.zip`, odczyt konfiguracji przez uruchomioną grę oraz próby misji z `TESTING.pl.md`. Nie ma potrzeby ponownego budowania tylko z powodu tych ośmiu znanych ostrzeżeń bibliotek SDK.

## Otrzymana i sprawdzona paczka instalacyjna

Następnie otrzymano `AutoplayXCom2.zip` o rozmiarze 66 360 bajtów. CRC archiwum jest poprawne. Jest jeden katalog `AutoplayXCom2`, własny `.u`, trzy pliki konfiguracji, manifest `RequiresXPACK=true`, obie lokalizacje w UTF-16LE z BOM, instrukcja oraz znacznik narzędzia budowania. Konfiguracja, manifest i teksty odpowiadają źródłom repozytorium; listy zawierają wszystkie 27 zdolności.

Statyczna kontrola `.u` potwierdziła 786 nazw, 464 importy i 773 eksporty, spójne zakresy tabel oraz dziewięć klas moda z oryginalnymi klasami bazowymi. Importy prowadzą wyłącznie do `Core`, `Engine`, `XComGame`; nie stwierdzono zależności od innych modów. Wszystkie importowane klasy są w przesłanym oryginalnym SDK lub należą do standardowych typów Core.

Na tej podstawie przygotowano paczkę `release/AutoplayXCom2-WOTC-0.1.0-alpha.zip`. Zachowuje ona identyczny `.u`, konfigurację i napisy; zawiera uaktualnioną instrukcję oraz `BUILD-INFO.json`. [Profil zgodności i granice tego potwierdzenia](COMPATIBILITY.pl.md).

Można powtórzyć kontrolę bez uruchamiania gry:

```powershell
python .\tools\check-compiled-package.py .\release\AutoplayXCom2-WOTC-0.1.0-alpha.zip
```

Ta kontrola oraz 14 testów parsera dotyczą struktury pliku, ścieżek ZIP, zależności i spójności hashy, nie wykonywania bytecode. Sprawdzenie paczki **nie potwierdza konkretnego numeru builda Steam, uruchomienia moda ani wykonania misji**. Następny etap to próba na docelowym czystym WOTC użytkownika.

## Uzupełnienie SDK w nowym środowisku — 02.11.2026

Po odtworzeniu commitu `ed74176` i przygotowaniu `mission-report-v6` otrzymano
`Development.rar` (15 468 196 bajtów), SHA-256:

```text
04ad9ed9c7296dd04f390c67e5dec5dfa89337800af1d3cc1915d9890ad6fb43
```

Archiwum rozpakowano poza repozytorium, po sprawdzeniu ścieżek i typów wpisów.
`SrcOrig` zawiera 4144 pliki źródłowe SDK. Wszystkie odpowiadające im pliki
w `Src` są bajtowo identyczne. Dodatkowe pliki w `Src` to znacznik narzędzia
budowania i 11 klas AutoplayXCom2; wszystkie te klasy odpowiadają commitowi
`ed74176`, a rejestrator deklaruje `mission-report-v5`. Potwierdza to wersję
źródeł pozostawionych w SDK przy poprzednim budowaniu.

Kontrola bieżących źródeł v6 z `APX_SDK_SOURCE_ROOT` wskazującym przesłany
`Development/SrcOrig` zakończyła się wynikiem **176 testów Python zaliczonych,
0 pominiętych**. Wcześniejsze 7 pominięć z braku SDK zostało usunięte.
`check-sdk-references.py` potwierdził 11 klas moda, obecność odwołań do klas
SDK, 29 skonfigurowanych nazw zdolności i znaczniki WOTC, bez zgłoszonych
niezgodności. Wszystkie trzy zestawy PowerShell przeszły wcześniej dla v6.

Ręcznie sprawdzono sygnatury `GetCoverTypeForTarget`, `CanSeeTileToTile`
i deklarację `GameRulesCache_VisibilityInfo` używane przez wspólną funkcję
ryzyka v6. Argumenty i istniejące zależności klas są zgodne. Źródła potwierdzają
także klasyfikację Faceless jako jednostki walczącej wyłącznie wręcz;
nie ma podstaw do dodawania wyjątku zastępującego tę klasyfikację.

Do tej weryfikacji nie brakuje kolejnych źródeł SDK. Pliki SDK pozostają
poza repozytorium i paczką moda. Kompilacja Windows i próba v6 w grze nadal
wymagają uruchomienia na komputerze z SDK WOTC i grą.

## Weryfikacja mission-report-v7 po drugim raporcie Legacy

Nowa próba v6 potwierdziła wydawanie poleceń i rejestrację danych w grze,
lecz zakończyła się porażką. Poprawki v7 obejmują bezpieczny ruch do ataku
wręcz i wycenę utraconego ataku przy wydawaniu AP na ruch.

Z przesłanym `Development/SrcOrig` zaliczono **189 testów Python, bez
pominięć** oraz kontrolę odwołań (11 klas moda, 29 nazw zdolności).
Sprawdzono źródłowy kontrakt `X2AbilityCost_ActionPoints`: `GetPointCost`,
`ConsumeAllPoints`, typy dopuszczanych AP, kolejność ich zużywania i znaczenie
`bFreeCost`. Projekcja zmienia tylko lokalną kopię AP. Ruch w niebieskim
zasięgu korzysta ze zwykłego kosztu ruchu; nie modelujemy nowego LOS,
reakcji przeciwnika ani wyniku kolejnych rzutów.

Kompilacja Windows i wynik v7 w grze pozostają do potwierdzenia.

## Weryfikacja v8 — 03.11.2026

Po trzeciej próbie Legacy i sugestiach taktycznych zaliczono **218 testów
Python bez pominięć**, korzystając z przesłanego `Development/SrcOrig`.
Kontrola odwołań potwierdza nadal 11 klas moda i 29 skonfigurowanych zdolności.
Wszystkie trzy zestawy PowerShell również przeszły: narzędzia budowania,
zbieranie źródeł SDK i zbieranie raportu misji.

Sprawdzono źródłowe kontrakty: usunięcie `X2Effect_MindControl` po śmierci
źródła i przywracanie właściciela, `SireZombieLink`/`KillSiredZombies`, mobilność
i jednostki zasięgu `MovingMelee`/`Cone`, a także typy i właściwości używane
przy diagnostyce blokera granatu. Przywrócenie kontroli zeruje stare AP,
a świeże przyznaje warunkowo, gdy trwa tura przywróconego właściciela.
Planer nie zakłada dodatkowego natychmiastowego ataku.

Lokalna tablica zasięgów wręcz powstaje przed pętlą kandydatów ruchu.
Opcjonalne `const out array<float>` i ujemny domyślny parametr liczbowy mają
odpowiedniki w składni SDK. Nie dodano wspólnych struktur klas APX ani nowych
zależności `DependsOn` między nimi.

Źródła SDK pozostają poza repozytorium. Kompilacja Windows i wynik v8 w grze
pozostają do potwierdzenia; testy kontraktów nie uruchamiają silnika gry.

## Potwierdzenie próby v8 i punktacja Legacy — 03.11.2026

Raport `AutoplayXCom2-20261103-002926-7428f88e.zip` potwierdza uruchomienie
`mission-report-v8` i zwycięstwo w `ChallengeAbductionGasStation` na Dowódcy,
w turze 14. To potwierdzenie tej konkretnej misji, bez pełnego logu budowania
i bez potwierdzenia całej drabinki. Dalsze szczegóły zawiera
[raport zwycięstwa](report-2026-11-03-legacy-v8-win.pl.md).

Odczytano także kod `XComGameState_LadderProgress`: wynik `CumulativeScore`
przechodzi do następnego etapu; progi medali są sprawdzane po końcu całej
drabinki. Pierwsze obrażenia odbierają premię za brak ran, a leczenie jej nie
przywraca. Utrata lub odpowiednie wyłączenie żołnierza odbiera premię przeżycia.
Punkty obejmują osobne reguły celów, przeciwników, ich pochodzenia i tur.

W zwycięskim logu są startowe pule i reguły, ale brak oficjalnego zdobytego
wyniku i medalu. Recorder v8 nie odczytuje tych wartości; nie rekonstruujemy
ich z końcowego HP ani pól `score` decyzji. To doprecyzowanie dokumentacji
nie zmienia kodu ani parametrów v8 i nie wymaga ponownej kompilacji.

## Zmiany v9 — ratunek, łup i reguły punktacji

Nowe źródła `mission-report-v9` wymagają kompilacji Windows i osobnej próby
w grze. Testy źródeł, scenariuszy oraz kontraktów korzystają z tego samego
prywatnego `Development/SrcOrig`; SDK nie jest dołączane do repozytorium.

Sprawdzane kontrakty ratunku obejmują `MedikitStabilize`/`GremlinStabilize`,
natywne warunki i koszt zdolności, `GetHitRange`, projekcję pozostałych AP
oraz `GetBleedingOutTurnsRemaining`. Efekt wykrwawiania wygasa na początku
tury jego właściciela, więc przy jednej pozostałej turze nie wystarcza
częściowe podejście. Sam zasięg z proponowanego pola nie dowodzi dostępności
celu; właściwa aktywacja nadal wymaga natywnego `AA_Success` po ruchu.

`Loot` jest neutralną darmową zdolnością z `X2AbilityTarget_Single`
i `X2AbilityMultiTarget_Loot`. Natywny builder pobiera przedmioty, a
`UnitMoveFinished` może wyzwolić automatyczny pickup po odświeżeniu celów.
Planer nie modyfikuje ekwipunku ani stanu pozycji podczas oceny. Zasięg łupu
jest ścisły (`Distance < LootableRange`), a LOS i dostępność nadal weryfikuje gra.

Punktacja korzysta z publicznego `XComGameState_LadderProgress.CumulativeScore`,
rewizji `XComGameState_ChallengeScore`, zdarzeń jawnej listy celów i ratunku
cywilów. SDK potwierdza utratę premii za brak ran tylko przy pierwszej ranie
oraz osobną premię przeżycia. Parametry wspólnego profilu pochodzą z tabel
`XCom_Challenge` w prawdziwym logu GasStation/Cemetery i jawnych wartości
domyślnych struktur SDK dla pozostałych typów przeciwnika. Plik
`tools/legacy-score-rules.json` zapisuje źródła i przyjęte konwencje.

V9 odczytuje też faktyczne parametry Legacy przez natywne, odczytujące
`XComChallengeModeManager.GetSoldierScoring`, `GetTimeScoring`, `GetEnemyScoring`
i `GetObjectiveScoring`. Wywołania dotyczą bieżącej drabinki i etapu;
reguły typów wrogów pochodzą tylko z widocznych podglądów, a cele z jawnych
zaliczeń. Nie są wywoływane funkcje `Add*` przyznające punkty. Uruchomienie
rejestracji F8 nie jest dowodem kompletności obserwacji misji.

Funkcje przyznawania punktów za zabicia, cele i koniec misji są natywne;
otrzymane `.uc` nie ujawniają ich pełnego algorytmu. Dlatego wynik porównawczy
stosowany do wszystkich misji jest opisanym profilem, nie odtworzeniem
oficjalnej punktacji co do punktu. Braki danych pozostają jawne.
[Szczegóły v9](tactics-v9.pl.md).

Kontrola końcowa v9: **280 testów Python zaliczonych bez pominięć** z ustawionym
`APX_SDK_SOURCE_ROOT`, audyt 11 klas i 29 nazw zdolności oraz trzy zestawy testów
PowerShell: budowania, zbierania źródeł SDK i raportów misji. Sprawdzono też
odnośniki dokumentacji i `git diff --check`. To nie zastępuje kompilacji Windows
ani próby v9 w grze.


## V10 — natywny licznik wyniku misji

`APX_MissionScore` jest obiektem odczytującym dane dla HUD-u. W Legacy bierze
różnicę `CumulativeScore` względem tego samego obiektu Ladder w taktycznym
start state (`FindStartStateIndex` i `GetGameStateForObjectID`). Sprawdza
zgodność misji, drabinki i etapu. Baseline nie pochodzi z chwili włączenia
F8 ani utworzenia HUD-u, więc może zachować punkty po wczytaniu zapisu.

Maksimum Legacy pochodzi z `GetChallengeMaxPossibleScoreTable`, tego samego
odczytu, którego używa `UILadderModeScoringDialog`. Jest buforowane dla misji.
W natywnym Challenge Mode wymagany jest `XComGameState_ChallengeData`; licznik
używa pary `GetTotalScore` / `GetMaxChallengeScore`, tak jak podsumowanie gry.
Bez natywnej punktacji lub dostępnego odczytu wyświetla „—”.
Nie przyznaje punktów, nie zmienia stanów gry i nie przekazuje danych do planera.

UI odczytuje publiczne `UIButton.FontSize` i odświeża się co 0,25 s także przy
wyłączonym autoplay. Nowe pole ma wyłączone przechwytywanie myszy i nawigację.
Rozszerzenie wymaga nowej kompilacji Windows oraz próby HUD-u w grze.
Raport v9 potwierdził natywny ujemny wynik i stabilizację, nie działanie
nowego licznika. [Zakres i próba v10](score-display-v10.pl.md).

Kontrola końcowa v10: **299 testów Python zaliczonych bez pominięć** z SDK,
audyt 12 klas i 29 nazw zdolności oraz trzy zestawy testów PowerShell
(budowanie, zbieranie źródeł SDK i raportów misji). Odnośniki dokumentacji
i `git diff --check` są poprawne. Nie przeprowadzono kompilacji Windows
ani testu nowego licznika w grze.

## V11 — wynik natywny i porównawczy na HUD-zie

Znany natywny wynik przy niedostępnym maksimum daje `aktualne/—`; nieznane
maksimum jest nadal odczytywane ponownie. Brak pewnego bieżącego odczytu
Legacy lub Challenge Mode nie jest zastępowany fikcyjnym zerem.

Po nowym wyborze użytkownika w niepunktowanych misjach HUD v11 pokazuje
`~wartość/—`, według tego samego profilu `wotc_legacy_observed_v1` co analizator.
Początkowe premie wynoszą 6000 za każdego obserwowanego kwalifikowanego
żołnierza. To częściowa ocena porównawcza, nie natywne zdobyte punkty;
czterech żołnierzy daje `~24000/—` przed ranami i stratami.

Obserwator odczytuje własne jednostki oraz historycznie widoczne fakty o wrogach.
Zabicie wymaga potwierdzenia; zniknięcie z widoku i samo HP równe zero nie
wystarczają. Nasłuchuje jawnych zaliczeń celów i ratunku cywilów. Zdarzenia
sprzed utworzenia HUD-u lub wczytania zapisu mogą być nieobserwowane, dlatego
ocena zawsze ma tyldę i nie obiecuje pełnego wyniku. Historia jest przeglądana
porcjami; nasłuchy są usuwane przy usunięciu HUD-u lub zmianie trybu.
Działanie nie zależy od F8. Nie ma wywołań przyznających punkty ani zmian gry.

Audyt kierunku osłony potwierdził `GetCoverTypeForTarget` od pozycji każdego
widocznego przeciwnika do rozważanego pola. Eksploracja bez widocznych wrogów
ocenia osłonę względem celu marszu; nie przewiduje ukrytych pozycji. V11 nie
zmienia tej taktycznej oceny.

Kompilacja Windows oraz próba nowego licznika w grze pozostają do wykonania.
[Zasady i scenariusze v11](score-display-v10.pl.md).

Kontrola końcowa v11: **315 testów Python zaliczonych bez pominięć** z SDK,
audyt 13 klas i 29 nazw zdolności oraz testy PowerShell budowania. Sprawdzono
zgodność wag licznika z profilem raportów, odnośniki dokumentacji i
`git diff --check`. Zapis `hud_score` zachowuje dokładny tekst licznika,
bez uruchamiania rejestratora ani wydawania rozkazów. Kompilacja Windows
i próba nowego licznika w grze pozostają do wykonania.

## V12 — usunięcie niepopartej bazy początkowej

Początkowe 6000 punktów na żołnierza było konwencją naszego profilu v1,
a nie odczytaną premią startową Legacy. W tabelach `SoldierScoring` wartości
1000 i 5000 tworzyły składowe maksymalnej puli. `UILadderModeScoringDialog`
pokazuje je jako ujemne kary; `XComGameState_LadderProgress.OnUnitDamage`
i `OnUnitKilled` odejmują je przy ranie i stracie. Zaobserwowane natywne
`game_score` na początku Legacy wynosi 0.

V12 zaczyna ocenę porównawczą od zera w HUD-zie i domyślnym analizatorze.
Pierwsza rana odejmuje 1000, potwierdzona strata 5000; każda kara występuje
najwyżej raz na kwalifikowaną obserwowaną jednostkę. Wagi zabicia, celu
i cywila nie zmieniają się. Nie są zakładane również nieobserwowane premie
końcowe: pełna implementacja `AddTacticalGameEnd` pozostaje natywna.
Natywne odczyty Legacy i Challenge Mode nie zostały zmienione.

Nowy domyślny profil to `wotc_legacy_observed_v2` w
`tools/legacy-score-rules.json`. Archiwalny v1 zachowano w
`tools/legacy-score-rules-v1.json`; wyniki obu baz wymagają przeliczenia
przed porównaniem. Historyczna telemetria v11 zachowuje swój oryginalny tekst.
[Korekta i scenariusze v12](score-display-v10.pl.md) ·
[Raport v11](report-2026-11-03-v11-score.pl.md).

Kompilacja Windows oraz próba korekty licznika w grze pozostają do wykonania.

Kontrola końcowa v12: **320 testów Python zaliczonych bez pominięć** z SDK,
audyt 13 klas i 29 nazw zdolności oraz poprawne odnośniki dokumentacji
i `git diff --check`. Na nowym raporcie odtworzono v1 subtotal 1400 oraz
v2 subtotal −22600; natywny odczyt Legacy pozostał bez zmian. Wersja profilu
jest teraz zapisywana przy porównawczych odczytach `hud_score`.
Kompilacja Windows i próba v12 w grze pozostają do wykonania.

## V13 — źródła jednostek i ocena zagrożenia

`APX_EnemyKnowledge` korzysta z załadowanego szablonu podstawowej broni
widocznego wroga. Średnia uwzględnia `BaseDamage.Damage` oraz `PlusOne/100`;
`PlusOne` jest szansą procentową na dodatkowy punkt, a nie płaskim dodatkiem.
Ograniczona waga broni i celności jest wspólna dla ekspozycji i priorytetu
zabicia. Efekty kontroli, obszarowe style celu i wsparcie wpływają na priorytet
celu. Nie ustalają faktycznej gotowości zdolności.

SDK potwierdza kontratak przeciw `StandardAim.bMeleeAttack`, również przy
inaczej gwarantowanym trafieniu. Planer rozpoznaje zainstalowaną zdolność
kontry i jawne `IsImpaired`, bez odczytu ukrytego limitu użycia. Zwykłe
`StandardMelee` ma styl `X2AbilityTarget_Single` z ograniczeniem do broni;
`GetHitRange` zwraca jednostki świata. Nie zakłada się `iRange=0`: broń zombie
ma w źródłach `iRange=2`. Dwa standardowe AP pozwalają na ruch i potem cios.

Katalog `data/unit-catalog.json` zawiera metadane źródeł bazowych, WOTC
i oficjalnych dodatków oraz odwołania do definicji. Obejmuje też żołnierzy,
cywilów, jednostki MP i mówców; liczba rejestracji nie jest liczbą wrogów.
Narzędzie nie wykonuje natywnych modyfikacji ani losowania wariantów.
Plików INI z pełnymi statystykami i ekwipunkiem nie było w przekazanym SDK;
wartości nierozwiązane pozostają jawne. W grze używane są załadowane parametry
broni zaobserwowanego kontaktu. Pełne SDK i logi pozostają poza repozytorium.

Przygotowanie zasadzki otrzymało ograniczenie wzrostu ryzyka po ujawnieniu.
Budżet 6 jednostek heurystyki lub 25% bieżącego ryzyka jest wyborem planera,
nie parametrem gry. Wagi kontaktów są obliczane raz na wyszukiwanie pól.
Kompilacja Windows oraz skuteczność nowych decyzji wymagają próby w grze.
[Mechaniki, katalog i scenariusze v13](enemy-knowledge-v13.pl.md).

Kontrola końcowa v13: **353 testy Python zaliczone bez pominięć** z SDK,
audyt 14 klas i 29 nazw zdolności oraz testy PowerShell budowania i zbierania
raportu. Katalog 253 rejestracji, 171 fabryk i 208 definicji broni jest
odtwarzalny z tych samych 196 plików źródeł. Rozpoznano wszystkie 253 nazwy
oraz dziesięć szablonów obserwowanych dotąd w raportach. Sprawdzono
odnośniki dokumentacji i `git diff --check`. Nie przeprowadzono kompilacji
Windows ani próby v13 w grze.

## V14 — otrzymane konfiguracje gry i SDK

Archiwa `Config.rar` i `Config sdk.rar` rozpakowano poza repozytorium,
po kontroli ścieżek i typów wpisów. Pierwsze zawiera 49 plików INI;
drugie 114, w tym 98 bezpośrednio w katalogu głównym i 16 w podkatalogach.
Siedem plików `Default` dotyczących statystyk, broni, zdolności, loadoutów,
efektów i AI jest bajtowo identycznych. Katalog korzysta z domyślnych
plików gry, z porównaniem do SDK. Wygenerowane pliki `XCom*.ini` SDK
nie nadpisują tego zestawu.

Źródłowe fakty katalogu zachowano i uzupełniono o oddzielne `config_values`
oraz `configuration_audit`. Warianty `_Diff_0`–`_Diff_3` dziedziczą bazowe
statystyki i zmieniają tylko zadeklarowane pola. Brak sekcji nie daje
fikcyjnego zera ani dowodu braku wyposażenia. Surowe INI i pełne SDK
pozostają prywatnymi danymi wejściowymi, poza repozytorium i paczką moda.

Kontrola `X2Effect_Marked` potwierdza +10 do celności oraz zerowe premie
krytyczne w przekazanych plikach. Planer sprawdza aktywny jawny efekt
na własnym żołnierzu i odczytuje faktyczną wartość klasy, stosując ograniczoną
wagę ryzyka. Nie odczytuje gotowości ani zamiaru przeciwnika. Telemetria
`move_threat_preview` dodaje `marked_aim_bonus` i `target_status_weight`.
Reguły punktacji v2 pozostają bez zmian.

[Zakres danych, ustalenia i odtwarzanie katalogu v14](config-knowledge-v14.pl.md).
Kontrola końcowa v14: **388 testów Python zaliczonych bez pominięć**
z SDK i oboma zestawami konfiguracji, w tym odtworzenie całego katalogu.
Audyt potwierdził 14 klas moda i 29 skonfigurowanych nazw zdolności.
Przeszły testy skryptu budowania, kolektora raportów, 79 lokalnych odnośników
w zmienionych dokumentach oraz `git diff --check`.
Testy źródeł i konfiguracji nie zastępują kompilacji Windows ani próby w grze;
wynik działania v14 pozostaje do potwierdzenia.

## Uzupełnienie konfiguracji DLC z gry

Otrzymano pięć archiwów z konfiguracjami gry: `DLC_1`, `DLC_2`, `DLC_3`,
`TLE` i `XCom_DLC_Day0`, łącznie 79 INI i 796252 bajty. W przekazanej
instalacji SDK nie ma katalogu konfiguracji DLC; nie jest potrzebny do tego
uzupełnienia. Pliki `XCom*.ini` z dodatków gry są odrębnym wejściem od
wygenerowanych ustawień SDK.

Rozszerzenie zachowuje pochodzenie wpisów i operatory tablic między warstwami
oraz rozpoznaje sekcje pochodnych klas szablonów, w tym SPARK-a.
Kolejność składania dostarczonych plików jest zapisana jawnie; pełna natywna
kolejność ładowania pozostaje niepotwierdzona. Usunięcia i dodatki AI z
`DLC_3` wymagają wcześniejszych wpisów `DLC_2`.

Nowe dane rozwiązują 55 wcześniejszych pól broni DLC. Dwa odwołania kategorii
apteczek mają wartość w już posiadanych źródłowych `defaultproperties`.
Pozostałe dwa odwołania obrażeń Feral MEC M2/M3 są opisane osobno,
bez przypisywania im wartości M1 i bez żądania kolejnych archiwów.

To aktualizacja narzędzi i katalogu. Kod UnrealScript, reguły punktacji
i rewizja `mission-report-v14` pozostają takie same; zainstalowany v14
nie wymaga nowej kompilacji tylko z powodu tego uzupełnienia.
[Wejścia, przykłady i odtwarzanie katalogu DLC](dlc-config-knowledge.pl.md).

Wynik katalogu po uzupełnieniu: 196 sekcji bazowych statystyk, 177 zestawów
wyposażenia i 684 rozwiązane odwołania parametrów broni (682 z konfiguracji,
2 ze źródłowych wartości domyślnych); 2 odwołania pozostają nierozwiązane.
Indeks AI obejmuje 28 jawnych korzeni i 166 dopasowań według grupy postaci.

Kontrola końcowa uzupełnienia: **412 testów Python zaliczonych bez pominięć**
z SDK, konfiguracją bazową i pięcioma katalogami DLC gry. Odtworzono cały
katalog i potwierdzono 13 zastąpionych węzłów AI bez pozostawienia starych
duplikatów, w tym cztery poprawki DLC_3 do DLC_2 z właściwym pochodzeniem.
Przeszły 53 lokalne odnośniki, walidacja argumentów CLI i `git diff --check`.
Ta aktualizacja nie zmienia UnrealScript ani wyniku prób w grze.

## V15 — AP, pozycja do ataku i chmury trucizny

[Raport v14](report-2026-11-04-v14-poison.pl.md) zawiera trzy przegrane próby.
Ostatnie GasStation kończy się w turze 9 z natywnym odczytem −15100.
Historia pokazuje odroczone spadki HP po `PoisonSpit`, lecz brak geometrii
chmur i flagi zatrucia w v14 uniemożliwia odtworzenie konkretnych wejść.
Wszystkie 48 podglądów ruchu v14 miało nieaktywne Marked; aktywna waga
tego efektu nadal wymaga osobnej próby.

V15 rozdziela publiczny `TileContainsPoison` od `Poisoned`, sprawdza aktualną
odporność oraz robotyczność i zachowuje natywną kontrolę pozostałych zagrożeń.
Wyjątek trasy wyjścia dotyczy ciągłego początku własnej chmury, wymaga czystego
widocznego końca i nie dopuszcza ognia, kwasu ani ponownego wejścia po wyjściu.
Nie usuwa istniejącego statusu trucizny.

Podgląd podstawowego strzału po ruchu wykorzystuje natywną zdalną widoczność
i warunki pojedynczego celu. Pełna kalkulacja szansy trafienia nie przyjmuje
hipotetycznej pozycji strzelca. Dlatego prognoza zmiany zasięgu i osłony jest
ograniczoną heurystyką, bez modyfikacji historii lub `TileLocation` jednostki.
AP są projektowane na lokalnej kopii z zachowaniem typów i kosztów.
Po każdej akcji kontroler odczytuje stan i legalne polecenia ponownie.

Nowy `attempt_verdict` wymaga zwycięstwa i pewnych dodatnich punktów bieżącej
misji. Natywne `outcome` pozostaje osobno; zero lub ujemny wynik nie zalicza
próby. `mission_points_known`, `mission_points` i `mission_final` nie
utożsamiają sumy drabinki, delty od F8 ani starego HUD-u z końcowym wkładem
misji. Częściowa ocena porównawcza nie potwierdza sukcesu.

Reguły porównawcze v2 i katalog DLC pozostają bez zmian. Kompilacja Windows
oraz skuteczność v15 w grze pozostają do sprawdzenia.
[Zakres, ograniczenia i scenariusze v15](tactics-v15.pl.md).

Kontrola końcowa v15: **480 testów Python zaliczonych bez pominięć**
z SDK oraz bazową i DLC konfiguracją gry. Audyt referencji potwierdził
17 klas moda i 29 skonfigurowanych nazw zdolności. Przeszły testy skryptu
budowania, kolektora raportów, 88 lokalnych odnośników w zmienionych
dokumentach i `git diff --check`. Testy obejmują typy AP i koszty darmowych
akcji, prognozę podstawowego strzału, wyjście z chmury i warunek dodatniego
wyniku. Nie przeprowadzono kompilacji Windows ani próby v15 w grze.


## V16 — odrzucony podgląd granatu i koniec tury

Późniejszy [raport v15](report-2026-11-04-v15-stops.pl.md) potwierdza
uruchomienie v15 i jeden zgodny podgląd ruchu przed strzałem: prognoza
47→68%, następny rzeczywisty odczyt 68%. Misja SabotageCC na trudności 3
zakończyła się porażką w turze 18. Chmury trucizny i kombinacje AP nie
wystąpiły w tej próbie.

Trzy zatrzymania w turze 10 nastąpiły przed aktywacją tego samego granatu.
Nie są odrzuceniami rozkazu przez silnik. Ogólny komunikat v15 nie pozwala
rozstrzygnąć, czy zmieniło się lądowanie, bezpieczeństwo wybuchu czy zestaw
celów. V16 zachowuje te kontrole, dodaje rozróżnione przyczyny i pamięć
odrzuconej zdolności; blokuje ten sam stan i ogranicza ponowienia po zmianie
historii. Następna decyzja może wybrać inną akcję bez wyłączania autoplaya.

Osobne starsze zatrzymania `Engine rejected end turn` wynikają z błędnej
interpretacji API. `XGPlayer.uc:437–446` wysyła `eGameRule_SkipTurn`, ale
po wysłaniu również zwraca `false`. V16 oczekuje ograniczony czas na
pasujący kontekst historii lub rzeczywistą zmianę gracza/tury i zapobiega
ponownemu wysyłaniu tego samego żądania. Zakres sprawdzania obejmuje
historię, misję i lokalnego gracza.

Reguły punktacji v2, wymóg zwycięstwa z wynikiem > 0 oraz katalog DLC
pozostają bez zmian. Liczba klas moda pozostaje 17. Kompilacja Windows
oraz próba v16 w grze wymagają osobnej weryfikacji.
[Zakres zmian i testy odbiorcze v16](tactics-v16.pl.md).

Kontrola końcowa v16: **505 testów Python zaliczonych bez pominięć**
z SDK oraz konfiguracją bazową i DLC gry. Audyt referencji potwierdził
17 klas moda i 29 skonfigurowanych nazw zdolności. Przeszły testy skryptu
budowania, kolektora raportów, 98 lokalnych odnośników w zmienionych
dokumentach i `git diff --check`. Niezależny przegląd nie znalazł uwag
blokujących w pamięci odrzuceń, limitach ponowień ani potwierdzaniu końca
tury. Nie przeprowadzono kompilacji Windows ani próby v16 w grze.

## V17 — przegląd dwóch portów pomocnika

Przyjęto [PR #7](https://github.com/HeisenbergC29/autoplay-xcom2/pull/7)
z natywnymi atakami Berserkera i
[PR #9](https://github.com/HeisenbergC29/autoplay-xcom2/pull/9)
z ochroną własnego żołnierza pod odwracalną kontrolą umysłu. SDK potwierdza
stockowe style melee, koszty AP oraz historyczny odczyt właściciela używany
przez usuwanie `X2Effect_MindControl`. Kontrole źródeł obejmują aktywny efekt,
usuwanie po śmierci źródła, wcześniejszą własność i ochronę granatu.
Zmiany zachowują pamięć odrzuconych podglądów i potwierdzanie końca tury v16.

Końcowy zestaw integracji zaliczył **513 testów Python bez pominięć**
z prywatnym SDK, konfiguracjami bazowymi i DLC gry. Audyt referencji
potwierdził **17 klas moda i 31 skonfigurowanych nazw zdolności**. Trzy
zestawy pomocników PowerShell — budowanie, zbieranie SDK i raportów —
zaliczono lokalnie w PowerShell 7.6.9.
[Publiczne CI kodu v17](https://github.com/HeisenbergC29/autoplay-xcom2/actions/runs/42021235262)
dla `97e79e3` zaliczyło **455 testów Python, przy 58 pominiętych** z braku
prywatnych wejść, oraz trzy zestawy PowerShell na Windows. Te testy
PowerShell nie uruchamiają kompilatora WOTC.

Twardy filtr pamięci marszu z PR #11 wymaga poprawek i nie został
zintegrowany w v17. Kompilacja Windows WOTC SDK i próba v17 w grze
pozostają **NIEURUCHOMIONE**. To integracja źródeł, bez nowego wydania
binarnego. [Zakres, pochodzenie i scenariusze v17](tactics-v17.pl.md).

## V18 — izolowana wizualizacja DevastatingPunchMP

[PR #16](https://github.com/HeisenbergC29/autoplay-xcom2/pull/16) dodaje
do rozpoznanych hit/miss efektów szablonu MP brakujące flagi ukrywania
`AA_HitResultFailure`, zgodnie ze zwykłym wariantem SDK. Przegląd nie
stwierdził zmian AP, obrażeń, efektu Impairing, HUD ani punktacji.
[Integracja #19](https://github.com/HeisenbergC29/autoplay-xcom2/pull/19)
oznacza kod jako v18 i dodaje startupowe liczniki zastosowania poprawki.

Integracja zaliczyła **518 testów Python bez pominięć** z prywatnym SDK
i konfiguracjami; audyt referencji potwierdził **17 klas / 31 nazw
zdolności**. Publiczne CI PR #16 zaliczyło 458 testów, pomijając 60
kontraktów prywatnych wejść; końcowe CI integracji jest w PR #19.

Późniejszy raport z rewizją v17 obejmuje dwie porażki i awarię, bez
potwierdzenia dokładnego SHA kompilacji. Przyczyna awarii pozostaje
nieustalona. Kompilacja Windows WOTC SDK i próba v18 w grze:
**NIEURUCHOMIONE**. Brak redscreen nie jest dowodem usunięcia crasha;
do oceny potrzebny jest rzeczywisty cios oraz startupowe `templates > 0`,
`matched > 0` i `skipped=0`. Pominięte warianty trudności wymagają przeglądu.
[Instrukcja A/B](experiment-15-berserker-mp-visualization.pl.md).

## V19 — osobny cache tekstu punktów HUD

PR #22 buforuje tylko tekst panelu; pozostawia natywne obliczenia,
końcowy odczyt, formatowanie oraz zapis faktycznie wyświetlanego tekstu.
Invalidacja obejmuje obiekt i indeks historii, pierwszy odczyt oraz
okresowy termin przy stabilnej historii. OFF nie wstrzymuje odświeżania.
Integracja v19 i startupowy opis interwałów są koordynowane w issue #23.

Przejrzany PR #22 oraz kod integracji v19 zaliczyły **524 testy bez
pominięć** z prywatnym SDK i konfiguracjami; audyt **17 klas / 31 nazw
zdolności PASS**. Publiczne CI PR #22: 464 PASS / 60 SKIP oraz trzy zestawy
PowerShell PASS. Końcowe CI v19 jest śledzone w PR #24. Windows WOTC SDK i gra v19:
**NIEURUCHOMIONE**.

Nowe zawieszenie v18 opisuje analiza HELPER w #21. Przyczyna nadal nie
jest ustalona; ukrycie HUD podczas fazy wroga samo jej nie dowodzi.
Baza A zachowuje tę samą poprawkę MP, a B zmienia tylko harmonogram
odczytu tekstu i identyfikację diagnostyczną.
[Porównanie v18/v19](experiment-17-hud-polling.pl.md).

## V20 — pełna mapa i pozycje aktywnych wrogów

6 listopada użytkownik bezpośrednio potwierdził pełną wiedzę AI o mapie
i lokalizacjach aktywnych przeciwników. PR #26 wprowadza `APX_FullIntel`
i domyślne `EnableFullIntel=true` dla lokalnego XCOM. Wariant `false`
zachowuje wiedzę opartą na widoczności. Natywne FOW API ujawniają teren;
nie są potwierdzeniem widoczności modeli ani źródłem nowych legalnych
celów ataku. Natywne `AvailableActions`, `AA_Success`, AP i RNG pozostają
obowiązujące. Pełna wiedza nie pozwala odczytywać prywatnych budżetów
akcji lub zamiarów wroga.

Po poprawkach przeglądu kod `e8aa70bef727a6a7672d400156f225896cdec1c6`
zaliczył **539 testów z prywatnymi wejściami bez pominięć** oraz audyt
**18 klas / 31 nazw zdolności PASS**. Regresje obejmują cel misji i łup
przy dalekim wrogu, widoczną walkę, ostatni AP oraz odzyskiwalnego sojusznika
jako zagrożenie chronione przed własnym atakiem. Końcowe CI i decyzja
są śledzone w PR #26 i issue #27. Kompilacja Windows WOTC SDK i próba v20 w grze:
**NIEURUCHOMIONE**.

[Najnowsza GasStation v19](report-2026-11-06-v19-gasstation.pl.md) zakończyła
się porażką i normalnym zamknięciem logu. −20100 pozostaje częściowym
odczytem przy 18 niezapisanych klatkach; misja nie sprawdzała natywnego
`GetTotalScore`, ciosu MP ani żądań końca tury. V20 nie jest przez to
potwierdzoną naprawą wcześniejszych zawieszeń.
[Zakres i próba v20](experiment-25-full-intel.pl.md).
