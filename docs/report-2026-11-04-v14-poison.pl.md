# Raport v14: ruch przed strzałem i trucizna

Raport `AutoplayXCom2-20261104-152948-6d84690d.zip` zawiera siedem
unikalnych sesji po usunięciu powtórzeń z kopii logów. Trzy sesje mają
`revision=mission-report-v14`; pozostałe są starszym materiałem.
Wszystkie trzy próby v14 zakończyły się porażką gry.

| Identyfikator sesji, końcówka | Misja | Trudność | Koniec | Zapis punktów |
| --- | --- | ---: | --- | ---: |
| `16-1-13-677_915` | `ChallengeAbductionGasStation` | 2 | porażka, tura 8 | natywny −14000 |
| `16-9-53-342_890` | `SabotageCC` | 3 | porażka, tura 14 | porównawczy, częściowy −16800 |
| `16-22-46-69_915` | `ChallengeAbductionGasStation` | 2 | porażka, tura 9 | natywny −15100 |

Ostatnia próba GasStation ma 31 przyjętych rozkazów i zero odrzuceń:
14 ruchów, 10 `StandardShot`, jeden strzał snajpera, jedną stabilizację,
trzy `HunkerDown` i dwa przeładowania. Nie wybrano granatu, overwatch ani
Aid Protocol. Potwierdzono zabicie trzech widocznych przeciwników.
Oddział kończy z dwoma zabitymi i dwoma nieprzytomnymi. Central zachował
1 HP, lecz natywny `LadderKilledScored` oznaczał punktową utratę żołnierza.
Liczba literalnych zgonów nie wystarcza więc do odtworzenia kary gry.

Ostatni zapis HUD-u pokazywał −10100; końcowy odczyt gry wynosił −15100.
Sam ostatni widoczny licznik nie jest pewnym końcowym wynikiem. Natywny
zapis drabinki, wynik pojedynczej misji oraz częściowy wynik porównawczy
pozostają osobnymi danymi.

## Trucizna: co pokazuje historia

W najnowszym GasStation `PoisonSpit` ma `seq=991`, historię 212 i turę 1.
Wpisy celów `seq=992–994` obejmują trzech żołnierzy: `63486`, `63474`
i `63480`. Nie tracą HP bezpośrednio w tych wpisach. Na początku tury 2,
w `seq=1005–1007`, każdy z nich traci po 1 HP. Snajper wcześniej otrzymał
3 obrażenia od `ScythingClaws` Facelessa, w `seq=999–1000`.

Central traci kolejne punkty HP również po późniejszym ruchu. Jest to zgodne
z trwającym statusem zatrucia: **opuszczenie chmury nie leczy już nałożonej
trucizny**. Raport v14 nie zapisuje jednak statusu `Poisoned` ani geometrii
chmur. Nie dowodzi, która konkretna trasa weszła w chmurę, jak długo dany
żołnierz w niej stał ani które późniejsze obrażenia pochodziły z tego efektu.

Kontrola SDK rozdziela publiczne `TileContainsPoison` od statusu jednostki.
Efekt wejścia w chmurę nakłada `Poisoned`, a ponowne nałożenie odświeża efekt.
Dlatego istniejące zatrucie nie powinno być traktowane jako odporność na
pozostawanie w chmurze lub ponowne wejście. Nie ustalono implementacji
natywnego `TileContainsHazard`; dodatkowa jawna kontrola trucizny nie jest
dowodem, że natywna funkcja jej nie uwzględniała.

## Ruch przed atakiem: okazje do sprawdzenia

Central w GasStation miał 2 AP i wybierał strzał 54% w decyzjach 21 i 23
(`seq=2532` i `2783`), bez zarejestrowanego kandydata ruchu dla niego.
W SabotageCC decyzje 33 i 34 zawierają strzały 32% i 30% przy 2 AP;
decyzja 42 zawiera strzał 38% przy 2 AP. To przypadki do sprawdzenia,
**nie dowód istnienia legalnego, bezpiecznego lepszego pola**.

Strzał 27% w decyzji 20 SabotageCC miał już tylko 1 AP. Ruch odbierałby
możliwość tego ataku; nie jest przykładem niewykorzystanej kombinacji
niebieskiego ruchu i strzału.

Dotychczasowe `best_attack_after_move_ap` porównuje te same bieżące legalne
cele po odjęciu kosztu AP ruchu. Nie oblicza szansy trafienia z docelowego
pola. Zwykły wynik ruchu konkuruje natomiast z pełną wartością bieżącego
strzału. Nowy ograniczony wariant oceny „ruch + strzał” opisuje
[taktyka v15](tactics-v15.pl.md).

## Pozostałe ustalenia i wynik próby

Raport potwierdza stabilizację w najnowszym GasStation oraz dwa zaakceptowane
granaty w próbie SabotageCC. Nie potwierdza skuteczności aktywnego Marked:
wszystkie 48 zapisów `move_threat_preview` z prób v14 mają
`marked_aim_bonus=0` i `target_status_weight=1`.

Nowe kryterium projektu wymaga **zwycięstwa i dodatniego wyniku misji**.
Wynik zero lub ujemny przy zwycięstwie oznacza nieudaną próbę. Brak pewnego
końcowego wyniku pozostawia ocenę niepotwierdzoną. Te trzy próby są
nieudane już na podstawie porażki gry. Historyczne zwycięstwa v8 zachowują
swój oficjalny wynik; nie potwierdzają automatycznie nowego kryterium.

[Następna próba](legacy-test.pl.md) · [Rejestr i punktacja](mission-recording.pl.md).
