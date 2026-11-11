# Eksperyment #38a — odblokowanie legalnego granatnika bez osłabienia ochrony celów

Baza `main` v23: `64c28e76b035bcda92a0ecc902f38ed5c889f88e`.
Gałąź `helper/38-native-launcher-objective-geometry`, NIE zintegrowana
i jeszcze bez odrębnego PR ze względu na limit trzech aktywnych prac
HELPER (#11, #43, #44). Nie instalować jako gotowej poprawki.

## Potwierdzenie z prywatnego logu v23

`ChallengeAbductionGasStation`: `outcome=loss`, końcowe natywne
punkty **−10 600**. Unit `63486` miała zapisane `LaunchGrenade`:
**13 razy AA_Success, 11 razy AA_CannotAfford_ActionPoints**.
Dla tej jednostki `ThrowGrenade` zgłasza `AA_WeaponIncompatible`,
co nie jest błędem moda. Granatnik był zatem legalnie dostępny
w części decyzji, ale **nie został użyty**.

Planer rozważał łącznie 355 centrów rzutów/wystrzałów z 118
`grenade_scan`. Suma odmów: **262 range, 91 blast**,
**0 accepted**. Dziesięć podsumowań skanu miało jako
ostatni powód `objective_near_blast` wraz z
`blast_blocker_geometry=empty_footprint`. To nie znaczy,
że wszystkie 91 odrzuceń są błędne. Jednocześnie wskazuje
konkretny nadmiernie zachowawczy przypadek: brak aktualnego
wizualnego obrysu dowolnego chronionego obiektu powoduje
globalną odmowę, nawet gdy jego natywny `TileLocation`
znajduje się daleko od celu rzutu.

## Implementacja 38a

W `APX_AreaAttackPlanner.FootprintNearImpact` rozróżnia się teraz:

- natywny widoczny obrys — pełna ochrona po istniejącym promieniu;
- pusty obrys przy znanym, rzeczywistym `XComGameState_Destructible`
  (również `InteractiveObject`) lub `XComGameState_Unit` —
  awaryjna kontrola ich `TileLocation` z **dodatkowymi
  dwoma polami marginesu bezpieczeństwa**;
- nieznana/usunięta lokalizacja, obiekt bez poprawnego
  pola w mapie albo brak stanu — **nadal odmowa**.

Wszystkie wywołania chroniące jednostki, obiekty z
`ObjectiveInfo` i aktywne interaktywne cele przekazują
rzeczywisty obiekt stanu. `AA_Success`, właściciel zdolności,
natywna trajektoria, obszar z obrażeniami, ochrona cywilów,
możliwość rozerwania otoczenia i liczba AP pozostają
niezmienione. Testy kodu: `tests/test_grenade_objective_fallback.py`
oraz zaktualizowane `tests/test_grenade_blocker_diagnostics.py`.
Weryfikacja SDK odbyła się lokalnie na prywatnym
`Development sdk.rar`, bez publikowania zawartości.

## Co dalej

- **38b / scenariusz z samochodem:** `XComDestructibleActor` ma
  natywne `HasRadialDamage()`, `GetRadialDamageTiles` i
  `GetDestroyedDamagePreview`. Użycie tego w ofensywie
  wymaga nie tylko wyceny możliwych obrażeń, ale też
  sprawdzenia sojuszników, cywilów, celów i ewentualnych
  kolejnych eksplozji w tych rzeczywistych polach.
  Obecny kod nadal **odrzuca** `HasDangerousScenery`;
  nie wyłączać tego globalnie i nie zakładać, że jedno
  trafienie na pewno wysadzi samochód.
- **#31a / osłona gracza:** osobny PR #44 ocenia
  niebezpieczne osłony po stronie XCOM i używa tej
  samej natywnej geometrii. Nie mieszać dwóch zmian
  w jednym teście A/B.
- A/B: na tym samym zapisie GasStation sprawdzić, czy
  `LaunchGrenade` zostanie **wybrany i wykonany z
  native AA_Success**. Zbierać `grenade_scan` z
  reasons, wybrany cel, potwierdzone obrażenia i to,
  czy nie ucierpiał żaden chroniony obiekt. Zapisać
  outcome i natywne końcowe punkty misji — sam
  przyrost użycia granatnika nie jest zwycięstwem.

Windows WOTC SDK kompilacja tej gałęzi i gra:
**NIEPRZEPROWADZONE**. Publiczne CI wymaga normalnego
PR do przeglądu LEAD, po zwolnieniu limitu. Nie
przedstawiać tej gałęzi jako zaliczonej misji.
