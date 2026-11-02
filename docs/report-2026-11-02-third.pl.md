# Trzeci raport Gatecrashera

Archiwum `AutoplayXCom2-20261102-131433-dc8925f9.zip` zawiera trzy sesje, w tym
starsze logi zapasowe. Najnowsza to `2026-11-2_14-8-10-938_890`, rewizja
`mission-report-v3`, `SabotageCC`, poziom 3 (Legenda), wynik `loss`.
Oddział stracił czterech żołnierzy. To kolejna porażka, nie potwierdzenie poprawy.

## Zapisane zachowanie

- 33 zaakceptowane polecenia: 8 ruchów, 14 zwykłych strzałów, 6 overwatch,
  1 hunker i 4 przeładowania. Nie użyto granatu.
- W decyzji 3 żołnierz 422 z jednym AP strzelał z ukrycia z szansą 65%.
  Pozostałe trzy jednostki również były ukryte. Dwie tylne, 416 i 428, miały
  jeszcze po dwa AP, ale nie były przygotowane na wspólne otwarcie.
  Strzał chybił, a po pierwszej turze przeciwnika strzelec już nie żył;
  drugi przedni żołnierz miał 1 HP. Brak przygotowania oddziału jest konkretnym
  problemem planowania, choć sam zapis nie dowodzi, że inna kolejność wygra misję.
- Później wybrano też strzały 26–30%. Nie jest prawdą, że mod w ogóle pomija
  overwatch lub hunker: oba występują w tym raporcie. Polecenie overwatch nie
  gwarantuje jednak strzału reakcyjnego ani dobrego trafienia.
- Planer granatu odnotował 49 sprawdzeń dostępnej obsługiwanej zdolności
  i 188 ocen punktów: 167 odrzuceń zasięgu, 3 trajektorii, 11 bezpieczeństwa
  wybuchu, 3 listy celów i 4 wartości ataku. Żaden punkt nie został przyjęty.
  To liczniki ocen, często powtarzanych w kolejnych decyzjach.
- W decyzjach 22/23 bezpieczny kandydat obejmował pojedynczego żołnierza ADVENT
  z 4 HP. Frag przewidywał 3–4 obrażenia. Dotychczasowa reguła odrzucała go,
  bo nie gwarantował zabicia minimalnym rzutem. Dostępny zwykły strzał miał
  około 30% szansy trafienia. Ta reguła była nadmiernie zachowawcza.
- Odrzucenia przez niebezpieczną scenerię i chronione jednostki są osobnym
  problemem od oceny wartości granatu. Nie usunięto tych zabezpieczeń.

## Wprowadzone zmiany

Rewizja `mission-report-v4` dodaje ograniczone przygotowanie zasadzki: zachowuje
strzelca otwierającego, a innym proponuje bezpieczniejszą pozycję z linią ostrzału
i legalny overwatch. Budżet przygotowań zapobiega niekończącemu się odkładaniu
ataku. To pierwsza realizacja funkcji wcześniej wymienionej w „Granicach wersji”.

Granat na pojedynczy cel może przejść ocenę przy wyraźnej przewadze nad zwykłym
strzałem i dużych obrażeniach z szansą zabicia albo sprawdzonym dobiciu sojusznika.
Log zapisuje teraz również liczniki tych okazji i ostatni podgląd obrażeń/HP.
[Opis reguł, wykorzystania natywnego AI i ograniczeń](native-ai-and-ambush.pl.md).

Testy numeryczne i kontrola interfejsów SDK przeszły w środowisku Linux.
Nowa kompilacja Windows i wynik misji nie są jeszcze potwierdzone.
Pobierz aktualny `main`, zbuduj na zachowanym SDK bez `-BuildBase`, jeśli baza
jest gotowa, i zainstaluj nowy `dist\AutoplayXCom2.zip`. Po próbie zbierz
[raport misji](mission-recording.pl.md). Najbardziej użyteczny będzie również
osobny zapis sprzed pierwszego ataku, pozwalający powtórzyć ten sam scenariusz.
