# Licznik punktów nad przyciskiem — v10

V10 dodaje nad przyciskiem „Autoplay” pole `aktualne punkty/maksimum misji`,
np. `0/46000`. Rozmiar czcionki jest odczytywany z przycisku. Pole odświeża
się co 0,25 s także przy wyłączonym autoplay i pozostaje widoczne po schowaniu
przycisku. Nie przechwytuje kliknięć mapy ani nawigacji klawiaturą.
Dotychczasowe położenie przycisku, statusu i znacznika pozostaje takie samo.

## Co oznaczają liczby

- W Legacy licznik pokazuje wkład **bieżącej misji**: aktualny wynik drabinki
  minus wynik przeniesiony do taktycznego stanu początkowego tego etapu.
  Nie zeruje się przy F8 i nie dolicza poprzednich misji po przejściu do
  następnego etapu. Brak pewnego odczytu stanu początkowego daje „—”.
- Maksymalna pula pochodzi z natywnego odczytu używanego przez okno punktacji
  Legacy i jest zachowywana dla tej misji. Nie jest wpisana na stałe ani
  zmniejszana po zabiciach, ranach czy śmierciach.
- W natywnym Challenge Mode wyświetlana jest para wynik/maksimum z funkcji
  używanych przez podsumowanie gry.
- Zgodnie z wyborem użytkownika misje bez natywnej punktacji pokazują „—”.
  Wspólna ocena porównawcza z analizatora raportów nadal działa oddzielnie;
  licznik nie przedstawia jej jako wyniku gry.

Wynik może być ujemny. W [najnowszej próbie v9](report-2026-11-03-legacy-v9.pl.md)
gra rozpoczęła od 0 i zakończyła obserwowany okres na −10000 przy puli 46000.
Odpowiadałoby to `-10000/46000`, bez ograniczania do zera. Ewentualne późniejsze
premie pojawią się dopiero wtedy, gdy gra zaktualizuje wynik.

Odczyt służy prezentacji. Nie przyznaje punktów, nie zmienia przebiegu misji
ani nie dostarcza planerowi informacji o ukrytych przeciwnikach.

## Kompilacja i sprawdzenie

Nowy kod wymaga kompilacji Windows według [instrukcji Legacy](legacy-test.pl.md).
Rejestr uruchomionego autoplaya ma wskazywać `revision=mission-report-v10`.
Sama obecność testów źródeł i kontraktów SDK nie potwierdza działania HUD-u.

Sprawdź:

1. Początek Legacy: licznik przed F8, poprawna pula, zgodna wielkość czcionki.
2. Zmianę wyniku po zabiciu i pierwszej ranie oraz ewentualny wynik ujemny.
3. Stałe maksimum po zabiciach i stratach, także pod koniec misji.
4. Kolejny etap i zapis ze środka misji: bez doliczania poprzedniego etapu
   i bez zerowania po wczytaniu lub przełączeniu autoplaya.
5. Widoczność przy OFF i schowanym przycisku, kliknięcia mapy pod licznikiem,
   różne rozdzielczości i skalę UI.
6. Zwykłą misję bez natywnej punktacji: „—”.

Do raportu dopisz widoczne wartości oraz ewentualną rozbieżność z ekranem gry.
Najnowszy raport potwierdza działanie ratunku v9, lecz GasStation zostało
przegrane; nowy licznik nie jest zmianą taktyki ani dowodem zwycięstwa v10.
