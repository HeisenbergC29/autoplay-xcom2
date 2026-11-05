# Wiedza o jednostkach i ocena zagrożeń — v13

V13 łączy audyt definicji SDK z danymi załadowanych szablonów widocznych
przeciwników. Celem jest lepszy wybór celu, pozycji i sposobu ataku.
Nowe decyzje wymagają kompilacji Windows i próby w grze.

[Raport v12](report-2026-11-04-v12-enemies.pl.md) obejmuje porażkę
`SabotageCC` w turze 8 przy trudności 3. Potwierdził `MarkTarget`, `Mindspin`
powodujący panikę oraz zabójczy `StandardMelee` zombie. We wszystkich
dostępnych raportach rozpoznano dziesięć szablonów przeciwników w 17 sesjach.
Ta próbka nie potwierdza jeszcze działania przeciw całej grze.

## Katalog źródeł

[Katalog jednostek](../data/unit-catalog.json) opisuje rejestracje z bazowej
gry, WOTC i oficjalnych dodatków. Zawiera również żołnierzy, cywilów, jednostki
MP i mówców, dlatego liczby rejestracji nie należy traktować jako liczby wrogów.
Metadane obejmują fabryki i odwołania do zdolności, wyposażenia, immunitetów,
cech jednostki oraz drzew AI, z plikami i liniami źródeł.

Audyt objął **253 rejestracje i 253 rozpoznane nazwy** z pięciu dostawców
szablonów, 171 fabryk oraz 208 definicji broni w 196 plikach źródłowych.
Katalog zawiera wszystkie dziesięć szablonów napotkanych dotąd w raportach.
Rozpoznanie nazwy nie oznacza rozwiązania jej konfiguracji ani pokrycia
wszystkich wariantów tworzonych natywnie podczas gry.

Przekazane źródła nie zawierają kompletu INI z liczbowymi statystykami,
zawartością loadoutów i drzewami zachowań. Katalog zachowuje odwołania do
konfiguracji i oznacza nierozwiązane lub warunkowe wartości. Nie wykonuje
natywnego kodu gry, doboru trudności, losowych wariantów ani zmian innych modów.
Pełne źródła SDK nie są publikowane w repozytorium.

Audyt można odtworzyć na lokalnym SDK, wskazując nowy plik wyniku:

```powershell
python .\tools\audit-unit-definitions.py `
  --sdk 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK' `
  --json '.\unit-catalog-local.json'
```

Nazwy typów i ich cechy stanowią wiedzę o grze. Bieżące pozycje ukrytych
przeciwników nie są wejściem do planera.

## Co zmienia się w decyzjach

**Broń i priorytet celu.** Widoczny przeciwnik zadający większe podstawowe
obrażenia może zwiększyć ocenę ekspozycji na danym polu i wartość jego
wyeliminowania. Model czyta załadowany `BaseDamage` broni, w tym procentową
szansę `PlusOne`, oraz celność. Waga ryzyka jest ograniczona do 0,75–1,6;
przy brakujących danych pozostaje neutralna. Te współczynniki są heurystyką,
a nie natywnym prawdopodobieństwem trafienia.

Rozpoznane efekty kontroli, obszarowe style celowania i wsparcie dodatkowo
wpływają na priorytet zabicia. Premia pozostaje ograniczona i zależna od
szansy zabicia. Sama obecność zdolności nie potwierdza jej zasięgu, gotowości
ani zamiaru AI. Geometria osłony i LOS nadal jest oceniana osobno.

**Kontratak przeciw melee.** Planer rozpoznaje zainstalowane
`CounterattackPreparation` lub `Counterattack` i unika zagrożonego ataku
wręcz, gdy cel nie jest jawnie obezwładniony. SDK dopuszcza kontrę również
przeciw inaczej gwarantowanemu trafieniu, więc podgląd 100% nie usuwa tego
ryzyka. Ukryty znacznik wykorzystania kontry w turze nie jest odczytywany.
Reguła jest związana ze zdolnością, a nie samą nazwą Mutona.

**Zwykłe melee zombie.** Poprzedni model rozpoznawał ruchomy atak i stożek,
ale dla zwykłego `StandardMelee` stosował zastępstwo. V13 obsługuje również
pojedynczy cel ograniczony zasięgiem broni. Natywne `GetHitRange` przelicza
z jednostek świata na pola; nie zakłada zerowego `iRange`. Budżet kolejnej
zwykłej tury uwzględnia ruch i następnie koszt ciosu. Jest to możliwy zasięg,
bez gwarancji dostępnej trasy lub przyszłej decyzji wroga.

**Przygotowanie zasadzki.** Ruch uzyskujący linię ognia podlega teraz również
porównaniu z ryzykiem obecnego pola. Dozwolony wzrost jest ograniczony do
większej z wartości: 6 jednostek heurystyki lub 25% bieżącego ryzyka. Ma to
ograniczyć przygotowania pozostawiające odsłonięty oddział po otwarciu ognia.
Raport pokazał wzrosty 24,78 → 55,65 i 44,22 → 80,97; nie dowodził jednak,
że przed ujawnieniem wróg mógł już strzelać.

Wagi broni i zasięgi są zachowywane lokalnie dla niezmienionej listy widocznych
kontaktów podczas wyszukiwania pól. Nie przechodzą jako nieaktualna wiedza
do kolejnych decyzji. Planer nadal korzysta ze zwykłych legalnych akcji gry.

## Następna próba

Sprawdź różne obrażenia broni przy tej samej osłonie, priorytet rozpoznanego
kontrolera lub użytkownika AoE przy porównywalnej szansie zabicia, zwykły cios
zombie i kontrę Mutona. Zweryfikuj również jawnie obezwładniony cel, brak
rozpoznanej broni oraz przygotowanie zasadzki bez bezpiecznej linii ognia.

Wpisy `enemy_knowledge` zapisują broń główną, średnie obrażenia bazowe,
celność, mobilność, pancerz, immunitety i cechy techniczne. Pola `base_*`
pochodzą z załadowanego szablonu: HP, celność, obrona, mobilność, wola, unik,
pancerz, psionika, obrona przed hakowaniem, wykrywanie i trafienia krytyczne.
Nie obejmują wszystkich losowych i aktywnych modyfikatorów jednostki.
Wagi `threat_weight`, `target_threat`, maska `capabilities` i
`melee_counter_possible` pozwalają porównać wiedzę z wybraną decyzją.
Maska ma wartości: kontrola 1, obszar 2, wsparcie 4. Identyczne dane nie są
powtarzane w każdym odczycie. `move_threat_preview.threat_weight` podaje
tę samą wagę dla bieżącego i docelowego pola.

Nowe wpisy umożliwiają zestawienie wiedzy z wybraną pozycją i późniejszym wynikiem. Zapis zdolności
opisuje jej potencjał, a nie odczyt ukrytych AP, amunicji, cooldownu lub AI.
Rzeczywiste trafienia i straty nadal trzeba oceniać na pełnym raporcie.

Rejestr powinien wskazywać `revision=mission-report-v13`. Profil punktacji
porównawczej v2 pozostaje bez zmian i zaczyna od zera.
[Budowanie i zbieranie raportu](legacy-test.pl.md) ·
[Testy odbiorcze](TESTING.pl.md).
