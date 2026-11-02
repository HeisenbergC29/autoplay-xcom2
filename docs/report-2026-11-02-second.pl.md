# Drugi raport Gatecrashera

Najnowsza sesja w ZIP-ie ma identyfikator rewizji `mission-report-v2`, poziom 3
(Legenda), wynik `loss` i cztery zgony własnego oddziału. ZIP zawiera także
kopię poprzedniej sesji w logu zapasowym; są analizowane osobno. Początkowe
pozycje oddziałów różnią się, więc nie jest to porównanie tego samego zapisu.

## Co rzeczywiście wydarzyło się w nowszej próbie

- 44 zaakceptowane rozkazy: 21 ruchów, 11 zwykłych strzałów i 12 overwatch.
  Brak przeładowań, przyczajenia i użytych granatów.
- Zwykłe strzały dały 6 trafień i 5 pudeł. Wykonano jeden strzał reakcyjny
  `OverwatchShot`: 18%, pudło. Dwanaście poleceń overwatch nie oznacza
  dwunastu oddanych strzałów.
- Poprawki poprzedniej wersji są widoczne: oddział używał trybu ostrożnego
  szukania kontaktu i nie wykonał wcześniejszego wejścia na dach.
- W decyzjach 35 i 36 zdrowi żołnierze wydali ostatni AP na odwrót oceniony
  odpowiednio na 46 i 45,48. Taki ruch wypierał strzał 46% oceniony na 39,65.
- Po potwierdzonym zabiciu przeciwnika jego pozycja pozostawała w pamięci
  kontaktów. Oddział ostrożnie szukał również zabitych celów, aż upłynął limit.
- Planer granatów sprawdził 239 punktów przy 41 sprawdzeniach dostępnej,
  obsługiwanej zdolności: 234 odrzucenia zasięgu, 1 trajektorii i 4
  bezpieczeństwa wybuchu. Żaden punkt nie przeszedł do oceny wartości ataku.
  Dane nie wskazują na błąd konwersji metrów na jednostki gry.
- `Interact_OpenDoor` było dostępne dopiero w późnych decyzjach ostatniego
  żołnierza. Brak osobnego planera tej akcji nie wyjaśnia początku porażki.

## Zmiany po tym raporcie

1. Zwykły odwrót zdrowego żołnierza ostatnim AP ma niższą ocenę. Nadal jest
   możliwy, gdy nie ma sensownego strzału; ratunkowy odwrót rannego zachowuje
   wyższy priorytet. To ocena kosztu utraconego strzału, nie reguła zakazująca
   odwrotu ani dowód, że atak zawsze będzie lepszy.
2. Pamięć kontaktu jest usuwana po potwierdzonej śmierci widocznego celu
   w wyniku własnej akcji. Używane są wcześniejsza widoczność i wynik tej akcji
   w historii, a nie bieżące HP ukrytego przeciwnika.
3. Granaty otrzymują propozycje celowania także bliżej rzucającego, przy
   krawędzi zasięgu. Cel może znaleźć się w promieniu wybuchu takiego punktu,
   mimo że nie można rzucić granatu dokładnie pod jego stopy. Propozycje używają
   natywnego zasięgu i promienia, a rzeczywista trajektoria, punkt lądowania,
   podłoga, widoczność i bezpieczeństwo wybuchu nadal muszą przejść kontrole.
4. Budżet punktów granatu jest dzielony między pozycje przeciwników, punkty
   przy krawędzi zasięgu i środki par. Późniejszy punkt poza zasięgiem nie
   nadpisuje już bardziej informacyjnej przyczyny odrzucenia bezpiecznej
   trajektorii. Log zawiera osobne powody oraz liczbowy zasięg i dystans.

Nowy rejestr oznacza sesję jako `mission-report-v3`. Następna próba wymaga nowej
kompilacji i instalacji `dist\AutoplayXCom2.zip`. Kompilację uruchamiaj na
zachowanym SDK bez `-BuildBase`, jeśli pakiety bazowe są już przygotowane.
Po misji zbierz raport [tym samym skryptem](mission-recording.pl.md).

Testy matematyki planowania i kontroli źródeł nie uruchamiają silnika gry.
Kompilacja Windows i skuteczność nowych decyzji wymagają ponownej próby.
