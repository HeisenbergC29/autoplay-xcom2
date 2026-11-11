# Eksperyment #38a — geometria chronionych obiektów przy pustym obrysie

Pierwotna baza v23: `64c28e76b035bcda92a0ecc902f38ed5c889f88e`.
PR #45 przygotowuje LEAD na podstawie gałęzi HELPER-a
`helper/38-native-launcher-objective-geometry`. Końcowy wariant do
kompilacji wskazuje [issue #4](https://github.com/HeisenbergC29/autoplay-xcom2/issues/4).
Jest częścią przygotowywanego v24 razem z #31 / PR #44.
Windows WOTC SDK i gra: **NOT RUN**.

## Dowód z v23

GasStation zakończyło się porażką i natywnym końcowym **−10600**.
Granatnik miał 13 kontroli `LaunchGrenade` z `AA_Success` i 11
z `AA_CannotAfford_ActionPoints`. Nie były to wykonane ataki.
`ThrowGrenade` z `AA_WeaponIncompatible` u granatnika nie jest błędem.

Sprawdzono 355 centrów: 262 odrzucenia zasięgu, 2 trajektorii,
91 bezpieczeństwa wybuchu, zero zaakceptowanych. Dziesięć podsumowań
skanów miało `objective_near_blast / empty_footprint`. Nie wyjaśnia to
wszystkich odmów i nie dowodzi, że wszystkie te miejsca były bezpieczne.
[Pełny wyciąg](report-2026-11-11-v23.pl.md).

## Zachowanie po poprawce LEAD

`FootprintNearImpact` najpierw zachowuje natywny niepusty obrys.
Przy jego braku:

- Jednostka używa `GetVisibilityForLocation` i pełnych natywnych pól
  zajmowanych przez jej `UnitSize`, zamiast pojedynczej kotwicy.
- Obiekt destrukcyjny wymaga rzeczywistego wizualizera z pasującym
  `ObjectID`. `GetComponentsBoundingBox` dostarcza granice komponentów
  kolizyjnych, a iteracja `AllOwnedComponents` dołącza aktualne bounds
  wszystkich właściwych meshy oraz komponentów kolizyjnych. To obejmuje
  niekolizyjne `AttachedMesh1/2` obiektów interaktywnych, które sam
  domyślny ActorBox mógłby pominąć.
- Wymagane są poprawne, skończone, niepuste bounds i zgodny właściciel,
  przyłączenie oraz brak oczekującego reattach/update transform. Jawnie
  wskazane główne i dołączone meshe muszą wystąpić w zebranych granicach.
  Brak, usunięty stan, nieznany typ mesha, nieaktualna geometria albo
  przekroczenie 64 komponentów nadal odrzucają kandydaturę.

Odległość do prostokąta XY bada najbliższy punkt rzeczywistych granic,
z dotychczasowym promieniem bezpieczeństwa. Z nadal pominiętym Z chroni
również pionową kolumnę, np. podłogę pod obiektem. Duży albo przesunięty
obiekt jest chroniony także daleko od kotwicy `TileLocation`.
Pierwotny fallback HELPER-a z dwoma dodatkowymi polami został zastąpiony:
stały margines nie wyznacza granic dowolnego celu.

Limit 64 ogranicza naszą iterację komponentów; nie jest dowodem stałego
czasu natywnego `GetComponentsBoundingBox`. Nie odświeżamy ani nie
przemieszczamy wizualizera, komponentów lub stanu historii do podglądu.
Niepewna geometria pozostaje blokadą, więc poprawka nie gwarantuje
odblokowania każdego dotychczas odrzuconego rzutu.

## Zachowane ograniczenia i próba

Natywne zdolności, AP, właściciel, zasięg, trajektoria, ponowna walidacja
ataku i ochrona sojuszników, cywilów, kontrolowanych żołnierzy oraz celów
misji pozostają. `HasDangerousScenery` nadal odrzuca nieocenione wybuchy
wtórne. **#38b — ofensywny solver reakcji łańcuchowej — nie jest wdrożony.**
Nie zakładać, że pojedyncze trafienie na pewno wysadzi samochód.

Testy `test_grenade_objective_fallback.py` wykonują matematykę faktycznego
helpera UC dla dużego przesuniętego obiektu, braku/niepoprawności granic,
styczności promienia i pionowej kolumny; dodatkowo kontrolują powiązanie
z API SDK i diagnostyką. Zielone testy nie potwierdzają runtime bounds
w Windows. Prywatne źródła SDK nie są publikowane.

Po kompilacji końcowego SHA odtworzyć ten sam zapis GasStation. Sprawdzić
powody odmów i nowe `blast_blocker_geometry`, faktycznie wybrany i wykonany
`LaunchGrenade`, obrażenia oraz zachowanie chronionych obiektów. Sam wzrost
liczby użytych granatów nie zalicza misji: wymagane jest zwycięstwo i znany
wynik końcowy >0. Defensywna ocena osłon z PR #44 jest osobną zmianą;
porównanie całego v24 do v23 nie izoluje wpływu samej geometrii.
