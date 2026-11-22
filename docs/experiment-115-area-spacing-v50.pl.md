# HELPER #115 — zgrupowanie pod Poison Spit vs legalny strzał

Baza `main d0f827edb5335360e69e32710437c9174038a6ee`, osobna gałąź `helper/115-poison-spit-spacing-v50`. Po włączeniu LEAD #117 nie modyfikowano `APX_CombatPlanner` ani jego oceny Hunker Down. Źródło dowodu: **wyłącznie bieżący** `Logs/Launch.log` w prywatnym archiwum `AutoplayXCom2-20261122-105517-9277c808.zip`. Trzy stare backupy nie są trzema dodatkowymi próbami v48.

## Zaobserwowane v48

- GasStation: natywna porażka −16900 pkt, normalnie zapisane zakończenie. W pierwszej turze trzech żołnierzy strzelało z trzech bliskich pól (19,14), (20,15), (20,14), na jednakowym poziomie; jeden PoisonSpit objął trójkę, mimo wcześniej rozpoznanej pozycji Vipera. Następnie nastąpiła ucieczka z chmury, ale nie prewencja.
- Punkty odniesienia: strzały do Facelessa 82%, 71%, 70%; szansa na cel nie gwarantuje zabicia, a punktacja akcji nie dowodzi, że przesunięcie byłoby korzystniejsze.
- Planer strzelców: 221 skanów w GasStation, 0 zaakceptowanych propozycji (138 niewłaściwa gotowość, 59 brak obecnego wspieranego strzału, 21 brak istotnej poprawy prognozy, 3 ryzykowne/odrzucone ścieżki). W SabotageCC również 0 z 257. To nie dowodzi, że konkretne rozproszenie było legalne na rzeczywistej mapie.
- Znane parametry: podstawowe `X2Ability_Viper.CreatePoisonSpitAbility` w dostarczonym WOTC SDK tworzy `PoisonSpit`, rodzaj `X2AbilityMultiTarget_Cylinder`, `bUseWeaponRadius=True`, natywne `X2AbilityTarget_Cursor`, koszt 1 AP i globalny/lokalny cooldown. Wymiary konkretnego wyniku nie są deterministyczne od samego wzorca zdolności. LEAD ustalił promień `PoisonSpitGlob` 4; zastosowany model bierze **minimum 4 pola**, jeśli aktualnie żywy bliski wróg ma zainstalowane `PoisonSpit`. Nie czyta jego cooldownu, intencji ani przyszłego celu. Rozważa geometryczną liczbę potencjalnych współtrafionych, nie gwarantowaną listę ofiar.

## Różnica źródłowa v50

Dotychczas `APX_RepositionPlanner.ChooseMove` szukał głównie **materialnie wyższej** szansy podstawowego strzału na obecnie legalny cel. Taki warunek odrzucał bezpieczne rozproszenie po którym natywny strzał nadal byłby legalny, ale szansa trafienia nie poprawiłaby się o co najmniej 12 p.p.

Nowa, niezależna ścieżka rozważa wyłącznie:
1. Żołnierza aktualnie ujawnionego, z 2 AP, natywnie legalnym ruchem i bez aktywnego blokującego hazardu. Jeden odczyt natywnego rosteru lokalnego XCom (maks. 24 wpisy) i 12 własnych towarzyszy; brak kompletnego odczytu wyłącza opcjonalną zmianę rozstawienia.
2. Bliską aktualnie żywą jednostkę z faktycznie zainstalowanym `PoisonSpit`, odległość maks. 18 pól — **możliwą zdolność**, nie gotowość do natychmiastowego ataku.
3. Obecnie możliwą powierzchnię rażenia: `WorstSharedAreaTargets` przed i po przesunięciu z promieniem minimum 4. Wymaga minimum trzech potencjalnie jednocześnie trafionych i **realnego spadku** po ruchu. Bez spadku pozostają normalne strzały i ruchy.
4. Gdy istnieje bieżący legalny `StandardShot` lub `PistolStandardShot`, jego prawdziwą obecnie zmierzoną szansę/damage, aktualny cel oraz natywny remote LOS/warunki/cover, koszt AP po blue. Nowa prognoza może stracić maksymalnie 8 p.p. (zamiast wymagać wzrostu 12 p.p.). Wysoce wartościowy strzał `NativeScore >= 100` przy `NativeChance >= 75` pozostaje i nie jest zastępowany wyłącznie za sprawą geometrii rozproszenia.
5. Gdy **brak** bieżącego legalnego wspieranego strzału, alternatywna, słabsza ocena tylko dla pozycji umożliwiającej natywny remote LOS i walidację celu na **już widzianego przez drużynę** przeciwnika. Brak wyceny przyszłych obrażeń; po rzeczywistym ruchu trzeba uzyskać od silnika nowe `AA_Success`. Taki ruch ma niższą punktację niż dobry strzał w bieżącej decyzji.
6. Trasa: istniejący native reachable-cache blue, zgodność punktów i całej ścieżki, warunki bezpiecznego podporu, rozpoznane hazardy, każda kontrola eksplodujących osłon, ekspozycja nieprzekraczająca bieżącej, znany teren oraz konserwatywny limit 12 dodatkowych prób sprawdzenia przyszłej linii. Budżet osłon jest współdzielony z pozostałymi planerami, a odrzucone/prognozowane trasy nie dają AP lub shotów.

Wynik kontynuuje dotychczasowe `ChooseCompetitiveReposition` i porównanie z najlepszym ruchem/strzałem całego oddziału. `ScanReason` zyskuje wartości:
- `area_spit_reposition_retains_shot` — można po ruchu przypuszczalnie zachować aktualny strzał.
- `area_spit_reposition_opens_squad_lane` — brak legalnego strzału obecnie, lecz natywna zdalna widoczność sugeruje możliwość uzyskania go po ruchu; **nie** jest to potwierdzone przyszłe AA_Success.

## Rozróżnialne decyzje i przypadek pozostania

*Scenariusz numeryczny oparty na metodzie z prawdziwego UC, **nie** symulacja mapy:* natywny strzał wart 70, prognozowany 68, szansa 71→69, ekspozycja 25→22, wspólne ofiary 3→2, koszt blue=3, 2 AP. `ScoreAreaShotMove=80.4` — wygrywa z natywnym strzałem ocenionym na 70 i pozwala sprawdzić nowe `AA_Success` po przesunięciu. Dla natywnego strzału wartego 112 z szansą 82%, samo rozproszenie jest odrzucone; mocny strzał pozostaje. Dodatkowo brak spadku liczby wspólnych ofiar albo zwiększona ekspozycja nie mogą premiować ruchu.

## Testy / ryzyka / kryterium WOTC

`tests/test_area_spit_spacing_v50.py` obejmuje numeryczne oceny obu wariantów, brak utraty AP, silny natywny strzał, nieznany cel, źródło aktualnej zdolności wroga, limit geometrii, budżet i bezpieczeństwo całej trasy oraz **syntetyczny ZIP→CLI** obejmujący wybór ruchu, nowy legalny strzał po nim i pozostawienie innego bardzo dobrego strzału. Ten E2E sprawdza zachowanie analizatora i przykładową zgodność pól, nie przewiduje ani nie wykonuje akcji WOTC.

LEAD może scalić obydwa PR #115/#116 i wykonać **jedną** kompilację Windows. Próba: GasStation t1 — zanotować pola trzech pierwszych strzelców, `offensive_reposition_scan` ze wskazaniem nowej ścieżki i jej konkurencyjnej oceny, liczbę ofiar pierwszego PoisonSpit, szanse realnych strzałów po ruchu, punkty końcowe i wynik. Nie twierdzić, że pojedyncze uniknięcie chmury dowodzi stabilnej poprawy: porównać kilka prób/ustawień pozycjonowania, osobno zliczyć legalność drogi i nowe native shots. Sprawdzić także, czy AI **nie** odkłada szybkiej eliminacji wroga bez potrzeby oraz czy nie wchodzi na niepewną trasę.

**Status:** źródła i testy automatyczne mogą potwierdzać politykę scoringu. Kompilacja UnrealScript, A/B WOTC, legalność konkretnego przemieszczenia z logu i przyczynowy wpływ na zwycięstwo pozostają niezweryfikowane.
