# Skończona kolejka przed wspólnym testem — 14 XI 2026

Parasol wykonania: [#86](https://github.com/HeisenbergC29/autoplay-xcom2/issues/86).
Na polecenie użytkownika [#4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4)
jest **BLOCKED** do końca bieżących prac źródłowych LEAD i HELPERA. Nie przekazujemy
osobnego buildu po każdym PR. Następna kolej pracy: **HELPER**, review i integracja LEAD.

Źródła po odbiorze #95: v40, source head `134eac9eb00b504868b58500f992330b56d77952`.
**834 private PASS/0skip**, SDK27/31 i niezależne review PASS;
CI300: 752 PASS/82 SKIP i 6 kroków PowerShell PASS.
Native Windows make/game v40: **NOT RUN**. Pobierać aktualne main po integracji.
Staging/OW jest źródłowo wdrożone, bez dowodu perfekcyjnego przyszłego kontaktu.

**Następny HELPER: #89 i skoordynowane #10**, potem pozostałe #28/#38.
Przyszły horyzont/footprint #87 nadal Unknown; w #89 potrzebny źródłowy
kontrakt albo precyzyjny disposition i bezpieczny krótszy ruch. Unknown nie
certyfikuje dash. Nie trzeba kolejnego manifestu SDK ani osobnego buildu v40.

## Lista realizacji

Każdy numer poniżej linkuje do issue w tym repozytorium. READY oznacza pracę
źródłową, SOURCE DONE oznacza wdrożenie, a GAME DEFERRED oznacza brak dowodu z gry.
To rozróżnienie nie zmienia warunku sukcesu: autonomiczne native WIN oraz znany
końcowy wynik misji >0. Niekompletne punkty nie certyfikują zaliczenia.

| Zadanie | Stan / zależność | Konkretny wynik wymagany przed przekazaniem |
| --- | --- | --- |
| LEAD, [#85](https://github.com/HeisenbergC29/autoplay-xcom2/pull/85) | SOURCE DONE | Naprawiony replay objective identity, bounded traversal, reviewed head9eca03d, merge49c7378. Pełna punktacja nadal osobno #79. |
| LEAD, zasady i kolejka | SOURCE DONE #90, bieżąca aktualizacja po #91–93 | Aktualne AGENTS/TEAM/PROJECT-STATE, poszerzona zgoda patrolowa, zadania i bramka #4; brak polecenia buildu. |
| HELPER [#87](https://github.com/HeisenbergC29/autoplay-xcom2/issues/87) | Bieżący horyzont SOURCE DONE #91; przyszły/footprint pozostały | Jeden snapshot/budżet kontaktu, świeżość danych patrolu na właściwym AI clock, concealment ruch/stacjonarny oraz revealed LOS; Clear/Caution/Unknown dla całej trasy i jawnego horyzontu. Musi wpływać na realną decyzję planera, nie tylko recorder. |
| HELPER [#88](https://github.com/HeisenbergC29/autoplay-xcom2/issues/88), konsoliduje [#12](https://github.com/HeisenbergC29/autoplay-xcom2/issues/12)/[#31](https://github.com/HeisenbergC29/autoplay-xcom2/issues/31) | SOURCE STAGE DONE #95; przyszła pewność nieudowodniona | Proaktywna zasadzka z kierunkiem osłony, liniami reakcji, odstępami AoE i stanem approach/setup/armed/open/abort. Ograniczony czas oczekiwania, reset i przerwanie przez timer/ratunek/zmianę kontaktu. Native opener/OW/AP; concealed i revealed osobno. |
| HELPER [#89](https://github.com/HeisenbergC29/autoplay-xcom2/issues/89) | READY po #95, skoordynować #10; domknąć kontrakty #87 | Szybszy zwykły marsz tylko po całej rzeczywiście osiągalnej, natywnie opłacalnej i potwierdzonej Clear trasie; Unknown prowadzi do legalnego krótszego ruchu. AA_Success StandardMove i Mobility×2 nie dowodzą kosztu dowolnej trasy. |
| HELPER [#10](https://github.com/HeisenbergC29/autoplay-xcom2/issues/10) | READY | Ograniczona wygasająca pamięć spokojnej trasy między turami, per unit/kontekst celu. Preferować postęp i alternatywę, zachować jedyną legalną drogę powrotu. Bez wpływu na ratunek, ewakuację, hazard escape i combat. |
| HELPER [#28](https://github.com/HeisenbergC29/autoplay-xcom2/issues/28) | READY | Podejście medyka do pilnego leczenia/detoksu, także niekrwawiącego pacjenta. Potwierdzony własny native ability/range/status/AP/ładunki, bezpieczna pełna trasa i świeży skan po ruchu. Obecna stabilizacja i ucieczka pacjenta z chmury nie zastępują tego zakresu. |
| HELPER [#38b](https://github.com/HeisenbergC29/autoplay-xcom2/issues/38) | READY | Skończona macierz rodzin player AoE w SDK oraz konkretne rozszerzenie planera o potwierdzone kontrakty poza obecnymi Frag/Alien Throw/Launch. Dla innych rodzin precyzyjny zakres unsupported. Wtórne eksplozje wymagają rzeczywistych extents/triggers i ochrony obiektów, bez zdejmowania guardów. |
| HELPER [#20](https://github.com/HeisenbergC29/autoplay-xcom2/issues/20), audyt podpór | SOURCE AUDIT DONE #93; forecast UNSUPPORTED | Rozstrzygnąć EnvironmentalDamage/ScythingClaws/podłogi/upadki: wdrożenie tylko przy wiarygodnym obserwacyjnym kontrakcie; w przeciwnym razie konkretny opis brakującego native/asset dowodu i zachowany fallback. Nie zakazywać dachów na podstawie hipotezy. Formation AoE już wdrożone. |
| HELPER [#79](https://github.com/HeisenbergC29/autoplay-xcom2/issues/79) | Reporting/audyt SOURCE DONE #92; parity/coverage DEFERRED | Analizator raportów rozpoznaje v3 profile/rate_source/parity/coverage niezależnie od archiwalnego v2. Skończony audyt civilian replay/origins/disabled/restart/bonus/decay: implementować udowodnione kontrakty, dokładnie opisać pozostałą niepewność i wymagany dowód. Sama zgodność stawek nie dowodzi kompletności/oficjalności. |

## Kolejność i granice pracy

Etapy bieżącego kontaktu #87/#91 i staging/OW #88/#95 są wdrożone.
Następny claim #89 i skoordynowane #10 na aktualnym main.
Równolegle można prowadzić niezależne badania #28/#38,
lecz przed edycją MissionPlanner/Controller trzeba uzgodnić właściciela plików.
Pozostałe focused zmiany #28/#38 po review; koordynować wspólne pliki.
Maksymalnie trzy aktywne implementation PR. Nie ma potrzeby czekania na zgodę
na już przypisane odwracalne prace, ale każdy PR wymaga aktualnej bazy i review LEAD.

[#48](https://github.com/HeisenbergC29/autoplay-xcom2/issues/48) ma już reader i
potwierdzoną emisję runtime. Jego bieżący konsument jest już w #91/#87, nie w kolejnym
reader-only PR. #12 i #31 zachowują historię, a wspólne wykonanie jest w #88.
Nie usuwać globalnie concealed gate ani nie wymyślać przyszłych native targetów.

Nowa zgoda obejmuje dostępne zapisane dane patrolu, również całą trasę, jeżeli
istnieje. Stock SDK nie daje typowej stałej trasy wieloturowej. Znany waypoint,
cache przebytego ruchu i graf korytarzy nie są równoważne. Nie uruchamiać
mutujących getterów, AI wyboru następnego ruchu ani przyszłego RNG.
[Źródła mechanik i granice prognozy](patrol-detection-and-tempo.pl.md),
[wybór kandydatów i losowanie punktu](patrol-selection-algorithm.pl.md).

#87 nadal nie ma konserwatywnego następnego horyzontu, cache segmentów ani pełnego
multi-tile visibility contract. #91 nie zostaje uznane za ukończenie tych punktów.
Pozostały zakres #89 wymaga obsłużonego footprint/źródłowej obwiedni albo
jawnego Unknown, bez uznawania waypointu za pewny przyszły ruch. Staging #95
korzysta z wariantów jako heurystyki, bez pełnej rekonstrukcji trasy. Prognoza wariantów
może rankować miejsca zasadzki; nie zwęża konserwatywnego dowodu bezpieczeństwa.

#79 po #92 ma ukończone osobne raportowanie v3 i skończony source disposition.
Civilian history nie wynika z samego removed-from-play; kwalifikacja native
award/decay/restart/bonus i coverage pozostają nieudowodnione. Nie ma kolejnej
READY implementacji bez nowego konkretnego kontraktu; partial pozostaje partial.

## Wdrożone źródła, odroczone dowody z gry

Te pozycje pozostają jawnie nieudowodnione, ale nie tworzą samodzielnie kolejnej
zmiany źródłowej bez nowego konkretnego błędu:

| Issue | Stan i dokładnie odroczony dowód |
| --- | --- |
| [#56](https://github.com/HeisenbergC29/autoplay-xcom2/issues/56) | Obecne opening/contact/Sweep/control-source i progress guards wdrożone do v37. Nowy raport ruchu/release/HP/outcome potrzebny do oceny przeżycia; ostatni source audit nie wskazał nowej konkretnej luki. Nie zwiększać arbitralnie ryzyka bez obserwacji. |
| [#29](https://github.com/HeisenbergC29/autoplay-xcom2/issues/29), [#46](https://github.com/HeisenbergC29/autoplay-xcom2/issues/46) | Native plant-goal/relay wdrożone; starsze raporty potwierdzają zaakceptowane akcje. Brakuje autonomicznego SabotageCC po v33 i wyniku nowej wspólnej wersji, nie kolejnej kopii tej samej implementacji. |
| [#54](https://github.com/HeisenbergC29/autoplay-xcom2/issues/54) | Melee/explosive-cover source guard wdrożony; skuteczność przyczynowa wymaga gry. Szerszy audyt podpór ma osobny skończony zakres w #20 powyżej. |
| [#15](https://github.com/HeisenbergC29/autoplay-xcom2/issues/15), [#21](https://github.com/HeisenbergC29/autoplay-xcom2/issues/21), [#40](https://github.com/HeisenbergC29/autoplay-xcom2/issues/40) | Historycznych awarii nie uznajemy zbiorczo za rozwiązane. Concrete v27 score crash path naprawiony #58; późniejsze próby doszły do native end. Bez nowego hang nie ma obecnie zadania na kolejny dump ani powtarzanie starego cache eksperymentu. |

## Warunek zamknięcia bramki

Każdy source zakres z listy otrzymuje implementację albo precyzyjny, sprawdzony
disposition wskazujący dlaczego brakującego dowodu nie da się uzyskać źródłowo.
Zachowane są bezpieczne fallbacki; unsupported nie jest nazywane implemented.
Każdy scalany head ma review LEAD, właściwe testy z uczciwymi PASS/SKIP,
dostępne kontrakty prywatnego SDK/config i audyt referencji przy UC.

Przed oddaniem użytkownikowi paczki nie pozostaje aktywny claim HELPERA,
gotowy nieprzejrzany PR ani nierozstrzygnięty konkretny source finding z tej listy.
LEAD weryfikuje końcowe main/CI/marker/ZIP i zapisuje jedną macierz scenariuszy
w #4. Wtedy dopiero kolej użytkownika: jeden Windows build i wspólna runda gry.

Nowe niezwiązane pomysły zapisujemy później, bez cichego wydłużania tej kolejki.
Ukończenie źródeł nie dowodzi idealnych zasadzek, globalnej stabilności ani
zwycięstwa we wszystkich misjach; nie zastępuje odroczonej walidacji w silniku.
