# Integracja v37 — 14 listopada 2026

Wspólna paczka obejmuje #83/v36 (runtime observed_v3) i #84/v37
(potwierdzone źródło kontroli jako cel bezpiecznego ruchu Sweep).
Zachowuje wcześniejsze X4, native-ready opening i highground z v35.
Nie wymaga osobnej kompilacji pośredniej v36. Dokładny commit/ZIP,
wykonane kontrole i oczekiwany raport użytkownika są w #4.

## Wdrożone naliczanie

Nowy APX_LegacyObservedV3 czyta publiczne stock class defaults
config(Ladder): tabele enemy/objective i soldier, w tym prawdziwy
czteropolowy klucz celu. W misjach bez natywnego licznika nalicza
zaobserwowane zwykłe/spawned zabicia oraz kwalifikowane własne rany,
straty, jawnie ukończone cele i ratunek cywilów. Nowy profil to
wotc_legacy_config_observed_v3_partial. Stary observed_v2 pozostaje
niezmieniony do odtwarzania historycznych raportów.

LEAD poprawił lukę kwalifikacji: niezweryfikowany retained start nie
dowodzi ordinary encounter, a pierwsza widoczna aktualna własność nie
określa pierwotnej drużyny. Kwalifikacja korzysta ze sprawdzonego kontekstu
tactical start i dostępnych dowodów początkowej własności; dawny XCOM
nie staje się nagrodą enemy kill. Ujemne konfiguracje potrąceń nie
tworzą dodatnich premii. Zbyt długa tabela nie jest po cichu obcinana
z fallbackiem do złej stawki. Jednorazowy log Legacy observed rates
podaje długości tabel i flagi start/coverage, bez dumpowania danych.

Natywne punkty Ladder/Challenge nadal mają pierwszeństwo. Guardy trwającej
latent submission i brak crashującego GetTotalScore pozostają. Nowy
licznik nie wywołuje award/mutacji historii ani nie zmienia zasad gry.

V3 jest **częściowy**. Nieznane późne jednostki nie otrzymują domniemanej
stawki ordinary. Reinforcement/disabled/restart/bonusy oraz odtworzenie
objective/civilian po load są dalszą pracą. Samo podobieństwo stawek
nie stanowi pełnego dowodu natywnej kwalifikacji i końcowej sumy.
HUD zachowuje ~ oraz nie wymyśla maksimum; recorder zapisuje profil,
rate_source i brak potwierdzenia parity/coverage.

DefaultObjectiveScoring w dostarczonej konfiguracji wynosi0; SabotageCC
nie ma własnego wpisu. V3 nie dopisze tam dawnych5000 za każdy cel.
Zmiana odzwierciedla tabelę, nie jest próbą poprawiania benchmarku.
Zasadę użytkownika zachowujemy: wynik moda ze zgodnymi regułami może być
oficjalny; pewna suma końcowa wymaga też kompletności zdarzeń.
[Zakres licznika](experiment-79-runtime-legacy-v36.pl.md),
[zasada punktacji](scoring-policy.pl.md).

## Ruch do potwierdzonego źródła kontroli

Wyłącznie dla BerserkerMP/SabotageTransmitter po native PlantBomb,
przy HP>=40% i bez wykrwawiającego się członka drużyny, planer rozważa
aktualnie widocznego wrogiego sprawcę aktywnego MindControl na dawnym
XCOM, z potwierdzonym bRemoveWhenSourceDies i linkiem source/target.
Sam szablon Priest lub dawne eHit_Success nie wystarczają.

Wstępny PR zmieniał głównie seed ClosestTile: ogólne combat PositionScore
ignorowało cel ruchu, a routine route wyłączała rzeczywista widoczność.
LEAD dodał scoped flagę i prawdziwy, ograniczony bonus postępu do źródła:
2 punkty utility na pole, maksymalnie12. Brak bonusu przy AP<2,
zwiększeniu ekspozycji, braku postępu lub nieaktywnej fladze.

Nie jest to dodatkowy Aim lub legalny przyszły atak. Routine route gate,
IsUsefulReposition, ostatni AP, pełna native ścieżka, hazardy, wsparcie,
koszt utraconego ataku i ochrona odzyskiwalnych sojuszników pozostają.
Źródło/efekt jest sprawdzane od nowa przy kolejnej decyzji. Zmiana nie
gwarantuje osiągalności, zabicia kontrolera ani przeżycia Sweep.
[Zakres Sweep](experiment-56-sweep-control-source-v37.pl.md).

## Walidacja i test użytkownika

Kontrole źródeł, SDK, testów i CI są zapisywane przez LEAD z dokładną
głową w rozmowach PR. Zielone kontrole nie są natywnym make lub misją.
**Windows WOTC make v37 i gra v37: NOT RUN.** Osobnego nowego raportu
v35 także nie dostarczono. Ostatni potwierdzony raport v32 zawiera
GasStation WIN/+6200, assisted SabotageCC, Cemetery LOSS/missionunknown
i Blood Killer LOSS/+7100.

Użytkownik kompiluje jedną końcową paczkę v37. W SabotageCC sprawdza
samodzielne X4, profil ~ i log Legacy observed rates z realnym config.
W Blood Killer: X4/relay, nowe źródło Sweep, rzeczywisty ruch, efekt
po śmierci kontrolera, odzyskanie sojusznika/straty i native end/score.
Legacy nadal ma pokazywać natywny wynik. Zapis/load nie może udawać
pełnej coverage ani dopisywać punktów za niepotwierdzone zdarzenia.
Log kompilacji i raport przekazać obu agentom. Kryterium projektu nadal:
autonomiczne native victory i pewne końcowe punkty>0.
Surowe SDK, INI i raporty pozostają prywatne.
