# Testy odbiorcze

Najnowszy wynik zgłoszony przez użytkownika: **PASS** — mod wydaje rozkazy;
**FAIL** — przegrywa Gatecrasher na Legendzie i Dowódcy. Dawna paczka 0.1.0 alpha
miała blokadę HUD-u. Bieżące zmiany taktyczne mają testy numerycznych heurystyk,
ale ich kompilacja i próby w grze pozostają **NIEURUCHOMIONE**.
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

- W zwykłej turze XCOM z dostępnymi akcjami włącz autoplay. Nakładka tury i licznik celu misji (`UITurnOverlay`, `UISpecialMissionHUD`) nie mogą powodować stałej pauzy; automat powinien wydać legalny rozkaz.
- Sprawdź rzeczywiste menu, dialog, sekwencję blokującą sterowanie i ręczne celowanie. Nowe rozkazy mają czekać; po zamknięciu menu lub anulowaniu celowania automat może wznowić pracę. Ekrany znajdujące się pod HUD-em nie powinny samodzielnie powodować pauzy.
- Przy utrzymującej się blokadzie sprawdź status i wpisy `AutoplayXCom2` w `Launch.log`. Log powinien podawać przyczynę zmiany stanu i dane ekranu, bez powtarzania identycznego wpisu w każdej klatce.
- 1920×1080, 2560×1440, ultrawide i różne skale UI: przycisk czytelny, znacznik w obrębie ekranu.
- Wszystkie stockowe elementy HUD, w tym ewakuacja, pasek umiejętności, lista przeciwników, podgląd Wybranego i wskaźniki celów: sprawdzić kolizje i poprawić domyślne położenie, jeśli wystąpią.
- Wskaźnik pozostaje widoczny i reaguje na hover; wygaszony przycisk nie przechwytuje kliknięć pola bitwy; najechanie i przejście ze znacznika na przycisk nie powoduje migotania.
- Włączony znacznik zielony, wyłączony niebieski; statusy i skrót czytelne w PL/EN.

## Reguły walki

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

Każdy wiersz wymaga pełnego przebiegu od włączenia do prawidłowego zakończenia, bez ręcznej akcji. Obecna wersja **nie ma potwierdzenia żadnego z nich**; szczególnie późniejsze skryptowane etapy wymagają implementacji i prób.

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

## Warunki awaryjne

Brak planu ma zatrzymać automat, a nie przepuszczać dowolnie wiele tur. Odrzucona akcja zatrzymuje go bez pętli ponawiania. Limit działań zabezpiecza nietypowe darmowe zdolności. Wyjście z misji usuwa aktora kontrolera i odnośniki do ekranów. Rozgrywka multiplayer, replay i samouczek mają odrzucić włączenie.
