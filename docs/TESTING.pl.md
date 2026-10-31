# Testy odbiorcze — jeszcze niewykonane w grze

Wyniki zapisuj osobno: PASS / FAIL / NIEURUCHOMIONY. Kompilacja nie potwierdza działania. Zacznij od osobnego testowego zapisu bez Ironman, z WOTC i wszystkimi oficjalnymi dodatkami; następnie osobno sprawdź zestaw pozostałych modów.

## Kompilacja i wejście

1. Zbuduj czyste pakiety SDK i mod; potwierdź brak błędów, świeży `.u` i poprawne polskie znaki po instalacji.
2. Uruchom istniejącą misję z modem. Bez włączenia autoplaya żaden rozkaz nie może zostać wydany.
3. Przyciskiem i F8 włącz/wyłącz automat kilkukrotnie w jednej turze, podczas ruchu, strzału, tury obcych, Lost oraz reakcji władcy. Po wyłączeniu może skończyć się tylko rozpoczęta akcja, bez kolejnej.
4. Escape i pauza: brak nowych rozkazów. Po wczytaniu zapisu, restarcie misji i powrocie z kolejnej misji automat ma być wyłączony, panel pojedynczy.
5. Otwórz menu, wybór celu, ekran przedmiotu i dialog fabularny. Automat nie może sam zamykać nieznanego ekranu ani rozgrywać pod nim tury.

## UI

- 1920×1080, 2560×1440, ultrawide i różne skale UI: przycisk czytelny, znacznik w obrębie ekranu.
- Wszystkie stockowe elementy HUD, w tym ewakuacja, pasek umiejętności, lista przeciwników, podgląd Wybranego i wskaźniki celów: sprawdzić kolizje i poprawić domyślne położenie, jeśli wystąpią.
- Wskaźnik pozostaje widoczny i reaguje na hover; wygaszony przycisk nie przechwytuje kliknięć pola bitwy; najechanie i przejście ze znacznika na przycisk nie powoduje migotania.
- Włączony znacznik zielony, wyłączony niebieski; statusy i skrót czytelne w PL/EN.

## Reguły walki

- Ranger, Specialist, Grenadier, Sharpshooter, Psi Operative, Reaper, Skirmisher, Templar, SPARK; brak amunicji, leczenie, wykrwawienie, melee, darmowe akcje i Lost headshot.
- Weryfikacja każdej domyślnej nazwy umiejętności, ograniczeń ładunków, cooldownów, trafień, pancerza i osłon. Brak strzałów do ukrytych wrogów i VIP-a do schwytania.
- Podpalenie/kwas na początku trasy i dalej na trasie: można wyjść z zagrożonego pola, ale nie przechodzić przez kolejne.
- Ruch przez drzwi, różne piętra, drabiny i blokady; prawidłowy koszt AP oraz ruch dołączonego GREMLIN-a. Brak pętli i rozkazów bez AP.
- Panika, ogłuszenie, kontrola umysłu, przejęte jednostki: wyłącznie jednostki rzeczywiście należące do lokalnego gracza.
- Żadnych dodatkowych AP, wymuszonego trafienia, odczytu ukrytego rzutu hacka ani sztucznego zwycięstwa.

## Cele i zakończenie misji

Każdy wiersz wymaga pełnego przebiegu od włączenia do prawidłowego zakończenia, bez ręcznej akcji. Obecna wersja **nie ma potwierdzenia żadnego z nich**; szczególnie późniejsze skryptowane etapy wymagają implementacji i prób.

| Rodzaj | Wymagane sprawdzenie |
| --- | --- |
| Eliminacja / zaopatrzenie | Zwycięstwo i ostatni niewykryty przeciwnik; obecnie brak pełnego przeszukiwania mapy |
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
