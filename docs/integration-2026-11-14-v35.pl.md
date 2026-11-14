# Integracja v35 — 14 listopada 2026

LEAD przejrzał trzy PR-y HELPERA. Runtime paczki ma marker
mission-report-v35 i obejmuje kolejne etapy #69/v34 oraz #70/v35.
Niezależny #81 dotyczy tylko narzędzia audytu danych. Nie trzeba
kompilować i testować każdej wersji pośredniej.

## Co zmienia zachowanie

#69 pozwala miękko preferować jeden aktualnie gotowy natywny
DevastatingPunchMP w turach 1–2 Blood Killer, gdy timer>=4, jest
przynajmniej trzech żywych Berserkerów i X4 nie zostało ukończone.
Sprawdza aktualnego właściciela, AA_Success, widoczny wrogi cel,
HP>=55%, wartość oraz zwykłe zabezpieczenia ścieżki melee.
Nowy wyjątek nie rozszerza spekulacyjnego marszu poza dawny dystans,
nie wybiera trasy za inne jednostki i nie obniża relaya.
Licznik rośnie dopiero po przyjęciu właściwej akcji; natywne AP
i konkurencja PlantBomb/ratunku pozostają rozstrzygające.
[Zakres v34](experiment-56-native-strike-v34.pl.md).

#70 uwzględnia stock próg przewagi wysokości i specjalne own BonusZ
w użyteczności stanowiska. Prognoza zwykłego strzału może rozważyć
osiągalne wyższe pole, zachowując native remote LOS/target checks,
niebieski ruch, rezerwę AP, całą trasę, hazardy, wsparcie i ryzyko.
Nowa premia Aim jest estymatą z discount, nie gotowym przyszłym
ShotBreakdown; bieżąca natywna premia nie jest dodawana drugi raz.
EnableElevatedShotForecast=false przywraca poprzedni zakres prognozy.
Istniejące wymaganie wsparcia może nadal blokować pierwszego
żołnierza próbującego wejść na pusty dach.
[Zakres v35](experiment-31-high-ground-v35.pl.md).

Naprawa podejścia do rzeczywistego pola X4 w SabotageCC z #78
pozostaje. Provider punktów i jego latent guards, brak crashującego
GetTotalScore, OFF/pauza oraz ochrona odzyskiwalnych sojuszników
nie zostały zmienione. Brak gwarancji zwycięstwa lub przeżycia Sweep.

## Audyt Legacy i poprawki przeglądu

#81 odczytuje prywatne DefaultLadder.ini i TLE XComLadder.ini,
zachowując źródła/hash i zwracając wyłącznie pochodne podsumowanie.
Na dostarczonych danych: 134 enemy overrides, 116 objective, 20 mission.
Reguły dla Troopera/Priesta i wybranego TerrorBar różnią się od v2.

LEAD wykrył i poprawił ciche pomijanie operatorów/config case,
nieprawidłowe porównania FName, typy identyfikatorów i brak separatorów.
Parser odrzuca nieobsługiwany podzbiór zamiast raportować stare stawki.
16 focused testów, w tym prawdziwe INI, PASS; wynik audytu tych danych
jest bajtowo identyczny przed i po poprawce.
To **etap A**, nie wdrożenie pełnej oficjalnej punktacji.
APX_ComparisonScore i wotc_legacy_observed_v2 pozostają bez zmian.
Pełny runtime parytet i kompletność wczytań/historii są dalszym #79.
[Audyt](experiment-79-legacy-rate-audit.pl.md),
[zasada oficjalności](scoring-policy.pl.md).

## Przegląd i potwierdzenie

Przejrzane głowy:

- #69: a82c2e558fdd01c5fea7f7c1581679a66d6b92f1;
- #70: 87936b8748acd6f7f20173abd0cfaf6b849fa572,
  drzewo identyczne z niezależnie przejrzanym cbbd8c9;
- #81: bb400d667329dead41166c724dc30ce49d7a8c67,
  z poprawką parsera 5d6537150b642baf84d5309b856a91a2acf133dd.

Wspólne źródła #69+#70 przeszły 757 prywatnych testów bez pominięć;
po dodaniu poprawionego #81 całe drzewo przeszło 773 testy, bez pominięć.
Audyt referencji SDK 24 klasy/31 nazw PASS. Publiczne CI ma pominięcia
prywatnych wejść i nie zastępuje ich ani kompilatora Windows.
Końcowe wyniki integracji i dokładny ZIP/commit są w #4 i rozmowie PR.

**Windows WOTC make v35 i test gry v35: NOT RUN.** Nie dostarczono
też jeszcze osobnego raportu gry v33. Ostatnia zweryfikowana próba
v32 ma GasStation WIN/+6200, wspomagane ręczne X4 w SabotageCC,
Cemetery LOSS/mission score unknown i Blood Killer LOSS/+7100.
[Raport v32](report-2026-11-13-v32.pl.md).

## Następny krok użytkownika

1. Skompilować i wdrożyć jedną końcową paczkę v35 wskazaną w #4.
   Zakomentowane przez użytkownika SDK Day0 powinno zostać zweryfikowane
   tym samym buildem; ostatni dostarczony log nadal miał0/1.
2. SabotageCC: po neutralizacji native plant anchor i autoplay chosen
   Interact_PlantBomb, bez ręcznego ruchu lub X4, następnie native end.
3. Blood Killer: native_strike_ready, pierwszy wybrany atak, timer,
   relay/X4 do terminu, źródła kontroli umysłu i przeżycie Sweep.
4. GasStation: rzeczywiste ruchy na wyższe stanowiska i native szansa
   oraz trafienia po ruchu, formacja/straty/końcowy wynik.
5. Przekazać log kompilacji i raport obu agentom. Kryterium nadal:
   autonomiczne native victory i pewne końcowe punkty>0.

Surowe SDK, INI i raporty pozostają prywatne. Zmiany dokumentacji
nie nadają oficjalności przybliżonemu v2 ani nie poprawiają wyniku misji.
