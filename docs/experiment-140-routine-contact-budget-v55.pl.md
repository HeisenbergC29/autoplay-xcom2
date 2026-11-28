# #140 etap 1 — rutynowa ocena tras przed kontaktem (v55)

## Zakres i dowód wejściowy

Baza `1b308c9c61617d5d136227c2e2ea7678d5809d6b`, [przydział LEAD #140](https://github.com/HeisenbergC29/autoplay-xcom2/issues/140#issuecomment-7242462305), [PR #144](https://github.com/HeisenbergC29/autoplay-xcom2/pull/144).
Według zanonimizowanego ustalenia LEAD Gas Station v53 D1: osiem detektorów, kompletny snapshot, cztery jednostki otrzymały Unknown/decision_budget, pozostało 0 sprawdzeń detektorów, 116 pól i 503 LOS. Wybrany ruch mission otworzył kontakt. Nie jest to dowód istnienia alternatywnej legalnej trasy na tej mapie. Nie analizowano surowego raportu.

## Mechanizm i koszt

- MaxDetectors nadal ogranicza snapshot do 64 referencji, a dotychczasowe 64 sprawdzenia pozostają dla nierutynowych konsumentów. Po korekcie LEAD przy aktywnym `bPatrolActive` również rutynowy ruch korzysta z tej samej wspólnej puli oraz starej strumieniowej oceny bez preflight. Nie otrzymuje dodatkowych 1024 par kosztem późniejszego ChooseApproach.
- MaxRoutineDetectorChecks = 1024 (brak lub wartość niedodatnia: 1024; dodatnia ograniczona do 1..1024). Jeden licznik dla całej decyzji kontrolera, wspólny dla wszystkich żołnierzy, prefiksów i lokalnych kandydatur ChooseMove. Wszystkie ścieżki nadal współdzielą limity 128 pól i 512 natywnych LOS.
- HasRoutinePairBudget sprawdza górne ograniczenie par (liczba przesuniętych pól * liczba znanych detektorów/interaktywnych). Jeśli nie mieści się w pozostałym limicie, zwraca Unknown/detector_pair_budget bez wydawania par/pól. Krótsza trasa może się zmieścić. Wcześniejsza pozytywna informacja o destrukcyjnym przejściu pozostaje nadrzędna. Preflight nie rezerwuje LOS i nie jest dowodem bezpieczeństwa.
- W najgorszym przypadku 1024 sprawdzenia par rutynowych i do 64 pozostałych (łącznie 1088); 16 razy większy limit rutynowy, nie 16 razy więcej LOS ani pól. Koszt rzeczywisty zależy od liczby detektorów i wczesnych zakończeń. Brak pomiaru czasu na silniku. Nie zwiększono puli endpointów ani długości dopuszczalnych tras. Przy 64 detektorach budżet rutynowy wystarcza najwyżej na 16 pełnych pól, przy 8 — na 128. Nie gwarantuje pełnej oceny wszystkich tras.
- Prefiks odrzucony tylko przez preflight `detector_pair_budget`, który przeszedł pozostałe bramki, nie kończy przedwcześnie ChooseMove. Zachowujemy go ze zwykłą oceną (z dotychczasową karą pamięci, jeśli występuje), a lokalne alternatywy muszą mieć Clear, przejść istniejące bramki postępu, osłon i concealment oraz uzyskać ściśle wyższy wynik ScoreOrdinaryRouteCandidate. Jeżeli takiej nie ma, zwracamy prefiks bez biletu drugiego blue. Pominięta trasa może zawierać rzeczywisty kontakt — Unknown nie jest Caution ani Clear, nie obiecujemy bezpieczeństwa.
- Istniejące kary Caution/Unknown, zakaz drugiego blue bez Clear, reguły AP, cover, concealment, pilność celu, zasadzki i ratunek/ewakuacja pozostają. Brak danych, natywnej geometrii lub budżetu nie daje Clear. Nie wprowadzono zmian AoE, Poison Spit, oceny strzału ani wyjścia z chmury. Legalny fallback może nadal otworzyć kontakt, jeśli nie ma lepszej kwalifikowanej trasy.

## Odtwarzalna próba źródłowa

`python -m unittest discover -s tests -p test_routine_contact_budget_v55.py -v`

Rzeczywiste fragmenty AssessRoute, ChooseMove (prefiks, lokalna ocena z minimalnym zyskiem, fallback, końcowa punktacja i bilet) oraz MakeDecision (TraceCandidateMove, Score > BestScore i CanUseMove) wykonuje translator UC; geometria, dostępność ścieżki, kohezja i zysk pozycji są kontrolowanymi fixture, nie symulacją całej gry. Stary wariant używa 64 par i wyłącza nowy preflight. Prefiks ma rzeczywiste ScoreRouteAdvance = 25 przy zerowym zysku kohezji, nie arbitralne 50. Lokalny zysk po kosztach 12 daje ScoreOrdinaryRouteCandidate = 32.

| Pomiar | Stary | Nowy |
| --- | ---: | ---: |
| Próby oceny | 4 | 5 |
| Rozpoczęte (co najmniej jeden odczyt pary) | 1 | 5 |
| Rozstrzygnięte Clear/Caution | 0 | 5 |
| Zużyte pary | 64 | 297 |
| Pozostałe pary | 0 | 727 |
| Propozycja czwartego żołnierza | Unknown, pierwotny prefiks | Clear, alternatywa z dodatnim zyskiem |
| Wybór kontrolera | Żołnierz 1, prefiks, 17 pkt | Żołnierz 4, alternatywa, 32 pkt |
| Bilet pierwszego blue wybranego ruchu | 0 | 1 |

Nowy wariant ocenia trzy prefiksy Clear, czwarty Caution (kontakt w środku, nie na końcu) oraz alternatywę Clear. Przy braku alternatywy pozostaje Caution bez biletu. Oddzielny test wymusza 16 par, odrzuca zbyt długą trasę bez zużycia, kończy krótszą i potwierdza Unknown przy rzeczywistym wyczerpaniu. Testy obejmują także niepełny snapshot, niezweryfikowane LOS, granice limitów i powiązanie liczników z MakeDecision.

## Druga korekta po przeglądzie LEAD — bramka kontrolera

[Przegląd](https://github.com/HeisenbergC29/autoplay-xcom2/pull/144#issuecomment-7245470269) do `53fce58b7c7140a78ddae1c6fac9a66c74103282`: gdy lokalna Clear wygrywa, `ChooseMove` oddaje przez opcjonalne out również wcześniej kwalifikowany `DeferredBudgetPrefix` i jego własny `DeferredBudgetScore`. Są zerowane na wejściu (także w kontrolerze przed wyborem każdej jednostki) i czyszczone, jeśli sam prefiks jest pierwszą propozycją. Gdy krótsza propozycja nie przejdzie istniejącej bramki, kontroler może porównać odłożony prefiks tylko z wyższą od obecnego BestScore oceną; obowiązują TraceCandidateMove oraz osobny CanUseMove bez wyjątków od powtórki. Po zaakceptowaniu Unknown zachowuje rutynowy charakter i nie daje biletu pierwszego blue ani wyjątku pilnego ruchu. Nie ma ponownego ChooseMove, BuildPathToTile ani dodatkowego AssessRoute. Diagnostyka `controller_budget_prefix_fallback` rozróżnia ten wybór od fallbacku wewnątrz planera.

Fixture z jedną jednostką: 12 kroków / Unknown / 17 pkt; 6 kroków / Clear / 32 pkt. Przy odwiedzonym krótkim końcu i świeżym prefiksie wybór to 12 kroków/17/bez biletu. Oba końce odwiedzone: oba odrzucone. Inny rozkaz z oceną 18 lub remis 17 zachowuje pierwszeństwo. Odwiedzenie krótkiego końca przez inną jednostkę nie blokuje Clear. Próba z rzeczywistym `RouteTempo.PenaltyFor`: zysk 40 minus kara powrotu 28 daje 12 i nadal 32 pkt; po zmianie celu kara jest zerowa, lecz bramka powtórki nadal odrzuca ten sam koniec. Test wykonuje fragmenty źródłowe `ChooseMove`, `MakeDecision`, pełne `CanUseMove` (w tym IsPostRevealShotReturn), `TraceCandidateMove`, `PenaltyFor` i `SoftVisitPenalty`. Kontrolowane zastępniki: ścieżki, geometria, wejścia scoringu i odwiedzin, recorder (lista wywołań) zamiast rzeczywistego zapisu, natywne bezpieczeństwo i dostępność na wejściu. Nie wykonuje natywnego dispatchu ani gry.

### Znana granica rankingu, świadomie bez zmiany wag

Przy 64 parach, 8 detektorach, kohezji +8, prefiksie 12 kroków i detektorze na pierwszym kroku, wcześniejszy strumień potwierdza Caution po 1 parze, a lokalna Clear z zyskiem 4,5 otrzymuje 24,5 i wygrywa. Preflight pomija długi prefiks bez odczytów, nadaje Unknown i 25 pkt (33 minus 8). Ta sama Clear zostaje w pełni oceniona po 48 parach, lecz przegrywa 24,5 do 25. Regresja jest odtworzona, nie skorygowana: nie uznajemy Unknown za Clear ani nie przyznajemy mu biletu; zmiana ogólnej punktacji lub częściowe sondowanie mogłyby zabrać budżet krótszym trasom. To ograniczenie kompromisu preflight do oceny przez LEAD, nie deklaracja równoważności obu polityk.

## Korekta po przeglądzie LEAD

[Uwagi](https://github.com/HeisenbergC29/autoplay-xcom2/pull/144#issuecomment-7245139298) do `b0c4f2c0fb97f0a381042e9ab744c3ebfcaa7451`: 1) przy 64 pozostałych parach prefiks 12 kroków jest pominięty bez pracy, a w tym samym wywołaniu krótsza trasa 6 kroków uzyskuje Clear po 48 parach, wynik 32 zamiast 17; 2) przy domyślnych 1024 parach i 32 detektorach trzy 10-krokowe trasy zużywają po 320, czwarty 8-krokowy prefiks jest pominięty, dwukrokowa alternatywa zużywa 64 i uzyskuje Clear; 3) przy aktywnym patrolu, 11 LOS, 8 detektorach i jednym niepotwierdzonym LOS na krok, zachowanie starej wspólnej puli 64 par pozostawia 3 LOS; rzeczywiste CountVariantLanes zwraca 3 i VariantPositionScore 66. Bez tej ochrony rozszerzona pula zużywa 11 LOS, 0 korytarzy, wynik -10000. Nie jest to dowód, że zasadzka zawsze ma dość budżetu; przywracamy dotychczasowy limit jej konkurenta, a nie zwiększamy wspólnej puli LOS. Testy obejmują też odmowę CanUseMove, lepszy istniejący rozkaz i brak drugiego blue dla Unknown.

Publiczne CI [46186998559](https://github.com/HeisenbergC29/autoplay-xcom2/actions/runs/46186998559) na `857fc692e6ee1f8cc2fcdd3b177b0b34dcb8fb89`: 1082 testy, 984 PASS / 98 SKIP, Python i PowerShell PASS. Kolejna zmiana dodaje negatywne warianty osłony, concealment, kontaktu i remisu punktacji. Wynik końcowego SHA jest w rozmowie PR, nie należy utożsamiać starszego przebiegu z nowszym.

Historyczne CI [46178711118](https://github.com/HeisenbergC29/autoplay-xcom2/actions/runs/46178711118) dla kodu i testów `df7734e75d438af3ae837aa0a64f256be3674976`: 1078 testów, 980 PASS / 98 SKIP, sześć testów #140 PASS, PowerShell helpers PASS. Wcześniejsze nieudane przebiegi ujawniły błędy adaptera testów, naprawione przed tym przebiegiem. Pełny prywatny audyt SDK nie został wykonany. Sprawdzono sygnatury istniejących natywnych metod GetPathPointsFromPath i CanSeeTileToTile oraz odczytów concealment w dostarczonym SDK; nie dodano nowych wywołań natywnych.

## Odbiór Windows / gra (NOT RUN)

1. LEAD przegląda dokładny HEAD PR, wykonuje pełny prywatny zestaw i audyt SDK, integruje zaakceptowane zmiany. Użytkownik kompiluje wskazany przez LEAD wariant v55 z 0 błędów / 0 ostrzeżeń.
2. Uruchomić Gas Station z tymi samymi ustawieniami i porównać pierwszą decyzję, snapshot, oceny kontaktu i wybrany ruch; odnotować, czy istnieje pełna ocena oraz użyteczna legalna alternatywa. Nie oczekiwać deterministycznego powtórzenia mapy/LOS ani gwarancji braku kontaktu.
3. Porównać czas decyzji przed kontaktem, w szczególności przy wielu detektorach, oraz porównać wybór przy aktywnej zasadzce; sprawdzić, czy pozostał budżet na ocenę korytarzy. Przy ograniczonym budżecie porównać `budget_prefix_fallback` z kwalifikowaną krótszą trasą; zarejestrować Unknown przy brakujących danych/limicie i sprawdzić, czy brak alternatywy nie wymusza postoju. Sprawdzić brak biletu drugiego blue po Caution/Unknown. Obecne markery pokazują ocenę wybranej trasy, nie pełne liczniki wszystkich odrzuconych kandydatur; fixture jest dowodem porównania pracy, nie raportem profilerowym.
4. Regresje: pilne X4/ratunek/ewakuacja, pościg w walce, zasadzki i OFF. Zachować natywny wynik i kompletną punktację; wygrana z wynikiem >0 pozostaje warunkiem sukcesu projektu.

Etap rozstawienia przed trwałym AoE i #141 pozostają poza tym PR. Nie scalamy main w roli HELPER.
