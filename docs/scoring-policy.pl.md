# Punktacja zgodna z Legacy

Użytkownik doprecyzował 13 listopada 2026:

> Jeżeli system punktacji w autoplay nalicza punkty w taki sam sposób jak
> istniejąca punktacja w legacy to należy to traktować jako oficjalną punktację.

Przyjmujemy tę zasadę również dla misji bez natywnego licznika. Wynik
moda o zweryfikowanej zgodności z regułami Legacy uznajemy za oficjalny.
Nadal zapisujemy źródło wartości: odczyt gry albo obliczenie przez mod.
Do uznania sumy za pewną i końcową potrzebny jest także kompletny zapis
zdarzeń do końca misji. Prawidłowa reguła zastosowana do części danych
nie daje pewnego wyniku całej misji.

Zwycięstwo i punkty >0 pozostają kryterium próby. Wynik dodatni przy
natywnej porażce nie zalicza misji, a ręczne ukończenie celu nie jest
samodzielnym zwycięstwem autoplay. Nie dodajemy początkowych premii,
nie zgadujemy maksimum i nie zmieniamy stawek dla poprawienia wyniku.

## Obecny profil nie spełnia jeszcze warunku

Audyt LEAD i niezależny audyt źródeł wykazały różnice pomiędzy
APX_ComparisonScore / wotc_legacy_observed_v2 a dostarczoną konfiguracją
Legacy. Poniższe przypadki dotyczą zwykłego przeciwnika, a późna tura
pozwala porównać minima bez rozstrzygania granicznego turn offset.

| Przypadek | Obecny licznik moda | Dostarczone reguły Legacy |
| --- | ---: | ---: |
| AdvTrooperM1, tura10 | 100 | 1000 |
| AdvPriestM3, tura10 | 100 | 2000 |
| Objective ChallengeTerrorBar, Group1/Line0, późna tura | 5000 | 10000 |
| Pochodzenie spawned/reinforcement | runtime używa zwykłej stawki | osobne stawki pochodzenia |

EnemyPoints rozpoznaje tylko Muton i grupę Faceless/Viper/Sectoid/
PsiZombieCivilian; reszta dostaje default struktury SDK 500→100.
Konfiguracja gry ustala inne stawki dla ADVENT i inny default.
CompletedObjectivePoints zawsze stosuje10000→5000, mimo override misji.
Profil jawnie pomija też m.in. nagrody disabled i kary restartu.
Są to rzeczywiste różnice reguł, nie tylko brakujące obserwacje.

Osobny problem to coverage: runtime widzi tylko zaobserwowane eliminacje,
nie odtwarza wcześniejszych zdarzeń objective/civilian po późnym wczytaniu
i nadrabia historię porcjami. Końcowy native end nie uzupełnia tych luk.
Offline complete_for_comparison_convention oznacza pełny zakres tej
konwencji, a nie dowód zgodności wszystkich reguł Legacy.

Nie przemianowujemy więc obecnego profilu na oficjalny. Historyczny
warunkowy szacunek SabotageCC v32 ~+100 pozostaje szacunkiem wspomaganej
misji; powodem nie jest samo obliczenie przez mod, lecz brak parytetu
i potwierdzenia pełnej sumy. GasStation +6200 i Blood Killer +7100
pochodzą z potwierdzonych odczytów gry i zachowują swoją klasyfikację.

## Pochodzenie i dalsza praca

Prywatne źródła użyte w audycie, ścieżki względne:

- Config/DefaultLadder.ini:579–581: AdvTrooper1500→1000;
  :595–597: AdvPriest3000→2000; :576: globalny default1000 bez spadku.
- TLE/Config/XComLadder.ini:6: objective TerrorBar15000→10000.
- XComGame/Classes/XComGameState_ChallengeScore.uc:18–24: naliczanie
  kill/objective/civilian ma deklaracje native; dostarczony UC nie zawiera
  ciał tych funkcji, więc sam plik nie dowodzi dokładnych granic decay.
- Publiczne APX_ComparisonScore.uc oraz tools/legacy-score-rules.json
  definiują aktualny profil i jego wyłączenia.

Nie potrzeba nowych plików SDK/configów do usunięcia wskazanych różnic.
Dalszy focused zakres w issue #79 powinien uwzględnić właściwe tabele,
override misji, kwalifikację i pochodzenie zdarzeń, a następnie porównać
naliczanie z natywnymi zapisami. Oddzielnie trzeba oznaczać coverage,
końcowość i pochodzenie obliczeń. Nie wystarcza zmiana flagi
is_official_game_score ani zgodność jednej sumy.

Ta zmiana zasad i dokumentacji nie zmienia runtime v33, HUD, providera
punktów ani paczki do testu X4. Gotowość źródeł, natywna kompilacja
i dowód działania w grze pozostają odrębnymi stanami.
Surowe SDK, konfiguracje i raporty pozostają prywatne.
