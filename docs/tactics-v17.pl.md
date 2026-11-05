# V17 — ataki Berserkera i ochrona przejętych sojuszników

Rewizja `mission-report-v17` integruje dwa tematy pomocnika po przeglądzie
prowadzącego: [PR #7](https://github.com/HeisenbergC29/autoplay-xcom2/pull/7)
i [PR #9](https://github.com/HeisenbergC29/autoplay-xcom2/pull/9).
To aktualizacja źródeł do kompilacji przez użytkownika. Kompilacja Windows
WOTC SDK i próba v17 w grze pozostają **NIEURUCHOMIONE**; stara paczka
binarna w `release` nie zawiera tych zmian.

## Berserker sterowany przez gracza

`DevastatingPunch` oraz `DevastatingPunchMP` dołączają do listy obsługiwanych
ataków. Druga nazwa jest także używana przez wariant jednostki, który może
wystąpić pod kontrolą gracza w scenariuszu; nie oznacza obsługi rozgrywki
wieloosobowej przez mod.

Obie zdolności korzystają ze stockowego `StandardMelee`, `MovingMelee`
i `MeleePath`. SDK definiuje koszt jednego AP z zużyciem pozostałych AP.
Planer rozważa tylko akcję dostępną według gry i widoczny wrogi cel.
Dotychczasowa kontrola kontry, natywnej trasy, zagrożeń na całej trasie,
widoczności i wsparcia oddziału obowiązuje również dla tych ataków.
Samo wpisanie zdolności do konfiguracji nie daje jej jednostce ani nie
zmienia kosztu, zasięgu, obrażeń czy szansy trafienia.

## Własny żołnierz pod kontrolą przeciwnika

Planer nie wybiera odzyskiwalnego członka własnego oddziału jako celu
bezpośredniego ataku. Kontrola obejmuje też dodatkowe cele ataku oraz
ochronę jednostek przy ocenie granatu. Rozpoznanie wymaga aktywnego efektu
`X2Effect_MindControl`, usuwanego przy śmierci źródła, i potwierdzenia,
że jednostka należała do obecnego gracza bezpośrednio przed nałożeniem
tego efektu. Sama obecna wroga przynależność albo nazwa szablonu nie
wystarczają do zakwalifikowania celu.

Odczyt historyczny dotyczy własności obecnie rozważanej jednostki, zgodnie
z mechanizmem przywracania kontroli w SDK. Nie służy wyszukiwaniu ukrytych
przeciwników lub ich pozycji. Gra nadal samodzielnie rozstrzyga usunięcie
efektu i odzyskanie żołnierza. Dotychczasowa premia za szansę zabicia
widocznego kontrolera z rozpoznanymi aktywnymi więziami pozostaje w ocenie
ataku; nie gwarantuje wyboru kontrolera w każdej sytuacji.

## Zachowane mechanizmy i zakres integracji

Obowiązują poprawki v16: odrzucony podgląd granatu prowadzi do ograniczonego
ponownego planowania, a koniec tury jest potwierdzany historią lub zmianą
gracza/tury. Zachowane są limity ponowień, pamięć niejasnego żądania po
OFF/ON, kontrola legalności i ręczne zatrzymanie.
[Szczegóły v16](tactics-v16.pl.md).

Twardy filtr ostatnio odwiedzanych pól z
[PR #11](https://github.com/HeisenbergC29/autoplay-xcom2/pull/11) wymaga
poprawek po przeglądzie i nie wchodzi do v17. Nie należy przypisywać tej
rewizji usunięcia pętli marszu między turami ani nowego planera zasadzek.

Punktacja pozostaje `wotc_legacy_observed_v2`, od zera. Zaliczenie próby
wymaga zwycięstwa i pewnego wyniku bieżącej misji > 0. Niepełny wynik
porównawczy nie potwierdza sukcesu.

## Próby użytkownika

Po zbudowaniu i instalacji sprawdź `revision=mission-report-v17` w logu.
Na osobnym zapisie skontroluj:

1. Berserkera pod kontrolą gracza: legalny cios powinien być kandydatem,
   a zablokowana trasa, niebezpieczne pole lub cel z kontrą nadal mogą go
   wykluczyć. Po wykonaniu porównaj rzeczywisty koszt AP i natywny wynik.
2. Własnego żołnierza przejętego odwracalną kontrolą: atak bezpośredni i
   wybuch nie powinny zostać wybrane przeciw niemu. Sprawdź normalne
   atakowanie pozostałych widocznych wrogów i zabicie widocznego źródła,
   jeśli gra daje taką możliwość. Zachowaj zapis i raport z aktywnym efektem.
3. Ponowną kontrolę granatu i potwierdzanie końca tury według scenariuszy
   v16. Brak konkretnej okazji w danej misji oznacza **NIEURUCHOMIONY**
   dla tej próby, a nie PASS.
4. Pełną misję: wynik gry, końcowe punkty tej misji, rany, straty i ręczne
   działania. [Przebieg i zbieranie raportu](legacy-test.pl.md).

## Pochodzenie i weryfikacja

Porty pochodzą z repozytorium pomocnika
[xcom2-autoplay-alternative](https://github.com/HeisenbergC29/xcom2-autoplay-alternative):
ataki Berserkera z
[`92157d6`](https://github.com/HeisenbergC29/xcom2-autoplay-alternative/commit/92157d6acd325f2ed601d406cc579d220c1de25d),
ochrona kontrolowanego sojusznika z
[`e43b56b`](https://github.com/HeisenbergC29/xcom2-autoplay-alternative/commit/e43b56b85eaf9f31358cd48e51fe6a9b5ac12389).
Przeniesiono te tematy osobno na wspólną bazę, zachowując poprawki v16.

Końcowe wyniki kontroli automatycznych integracji są zapisywane w
[audycie SDK](SDK-AUDIT.pl.md) i [stanie projektu](PROJECT-STATE.pl.md).
Testy źródłowe i kontrakty SDK nie uruchamiają silnika ani nie potwierdzają
skuteczności v17 w pełnej misji.
