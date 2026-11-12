# Eksperyment #46 — natywne ataki na potwierdzony przekaźnik

Baza v25: `eae4db165f679d6cac56d6e207900106c4ed3f55`.
Wariant integracji: `mission-report-v26`. Windows WOTC SDK i gra v26:
**NOT RUN**. Dokładny końcowy SHA do kompilacji wskazuje LEAD w #4.

## Problem i dowód

[Raport v25](report-2026-11-12-v25.pl.md) identyfikuje siedem obiektów
`DestroyTransmitter_TempAssets.Archetypes.ARC_IA_PsionicNode`, wszystkie
z `IsObjectiveTarget=true`. W pięciu odnotowanych ofertach cache
DevastatingPunchMP ma AA_Success na obiekt 474, lecz planer nie zapisuje
żadnej kandydatury tego celu. Nie oznacza to pięciu gwarantowanych okazji
po wszystkich kontrolach ścieżki i w chwili właściwego dispatchu.

Źródłową przyczyną pomijania było jawne odrzucenie MovingMelee oraz
ProvidesPath w `ScoreObjectiveAttack`. Natywny SDK obsługuje tu cel
BaseObject, a wersja MP punch dopuszcza non-unit targets bez knockback.

## Poprawka

Wąski wyjątek obejmuje rozpoznany archetyp, misję SabotageTransmitter,
żywy nieusunięty cel, zgodnego wizualizera, natywny objective/hostile
status i widoczność. Akcja musi już pochodzić z cache AA_Success własnej
zdolności. Wyjątek ścieżkowy dotyczy wyłącznie DevastatingPunchMP.
Nie nadaje takiej obsługi zwykłemu DevastatingPunch ani innym propsom.

`HasRequiredMeleePath` przyjmuje BaseObject; kontrę wręcz bada tylko dla
jednostek. Dla obiektu używa tego samego natywnego SelectAttackTile,
budowania ścieżki oraz dotychczasowych kontroli terenu, hazardów,
widoczności, wsparcia i ekspozycji. Controller uruchamia oryginalną
AvailableAction z rzeczywistym target index; nie dodaje AP ani trafień.

Rozpoznany relay dostaje ograniczoną ocenę opartą o natywny podgląd
obrażeń i szansy trafienia, z kosztem ryzyka przemieszczenia. Maksimum
135 pozostaje poniżej gotowej interakcji PlantBomb (200), stabilizacji
(400) i pilnego leczenia (co najmniej 144). Ta ocena i faza dotyczą także
już obsługiwanych ataków dystansowych w rozpoznany node; wcześniejsze
160+damage mogło przewyższać podłożenie X4. Nie przeliczamy tego na
zmyśloną liczbę dodatkowych tur ani punktów.

Natywny wpis MissionObjectives o nazwie PlantBomb i statusie strategy
musi być nieukończony. Ukończenie X4 wyłącza tę preferencję i melee
wyjątek; Sweep jest odrębnym zadaniem, zgodnie z definicją misji.

## Granice ochrony wybuchów

Jeden limit 32 obejmuje DamagedEvents, DestroyedEvents i AnnihilatedEvents.
Każda radialna akcja albo niepełny profil odrzuca atak w relay. To
konserwatywny filtr, nie solver propagacji wybuchu. Nieznany profil
rzeczywistego assetu może nadal zablokować odnotowaną ofertę; nie
obiecywać z góry, że wszystkie pięć będzie teraz wykonane.

Raz na turę istniejący relay_object_candidate zapisuje długości trzech
list oraz radial_event_lists_clear. True oznacza kompletny profil w
limicie, bez radialnej akcji; nie jest dowodem braku każdej możliwej
reakcji skryptu mapy. False przy długości w limicie wskazuje radialną
akcję; przekroczenie limitu pozostaje niepewnością. Nie enumerujemy pól
wybuchu ani nie wywołujemy akcji obiektu w celu podglądu.

## Próba

Po kompilacji końcowego SHA odtworzyć tę samą Blood Killer. Sprawdzić
czy dla rozpoznanego node pojawia się kandydatura i faktyczny
DevastatingPunchMP, czy HP obiektu spada i timer rzeczywiście zyskuje
czas. Przy odmowie zestawić profil radialny i bezpieczną ścieżkę.
Gotowy PlantBomb i pilna pomoc mają zachować pierwszeństwo.

Osobna zmiana #29 szuka właściwego pola interakcji X4. Zniszczenie node
nie oznacza podłożenia bomby ani zwycięstwa. Raportować wykonane cele,
native outcome i pewny końcowy wynik >0. Testy Python i audyt SDK nie
zastępują kompilacji WOTC ani realnej próby. Surowe SDK/logi są prywatne.
