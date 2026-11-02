# Wczesne Ostrzeżenie Warszawa

Pulpit sygnałów zagrożenia wobec Polski i Bałtów z ocenionych źródeł RSS, aktualizowany co godzinę. Główny parametr: współczynnik wpierdolu (WW, 0–100) i zegar zagłady. Mailem przychodzą tylko alarmy (spiętrzenie sygnałów, sygnał krytyczny, alarm trendu) i raport tygodniowy w poniedziałek. Metodyka: `strona/metodyka.html`.

## Uruchomienie lokalne
```
cd app
pip install -r requirements.txt
python ostrzezenie.py uruchom --bez-powiadomien
# otwórz ../strona/index.html
```

## Publikacja dla znajomych (raz, ok. 10 minut)
1. Załóż publiczne repo, np. `wczesne-ostrzezenie`, i skopiuj do niego zawartość tego folderu.
2. Przenieś `deploy/ostrzezenie.yml` do `.github/workflows/`.
3. Settings → Pages → Source: **GitHub Actions**. Adres strony wpisz jako zmienną `SITE_URL` (Settings → Secrets and variables → Actions → Variables).
4. Powiadomienia na telefon: wymyśl trudną do zgadnięcia nazwę tematu (np. `waw-ostrzezenie-7k3q`), zapisz jako sekret `NTFY_TOPIC`. Znajomi instalują aplikację **ntfy** (Android/iOS) i subskrybują ten temat.
5. Mail: na koncie nadawcy (Gmail z weryfikacją dwuetapową) utwórz hasło aplikacji (myaccount.google.com/apppasswords). Sekrety: `SMTP_USER` (adres nadawcy), `SMTP_PASS` (hasło aplikacji, 16 znaków), `MAIL_DO` (odbiorcy po przecinku). Odbiorcy dostają mail w kopii ukrytej. Skrót dnia idzie rano, alarm przy wzroście do Ostrzeżenia lub Alarmu.
6. Tłumaczenie bałtyckich nagłówków na subskrypcji Claude: na swoim komputerze `claude setup-token`, wynik jako sekret `CLAUDE_CODE_OAUTH_TOKEN` (bez niego nagłówki zostają w oryginale).
7. Godziny skrótu: zmienna `STATUS_GODZINY` (czas Warszawy, np. `6` albo `6,18`).
8. Uruchom workflow ręcznie (Actions → wczesne-ostrzezenie → Run workflow).

## Jak czytać
- **Kolor i indeks 0–100:** ile kategorii wskaźników naraz jest aktywnych wobec Polski i Bałtów, ważone oceną źródła.
- **Spiętrzenie sygnałów:** Uwaga (1 kategoria z 3+ niezależnymi redakcjami w 72 h), Ostrzeżenie (2), Alarm (3, w tym ewakuacja, ostrzeżenia wywiadu, mobilizacja albo zamknięcia nieba). Powiadomienie idzie tylko przy wzroście do Ostrzeżenia lub Alarmu.
- **Sygnał krytyczny:** ewakuacja ambasady, mobilizacja, art. 4/5 NATO, zamknięcie nieba albo atak zbrojny wobec Polski lub Bałtów, opisane przez 2 niezależne redakcje A/B w 24 h. Mail od razu, sprawdzane co godzinę.
- **Analogia 2021/22:** 10 zdarzeń sprzed ataku na Ukrainę i czy mają dziś odpowiednik wobec flanki.

To prywatne narzędzie, nie komunikat władz. Oficjalne alerty: Rządowe Centrum Bezpieczeństwa (gov.pl/web/rcb) i Alert RCB w telefonie.
