# GasStation v19 — raport z 6 listopada 2026

Najnowszy log z przekazanego pakietu zawiera jedną nową próbę
`ChallengeAbductionGasStation`, trudność 2, `mission-report-v19`.
Starsze kopie zapasowe pozostają osobnymi próbami. Rewizja i wpisy startowe
potwierdzają uruchomienie v19, ale log nie podaje dokładnego SHA kompilacji.
Surowych logów, zapisów i metadanych prywatnego pakietu nie publikujemy.

## Wynik i granice zapisu

| Obserwacja | Wynik |
| --- | --- |
| Natywne zakończenie misji | porażka |
| Przyjęte rozkazy | 40 z 40; 18 ruchów |
| Ostatni natywny odczyt punktów | −20100, częściowy |
| Pewność końcowego wyniku | `mission_final=False`; 18 klatek historii pozostało |
| Zamknięcie programu | normalne wyjście na żądanie i zamknięty log |
| Crash, autostop, potwierdzone zawieszenie | niezarejestrowane w tej próbie |

Próba projektu ma **FAIL** z powodu natywnej porażki. −20100 to ostatni
zaobserwowany odczyt, nie certyfikowana suma końcowa. Brakujące klatki mogą
zawierać ostatnie wyniki akcji; normalne zamknięcie pliku ich nie uzupełnia.
Nie należy z tej przegranej wnioskować, że scenariusz jest niemożliwy.

Startup potwierdza konfigurację cache HUD oraz dopasowanie poprawki MP
(`templates=1`, `matched=1`, `skipped=0`). W tej próbie nie wystąpił jednak
`DevastatingPunchMP`. Nie ma też żądań i potwierdzeń końca tury przez
mechanizm ticketów; nie został on tutaj osobno sprawdzony.

Legacy korzystało z punktów drabinki. Brak wywołań natywnego `GetTotalScore`
oznacza, że ta próba nie sprawdza redukcji jego częstości w Challenge ani
wcześniejszego zawieszenia `SabotageTransmitter`. Pojedyncza misja bez
awarii nie potwierdza usunięcia problemów stabilności.

## Taktyka i czynności pomocnicze

Powtarza się trafienie trzech członków drużyny jednym `PoisonSpit`.
Późniejsza ucieczka z chmury nie cofa wcześniejszych obrażeń i zatrucia.
Problem miękkiej oceny skupienia drużyny pozostaje w
[issue #20](https://github.com/HeisenbergC29/autoplay-xcom2/issues/20).

Dwukrotnie po `AidProtocol` nastąpił rzeczywisty strzał. To potwierdza
konkretne użycia wsparcia z zachowanym legalnym atakiem, nie dowodzi jeszcze
obsługi wszystkich kombinacji AP.

Dla łupu natywna zdolność zgłaszała `AA_NoTargets`; raport nie pokazuje
zignorowanej gotowej akcji podniesienia. Wykrwawiający się żołnierz zginął
przed następną decyzją planera, więc ten przypadek nie dowodzi pominięcia
legalnej, gotowej akcji stabilizacji. Oddzielne badanie wcześniejszego
podejścia i leczenia jest w
[issue #28](https://github.com/HeisenbergC29/autoplay-xcom2/issues/28).
Zaobserwowana panika nie jest potwierdzeniem kontroli umysłu; tej próbie
nie przypisujemy sprawdzenia ochrony przejętego sojusznika.

## Następna wersja

Użytkownik potwierdził pełną wiedzę o mapie i pozycjach aktywnych wrogów.
[V20](experiment-25-full-intel.pl.md) zmienia ten zakres informacji,
zachowując natywne akcje, AP, RNG i punktację. To osobna zmiana zachowania,
nie naprawa udowodniona tym raportem. Windows WOTC SDK i gra v20 pozostają
nieuruchomione; dokładny wariant do próby publikuje LEAD w
[issue #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
