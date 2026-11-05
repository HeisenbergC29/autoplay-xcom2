# V16: ciągłość działania po odrzuceniu planu

[Raport v15](report-2026-11-04-v15-stops.pl.md) ujawnił trzy zatrzymania
przed rzutem tego samego granatu. Starszy log ujawnił niezależny błąd
interpretacji wyniku funkcji kończącej turę. V16 poprawia obsługę tych
dwóch przypadków; reguły punktacji i katalog DLC pozostają bez zmian.

## Odrzucone przygotowanie granatu

Przed aktywacją granatu nadal trzeba ponownie potwierdzić dostępność,
trajektorię, lądowanie, bezpieczeństwo wybuchu i zestaw celów.
Nieudana kontrola nie uprawnia do rzutu. V16 zapamiętuje odrzucenie
kandydata i w kolejnej decyzji rozważa inną legalną akcję.

Ta sama zdolność tego samego żołnierza nie jest ponawiana w niezmienionej
historii. Zmiana stanu pozwala ją ponownie rozważyć, lecz najwyżej trzy
niepowodzenia danej zdolności w rzeczywistej turze gracza. Historia,
gracz, tura i cofnięcie zapisu wyznaczają zakres pamięci. Ręczne OFF/ON
nie powinno samo usuwać blokady tego samego błędnego planu.
Pamięć ma limit 128 wpisów; nasycenie blokuje kolejne kandydatury obszarowe
do zmiany zakresu, zamiast usuwać stare wpisy i dopuścić pętlę.

Znacznik `area_revalidation_rejected` zapisuje żołnierza, identyfikator
zdolności, historię i szczegółowy wynik kontroli. Pola `reason`,
`evaluation_stage`, `evaluation_reason`, `impact_delta_sq`,
`location_delta_sq`, `expected_targets` i `fresh_targets` rozdzielają
brak dostępnej zdolności, nieudaną trajektorię, różnicę lądowania,
niebezpieczny wybuch i różnice celów. Liczby świeżych celów pozostają −1,
dopóki nie przejdzie pełna świeża kontrola bezpieczeństwa.
Są to odrzucenia podglądu przed wysłaniem rozkazu;
nie należy utożsamiać ich z `chosen.accepted=false`.

Poprawka nie wznawia ręcznego OFF ani nie pomija rzeczywistych odrzuceń
rozkazu przez silnik. Gdy nie ma innej sensownej akcji, nadal obowiązują
zwykłe reguły końca tury i ochrony przed bezcelową grą.

## Potwierdzenie końca tury

Stockowe `XGPlayer.EndTurn()` może wysłać `eGameRule_SkipTurn` i mimo to
zwrócić `false`. Sam wynik bool `PerformEndTurn()` nie rozstrzyga więc,
czy żądanie zostało przyjęte.

V16 wysyła jedno żądanie i oczekuje na pasujący kontekst `SkipTurn`
w nowej historii albo rzeczywistą zmianę gracza/tury. Sprawdza ciągłość
tej samej misji, historii i lokalnego gracza. Skan historii jest ograniczony
na klatkę; limit pięciu aktywnych sekund może zakończyć oczekiwanie dopiero
po nadrobieniu kursora historii. Kolejne decyzje nie mogą w tym czasie
wysłać duplikatu.

Znaczniki `end_turn_requested`, `end_turn_confirmed` i
`end_turn_unconfirmed` rozdzielają żądanie, dowód przyjęcia oraz brak
potwierdzenia. Dowodem jest `skip_turn_history` lub
`player_or_turn_transition`; `native_return` jest tylko diagnostyką.
Zmiana świata, utrata właściwego kontekstu lub rzeczywisty brak
potwierdzenia mają dać osobną diagnozę. Po przekroczeniu czasu żądanie
pozostaje zapamiętane, więc ręczne OFF/ON nie tworzy drugiego niejasnego
żądania tego samego końca tury.

## Zakres i kolejna próba

Pozostają mechaniki [v15](tactics-v15.pl.md): ograniczona prognoza ruchu
przed podstawowym strzałem, typy i koszty AP, czynności przygotowawcze
z zachowaniem legalnego ataku oraz rozróżnienie chmury i statusu trucizny.
Najnowszy raport potwierdza jeden ruch 47→68%, ale nie sprawdza chmur
ani kombinacji medycznej/Aid Protocol. Nie jest to potwierdzenie całej taktyki.

Sukces próby nadal wymaga **zwycięstwa i pewnego wyniku misji > 0**.
Zero, wynik ujemny lub brak pewnej końcowej punktacji nie potwierdzają
zaliczenia; oficjalny wynik gry pozostaje zapisany osobno.

Zbuduj v16 na Windows, zainstaluj świeży `dist\AutoplayXCom2.zip`
i sprawdź w raporcie `revision=mission-report-v16`. Kompilacja Windows
i próba v16 w grze pozostają do potwierdzenia.

Sprawdź odrzucony podgląd granatu z dostępną alternatywą, powtórzenie
w niezmienionej historii, zmianę stanu, limit ponowień, ręczne OFF/ON
i cofnięcie zapisu. Kontrola sojuszników, cywilów i celów misji musi nadal
blokować niebezpieczny rzut. Przy końcu tury sprawdź natywny zwrot `false`
z faktycznym `SkipTurn`, opóźnione potwierdzenie, pauzę, zmianę gracza/tury
oraz rzeczywisty brak potwierdzenia. Zachowaj pełny raport także po sukcesie.

[Instrukcja próby](legacy-test.pl.md) · [Lista testów](TESTING.pl.md) ·
[Rejestracja](mission-recording.pl.md).
