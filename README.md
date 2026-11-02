# Wczesne Ostrzeżenie

Pulpit sygnałów zagrożenia wobec Polski i Bałtów z ocenionych źródeł RSS, aktualizowany co godzinę. Główny parametr: współczynnik wpierdolu (WW, 0–100) i zegar zagłady.

**Strona:** https://climbat1ze.github.io/wczesne-ostrzezenie/ · **Metodyka:** https://climbat1ze.github.io/wczesne-ostrzezenie/metodyka.html

To prywatne narzędzie, nie komunikat władz. Oficjalne alerty: Rządowe Centrum Bezpieczeństwa (gov.pl/web/rcb) i Alert RCB w telefonie.

## Jak czytać
- **Kolor i indeks 0–100:** ile kategorii wskaźników naraz jest aktywnych wobec Polski i Bałtów, ważone oceną źródła.
- **Spiętrzenie sygnałów:** Uwaga (1 kategoria z 3+ niezależnymi redakcjami w 72 h), Ostrzeżenie (2), Alarm (3, w tym ewakuacja, ostrzeżenia wywiadu, mobilizacja albo zamknięcia nieba). Mail idzie tylko przy wzroście do Ostrzeżenia lub Alarmu.
- **Sygnał krytyczny:** ewakuacja ambasady, mobilizacja, art. 4/5 NATO, zamknięcie nieba albo atak zbrojny wobec Polski lub Bałtów, opisane przez 2 niezależne redakcje A/B w 24 h. Mail od razu.
- **Alarm trendu:** rusza po zebraniu 21 dni historii.
- **Analogia 2021/22:** 10 zdarzeń sprzed ataku na Ukrainę i czy mają dziś odpowiednik wobec flanki.

## Maile
Mailem przychodzą tylko alarmy (spiętrzenie sygnałów, sygnał krytyczny, alarm trendu) i raport tygodniowy w poniedziałek rano. Odbiorcy są w kopii ukrytej i nie widzą swoich adresów nawzajem. Żeby dopisać lub usunąć odbiorcę, nadpisz sekret pełną listą adresów po przecinku:

```
gh secret set MAIL_DO -R Climbat1ze/wczesne-ostrzezenie
```

## Jak to działa
Workflow `.github/workflows/ostrzezenie.yml` uruchamia się co godzinę (minuta 47): pobiera kanały, tłumaczy bałtyckie nagłówki, liczy WW, wysyła alarmy i publikuje stronę na GitHub Pages. Stan (historia, wpisy, statystyki źródeł) żyje na gałęzi `dane`, nadpisywanej jednym commitem przy każdym przebiegu. Raz w tygodniu przegląd źródeł aktualizuje `app/zrodla.yaml` na `main`.

Ręczne uruchomienie: Actions → wczesne-ostrzezenie → Run workflow (opcja „Wyślij raport mailem teraz”).

## Konfiguracja
| Nazwa | Rodzaj | Do czego |
|---|---|---|
| `SMTP_USER` | sekret | adres Gmail nadawcy |
| `SMTP_PASS` | sekret | hasło aplikacji Gmail (myaccount.google.com/apppasswords) |
| `MAIL_DO` | sekret | odbiorcy po przecinku |
| `CLAUDE_CODE_OAUTH_TOKEN` | sekret | tłumaczenie nagłówków; wynik `claude setup-token`. Bez niego nagłówki zostają w oryginale |
| `MAIL_ADMIN` | sekret, opcjonalny | odbiorca maili o przeglądzie źródeł (domyślnie nadawca) |
| `SITE_URL` | zmienna | adres strony, wstawiany do maili |
| `STATUS_GODZINY` | zmienna, opcjonalna | godzina raportu, czas Warszawy (domyślnie `7`) |
| `STATUS_DNI` | zmienna, opcjonalna | dni raportu, 1 = poniedziałek (domyślnie `1`) |
| `STATUS_FORMA` | zmienna, opcjonalna | `tydzien` (raport tygodniowy, domyślnie) albo `dzien` (pełny skrót) |
| `CLAUDE_BUDZET_DZIENNY` | zmienna, opcjonalna | dzienny limit zapytań do Claude (domyślnie `150`); po wyczerpaniu nagłówki zostają w oryginale, jeden mail do administratora na dobę |
| `CLAUDE_WYLACZ` | zmienna, opcjonalna | `1` = żadnych wywołań Claude (tłumaczenie, oceny, przeglądy) |
| `ALARMY_DZIENNIE` | zmienna, opcjonalna | najwyżej tyle alarmów mailem na dobę (domyślnie `3`); kolejne czekają w kolejce i idą zbiorczo o godzinie raportu albo z następnym alarmem |

## Uruchomienie lokalne
```
cd app
pip install -r requirements-dev.txt
python ostrzezenie.py uruchom --bez-powiadomien
cd .. && python -m pytest -q   # testy
# otwórz ../strona/index.html
```
Źródła: `python ostrzezenie.py zrodla lista` (także `testuj`, `dodaj`, `ocen`, `status`, `przeglad`).
