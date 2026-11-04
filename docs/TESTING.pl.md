# Testy odbiorcze

Najnowszy [raport v12](report-2026-11-04-v12-enemies.pl.md): `SabotageCC`,
trudność 3, **FAIL** w turze 8, 40 przyjętych rozkazów i zero odrzuceń.
Start oceny porównawczej od zera: **PASS**. Nowa ocena zagrożeń v13:
kompilacja Windows i próba w grze **NIEURUCHOMIONE**.
[Mechaniki i scenariusze v13](enemy-knowledge-v13.pl.md).

Sprawdź różne obrażenia broni przy porównywalnej geometrii, rozpoznane
zdolności kontroli/AoE/wsparcia, zwykłe melee zombie, możliwą kontrę Mutona
oraz nadmierny wzrost ekspozycji podczas przygotowania zasadzki. Nieznane
dane powinny zachować neutralną wagę, a nie usuwać zagrożenie.

Profil punktacji v2 pozostaje bez zmian: `~0/—` na początku zwykłej misji,
pierwsza rana −1000, potwierdzona strata −5000. Wykrwawienie nie udaje śmierci,
leczenie nie zwraca kary, a F8 nie zeruje oceny.

Wcześniejszy materiał to [ponowna próba GasStation na v9](report-2026-11-03-legacy-v9.pl.md):
Dowódca, **FAIL** w turze 7, wynik gry **−10000** przy maksymalnej puli 46000.
Podejście i stabilizacja snajpera: **PASS**. Legalny pickup łupu: **NIEZAREJESTROWANY**.
Ten sam raport zawiera zwycięstwo v8 w `SabotageCC` na trudności 3.
Wcześniejsze zwycięstwo v8 w pierwszej misji Legacy pozostaje osobną próbą;
Cemetery nadal nie ma udokumentowanej próby autoplaya.
V10 działało w zwykłej niepunktowanej misji. Wyświetlanie liczb Legacy
oraz nowe mechaniki v13 nadal wymagają kompilacji Windows i próby w grze.
[Instrukcja Legacy](legacy-test.pl.md) · [Licznik v12](score-display-v10.pl.md).

Dotychczasowy wynik zgłoszony przez użytkownika: **PASS** — mod wydaje rozkazy;
**PASS** — pierwsza misja Legacy na v8; **FAIL** — dotychczasowe próby
Gatecrashera. Dawna paczka 0.1.0 alpha miała blokadę HUD-u. Wynik jednej misji
nie potwierdza pełnej obsługi wszystkich etapów ani innych rodzajów misji.
[Scenariusze taktyczne i kompilacja z zachowanym SDK](tactics-update.pl.md).

Nowe próby powinny korzystać z wersji zawierającej [rejestr misji](mission-recording.pl.md).
Sprawdź słaby strzał kontra overwatch, ranną jednostkę pod ostrzałem kontra
hunker, gaszenie Burning oraz ochronę Aid Protocol. Po porażce zachowaj raport
ZIP z `Diagnostics\Collect-MissionRecording.ps1` i poziom trudności. Test
rejestratora wymaga prawdziwej gry: obecność testów analizy logów nie potwierdza,
że nowy kod skompilował się i zarejestrował rzeczywistą misję.

Rewizja `mission-report-v4`: z zapisu sprzed pierwszego ataku sprawdź, czy
przedni strzelec zachowuje akcję, a pozostali ustawiają się i włączają overwatch
przed ujawnieniem oddziału. Sprawdź także brak bezpiecznej trasy, brak dostępnego
overwatch i wyczerpany budżet przygotowań: atak musi móc nastąpić bez zapętlenia.
Porównaj bezpieczny Frag 3–4 przeciw 4 HP ze strzałem około 30%, potem z dobrym
strzałem około 80%; wyjątek dla granatu nie powinien wypierać dobrego strzału
ani omijać kontroli sojuszników i obiektów celu. Prześlij raport również po
zwycięstwie, aby dało się ocenić wynik całej misji.

Rewizja `mission-report-v5`: przy tylnym żołnierzu ponad 8 pól od strzelca
otwierającego i poza zasięgiem wzroku celu sprawdź bezpieczny ruch doganiający
przed atakiem. Przybliżenie poniżej 2 pól lub wzrost ryzyka nie powinny wystarczyć.
Po ruchu nadal ma pozostać AP; limit przygotowań nie może powodować pętli.
Sprawdź geometryczną osłonę i LOS w `move_threat_preview`, w tym widoczność
z domyślnej pozycji oraz sytuację wymagającą wychylenia strzelca.
Przy granacie sprawdź, czy `area_target_preview` odpowiada wybranemu punktowi
i późniejszym `result_target`, także przy aktywnym Explosive Falloff.

Wyniki zapisuj osobno: PASS / FAIL / NIEURUCHOMIONY. Kompilacja nie potwierdza działania. Zacznij od osobnego testowego zapisu bez Ironman, z WOTC i wszystkimi oficjalnymi dodatkami, bez innych modów.

## Kompilacja i wejście

1. Zbuduj czyste pakiety SDK i mod; potwierdź brak błędów, świeży `.u` i poprawne polskie znaki po instalacji.
   Ostrzeżenia `Import failed ... property is config` dla `AutoplayXCom2` muszą zniknąć. Osiem znanych ostrzeżeń bibliotek SDK nie zastępuje osobnej kontroli logu moda. Sprawdź, że paczka zawiera `XComAutoplayXCom2.ini` z listami zdolności i `XComGame.ini` z identyfikatorem DLC.
2. Uruchom istniejącą misję z modem. Bez włączenia autoplaya żaden rozkaz nie może zostać wydany.
3. Przyciskiem i F8 włącz/wyłącz automat kilkukrotnie w jednej turze, podczas ruchu, strzału, tury obcych, Lost oraz reakcji władcy. Po wyłączeniu może skończyć się tylko rozpoczęta akcja, bez kolejnej.
4. Escape i pauza: brak nowych rozkazów. Po wczytaniu zapisu, restarcie misji i powrocie z kolejnej misji automat ma być wyłączony, panel pojedynczy.
5. Otwórz menu, wybór celu, ekran przedmiotu i dialog fabularny. Automat nie może sam zamykać nieznanego ekranu ani rozgrywać pod nim tury.
6. Wyłącz i włącz automat przed pojawieniem się jego ekranu hakowania, na ekranie wyboru nagrody oraz w czasie animacji hacka. Powinien wznowić tylko ten sam własny kontekst. Późniejszy ręczny hack tym samym żołnierzem i zdolnością nie może zostać przejęty.

## UI

- V12: nad przyciskiem widoczne `punkty/maksimum`, z wielkością czcionki
  przycisku. Sprawdź odświeżanie przy OFF, po zwinięciu przycisku i po wczytaniu
  zapisu ze środka misji. W kolejnym etapie Legacy wynik nie obejmuje wcześniejszych
  misji, a maksimum nie maleje po zabiciach i stratach. Ujemny wynik ma zachować
  minus. W v12 zwykła misja bez punktacji pokazuje `~wartość/—`; natywny
  wynik bez maksimum daje `wartość/—`. Pole przepuszcza kliknięcia mapy.
- W zwykłej turze XCOM z dostępnymi akcjami włącz autoplay. Nakładka tury i licznik celu misji (`UITurnOverlay`, `UISpecialMissionHUD`) nie mogą powodować stałej pauzy; automat powinien wydać legalny rozkaz.
- Sprawdź rzeczywiste menu, dialog, sekwencję blokującą sterowanie i ręczne celowanie. Nowe rozkazy mają czekać; po zamknięciu menu lub anulowaniu celowania automat może wznowić pracę. Ekrany znajdujące się pod HUD-em nie powinny samodzielnie powodować pauzy.
- Przy utrzymującej się blokadzie sprawdź status i wpisy `AutoplayXCom2` w `Launch.log`. Log powinien podawać przyczynę zmiany stanu i dane ekranu, bez powtarzania identycznego wpisu w każdej klatce.
- 1920×1080, 2560×1440, ultrawide i różne skale UI: przycisk czytelny, znacznik w obrębie ekranu.
- Wszystkie stockowe elementy HUD, w tym ewakuacja, pasek umiejętności, lista przeciwników, podgląd Wybranego i wskaźniki celów: sprawdzić kolizje i poprawić domyślne położenie, jeśli wystąpią.
- Wskaźnik pozostaje widoczny i reaguje na hover; wygaszony przycisk nie przechwytuje kliknięć pola bitwy; najechanie i przejście ze znacznika na przycisk nie powoduje migotania.
- Włączony znacznik zielony, wyłączony niebieski; statusy i skrót czytelne w PL/EN.

## Reguły walki

- V9 — wykrwawienie: ratownik z rzeczywistym ładunkiem i AP powinien podejść
  bezpieczną znaną trasą, zachować koszt stabilizacji i użyć jej dopiero przy
  legalnym celu. Sprawdź brak ładunku, ostatnią turę wykrwawiania, niedostępną
  trasę, przeszkodę przy pacjencie i zagrożonego rannego ratownika. Żołnierz
  ustabilizowany nie powinien pozostawać celem ponownej stabilizacji.
- V9 — łup: sprawdź darmową natywną akcję i automatyczny pickup po ruchu,
  upływ terminu łupu, brak LOS, wsparcie i zagrożenia na całej trasie. Widoczny
  przeciwnik, pamiętany niedawny kontakt, wykrwawienie w oddziale, ewakuacja,
  gotowy cel albo aktywny licznik misji powinny blokować wycieczkę po łup.
- Ranger, Specialist, Grenadier, Sharpshooter, Psi Operative, Reaper, Skirmisher, Templar, SPARK; brak amunicji, leczenie, wykrwawienie, melee, darmowe akcje i Lost headshot.
- Weryfikacja każdej domyślnej nazwy umiejętności, ograniczeń ładunków, cooldownów, trafień, pancerza i osłon. Brak strzałów do ukrytych wrogów i VIP-a do schwytania.
- Podpalenie/kwas na początku trasy i dalej na trasie: można wyjść z zagrożonego pola, ale nie przechodzić przez kolejne.
- Ruch przez drzwi, różne piętra, drabiny i blokady; prawidłowy koszt AP oraz ruch dołączonego GREMLIN-a. Brak pętli i rozkazów bez AP.
- Włącz automat po ustawieniu ręcznych punktów trasy: stara trasa nie może zostać dołączona do nowej ani do ruchu innego żołnierza. Przy ręcznym celowaniu automat ma czekać na zakończenie lub anulowanie celowania.
- Panika, ogłuszenie, kontrola umysłu, przejęte jednostki: wyłącznie jednostki rzeczywiście należące do lokalnego gracza.
- Żadnych dodatkowych AP, wymuszonego trafienia, odczytu ukrytego rzutu hacka ani sztucznego zwycięstwa.
- Granaty Frag/Alien: skupiona grupa wrogów, sojusznik lub cywil w obszarze, VIP, obiekt celu, zbiornik paliwa na trasie i w wybuchu, piętra nad wybuchem, rzut i granatnik. Faktyczny punkt lądowania i lista trafionych obiektów muszą odpowiadać natywnej trajektorii. Brak przejęcia grafiki trajektorii gracza podczas samej oceny.
- Eksploracja: brak widocznych wrogów, pełna kolejka pól, niedostępny cel dla jednego żołnierza, zmiana tury, zużycie wszystkich AP i przebudowa mapy. Nie może wystąpić nieskończone czekanie ani zniknięcie reszty niezeskanowanych pól po zapełnieniu kolejki.

## Cele i zakończenie misji

Każdy wiersz wymaga pełnego przebiegu od włączenia do prawidłowego zakończenia.
Potwierdzono pierwszą misję Legacy, przy jednym włączeniu i zatrzymaniu dopiero
na końcu; log nie jest pełnym audytem każdego wejścia gracza. Cała drabinka
i pozostałe kategorie nadal wymagają prób, szczególnie późniejsze etapy skryptowane.

| Rodzaj | Wymagane sprawdzenie |
| --- | --- |
| Eliminacja / zaopatrzenie | Zwycięstwo i ostatni niewykryty przeciwnik; eksploracja niezbadanych pól oraz wrogowie przemieszczający się na odwiedzony teren |
| Hakowanie / odzyskanie danych | Podejście, hack, legalny wybór nagrody, animacja, zaliczenie celu, wynik misji |
| Zniszczenie / ochrona urządzenia | Atak na wrogi obiekt oznaczony jako cel i termin; brak ataku na urządzenie do ochrony; sprawdzić metadane poszczególnych typów celów |
| Sabotaż obiektu / Blacksite | Interakcja ładunku / fiolki, istniejąca lub wymagana nowa strefa ewakuacji, cały żywy oddział |
| VIP: ratunek / pojmanie | Uwolnienie/przejęcie, nokaut zamiast zabicia, niesienie, ewakuacja VIP-a i żołnierzy |
| Odwet / obrona cywilów | Ratunek i przeciwnicy; brak zapętlenia na nieaktywnych markerach |
| Skrzynie WOTC | Oznaczanie, terminy, nieczynne i zabrane skrzynie |
| Zasadzka na tajnej operacji | Przejście do ewakuacji i komplet ocalałych |
| Lost and Abandoned / Legacy | Wszystkie etapy i transfer między nimi; samouczek jest obecnie wyłączony |
| Alien Nest / Lost Towers | Przejścia pięter/etapów, boss, interakcje i zakończenie |
| Twierdza Wybranego | Portal, komora, sarkofag, boss i zakończenie |
| Obrona Avengera / finał | Cele na obiektach, etapy skryptowane i faktyczny wynik |

## Punktacja każdej symulacji

Uruchom aktualny analizator dla każdego raportu, także Gatecrashera i innych misji
bez oficjalnych punktów. Sprawdź obecność `game_scoring.comparison` z profilem
`wotc_legacy_observed_v2`, listą składowych i brakujących danych. Jest to wspólna
miara porównawcza oparta na regułach gry; nie dodaje punktów do stanu misji.
Wcześniej podane ręcznie wartości zostały zastąpione regułami odczytanymi z gry.
V2 zaczyna od zera; baza +6000 na kwalifikowanego żołnierza w v1 została
usunięta jako niepoparte założenie. Archiwalny v1 zachowujemy osobno.
Nie porównuj sum obu profili bez przeliczenia.

Przypadki analizy: pierwsza rana kontra ponowne obrażenia i leczenie, śmierć
kontra wykrwawienie, potwierdzone fabularne wyłączenie, przeciwnik przejęty
kontrolą umysłu, przeciwnik przywołany i z posiłków, opcjonalny cel, ratunek
cywila, późne włączenie F8 i urwany log. Brak danych nie może dawać pozornie
pełnego wyniku ani zaliczać wszystkich celów na podstawie zwycięstwa.

### Oficjalny wynik Legacy

Przy każdej misji zapisuj osobno: wynik, numer etapu, tury, zgony, wyłączenia
i rany, oficjalny wynik punktowy misji oraz skumulowany, ewentualne restarty
i ręczne działania. Medal zapisuj, gdy został faktycznie przyznany; SDK
porównuje skumulowany wynik z progami po zakończeniu całej drabinki.

Punkty zależą m.in. od celów, przeciwników, tur, obrażeń i przeżycia oddziału.
Leczenie nie odtwarza utraconej premii za brak obrażeń. Fabularna jednostka
pozostająca żywa po wyłączeniu może ponieść karę punktową jak za utratę.
Nie należy odtwarzać wyniku tylko z końcowego HP i liczby zabitych.

V9 zapisuje odczyty `game_score.cumulative_score` tylko dla właściwego etapu.
`recording_delta` obejmuje okres od pierwszego do ostatniego odczytu, nie
gwarantuje punktów całej misji. Sprawdź przejście do kolejnego etapu: nie wolno
przypisać jego wyniku poprzedniej misji. Końcowe premie po zamknięciu rejestracji
mogą wymagać porównania z ekranem podsumowania.

`score` w `APXREC` oznacza wewnętrzną ocenę rozkazu. `MaxScore` w tabelach
`XCom_Challenge` oznacza początkową maksymalną pulę. Żadne z tych pól nie jest
potwierdzeniem zdobytej punktacji. Przy braku oficjalnej liczby wpisuj
**NIEZAREJESTROWANY**, bez wyliczania medalu z przybliżeń.

## Warunki awaryjne

Brak planu ma zatrzymać automat, a nie przepuszczać dowolnie wiele tur. Odrzucona akcja zatrzymuje go bez pętli ponawiania. Limit działań zabezpiecza nietypowe darmowe zdolności. Wyjście z misji usuwa aktora kontrolera i odnośniki do ekranów. Rozgrywka multiplayer, replay i samouczek mają odrzucić włączenie.
