# Raport v15: zatrzymania przed rzutem granatu

Analiza archiwum `AutoplayXCom2-20261104-201452-ae0122fb.zip`.
Archiwum zawiera także starsze logi; poniższy wynik dotyczy najnowszej
sesji `2026-11-4_21-1-46-97_890`, z rewizją `mission-report-v15`.
Pełne logi i archiwum pozostają poza repozytorium.

## Wynik najnowszej próby

`SabotageCC`, trudność 3: **porażka w turze 18**. Zarejestrowano
80 przyjętych rozkazów i zero rozkazów odrzuconych przez silnik:
34 ruchy, 18 strzałów, 14 overwatch, 7 hunker, 6 przeładowań i jeden własny
granat. Potwierdzono osiem zabitych widocznych przeciwników. Na końcu
trzech żołnierzy nie żyje, a ostatni, 409, wykrwawia się przy 1 HP.

Misja nie prowadziła natywnej punktacji. Częściowy wynik porównawczy wynosi
−17500. `attempt_verdict=fail` wynika już z oficjalnej porażki; częściowy
wynik nie jest przedstawiany jako pewny pełny wynik misji.

## Dlaczego autoplay się wyłączył

W najnowszym logu występują trzy automatyczne zatrzymania przed rzutem,
wszystkie w turze 10. Czasy w tabeli są czasami względnymi z logu.

| Decyzja | Seq | Czas | Powód |
| --- | ---: | ---: | --- |
| 64 | 6911 | 665,43 s | `Grenade landing or affected objects changed` |
| 65 | 6922 | 686,55 s | ten sam |
| 66 | 6932 | 693,34 s | ten sam |

Za każdym razem wybierano ten sam granat żołnierza 421, który miał
1 HP, 1 AP i pusty karabin. Granat otrzymywał ocenę 70 wobec przeładowania
na 35. Cel 918 miał 1 HP po poprzednim zaakceptowanym granacie żołnierza
415 w decyzji 63, który obniżył jego HP z 4 do 1.

`PrepareForActivation()` odrzucało plan jeszcze przed aktywacją zdolności.
Granatu żołnierza 421 **nie wysłano do silnika**. Dlatego te zatrzymania
nie zwiększają licznika odrzuconych rozkazów. Ponowne włączenie autoplaya
wybierało ten sam kandydat w niezmienionej sytuacji i powtarzało zatrzymanie.

Ogólny komunikat nie rozróżnia nieudanej trajektorii, różnicy miejsca
lądowania, bezpieczeństwa wybuchu i zmiany zestawu celów. Log nie dowodzi,
że faktycznie przesunęło się miejsce lądowania. [V16](tactics-v16.pl.md)
zachowuje kontrolę bezpieczeństwa, dodaje dokładniejszy powód i przechodzi
do innej akcji po odrzuceniu kandydata.

## Oddzielny błąd kończenia tury w starszym logu

Starsza sesja v14 `SabotageTransmitter` zawiera siedem zatrzymań
`Engine rejected end turn`, przy decyzjach 4, 6, 12, 14, 19, 20 i 24.
Nie są to trzy zatrzymania granatu z najnowszej próby.

W posiadanym SDK `XGPlayer.uc:437–446` wysyła kontekst
`eGameRule_SkipTurn`, lecz także po wysłaniu zwraca `false`.
`XComTacticalController` przekazuje tę wartość. Nasz kontroler błędnie
traktował ją jako dowód odrzucenia. W logu pierwszy taki stop przy 73,08 s
jest zaraz potem uzupełniony przejściem silnika do następnego gracza
przy 73,09 s. V16 potwierdza żądanie na podstawie historii lub rzeczywistej
zmiany gracza/tury, z ograniczonym oczekiwaniem.

## Co potwierdzono w v15

Jedno przestawienie przed strzałem zadziałało zgodnie z prognozą.
W decyzji 29 (`seq=3091`) żołnierz 421 przesunął się przed atakiem na 911:
bieżąca szansa wynosiła 47%, prognozowana 68%, a ryzyko obu pozycji 31,7833.
Następny rzeczywisty strzał w decyzji 30 (`seq=3116`) otrzymał natywne 68%.
Wynik `seq=3335` był krytyczny i zabił cel z 4 HP. To potwierdza jeden
przypadek prognozy; nie dowodzi poprawności dla wszystkich sytuacji.

W tej próbie nie wystąpiły szkodliwe chmury trucizny ani kandydaci kombinacji
AP z czynnością medyczną lub Aid Protocol. Tych mechanizmów raport nie
zweryfikował. Porażka misji pozostaje wynikiem całej próby, mimo poprawnego
wykonania pojedynczego przestawienia.

[Zakres poprawki i następna próba v16](tactics-v16.pl.md) ·
[Zbieranie raportu](mission-recording.pl.md).
