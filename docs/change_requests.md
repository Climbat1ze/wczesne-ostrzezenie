# Rejestr zgłoszeń zmian (Change Requests)

Każda zmiana aplikacji zaczyna się od zgłoszenia: formularz issue „Zgłoszenie zmiany (Change Request)” albo prośba
właściciela. Właściciel nadaje numer CR, decyduje i wpisuje wynik tutaj. Wdrożenie: pull request, wersja w `app/WERSJA`,
wpis w `CHANGELOG.md`.

Statusy: **zgłoszone**, **zaakceptowane**, **odrzucone**, **wdrożone**, **wycofane**.

| CR | Data | Zgłaszający | Co | Decyzja i uzasadnienie | Status | Wersja | PR |
|----|------|-------------|----|------------------------|--------|--------|----|
| CR-001 | 2026-11-04 | właściciel | Logować historię zmian i zgłoszenia zmian | `CHANGELOG.md` (Keep a Changelog) + ten rejestr + formularz issue. Wersje 1.0.0–1.5.1 odtworzone z historii PR. | wdrożone | 2.0.0 | #13 |
| CR-002 | 2026-11-04 | właściciel | Wersjonowanie aplikacji | Semver w `app/WERSJA`; MAJOR = nowy moduł albo zmiana liczenia WW. Wersja widoczna w stopce, mailach, odpowiedziach na zgłoszenia. | wdrożone | 2.0.0 | #13 |
| CR-003 | 2026-11-04 | właściciel | Ręczny skan źródeł po słowach kluczowych, dla każdego użytkownika | Dwie drogi: szukanie w przeglądarce (bez konta, 3 dni) i pełny skan przez formularz issue (konto GitHub). Strona statyczna nie ma serwera, więc formularz issue to jedyny bezpieczny sposób uruchomienia skanu przez obcą osobę bez tokenu w stronie. Limit 3 na osobę i 10 na dobę chroni subskrypcję. | wdrożone | 2.0.0 | #13 |
| CR-004 | 2026-11-04 | właściciel | Weryfikacja przez link: prawdziwość i inne wystąpienia | Ten sam formularz z polem Link. Kontrola adresu i przekierowań (bez adresów prywatnych), ocena domeny z rejestru, szukanie w archiwum, kanałach i Google News, werdykt modelu. | wdrożone | 2.0.0 | #13 |
| CR-005 | 2026-11-04 | właściciel | Lepsze wnioskowanie: unikać źle rozpoznanej intencji (wojsko przy granicy) | Reguła strony (pierwszy aktor + czasownik) + model sonnet raz na godzinę dla wpisów, które mogą podnieść spiętrzenie. Model tylko zdejmuje kategorię (pewność >= 0,7), nie dodaje i nie wycisza sygnałów krytycznych. Zgłoszenia analizowane metodą hipotez konkurencyjnych. | wdrożone | 2.0.0 | #13 |
| CR-006 | 2026-11-04 | właściciel | Historia zgłoszeń i analiza wsteczna z oceną (kontrola jakości, samodoskonalenie) | Gałąź `zgloszenia` z pełną historią commitów, ponowne sprawdzenie po 7 i 30 dniach, trafność, wynik Briera, lekcje do autoulepszania (PR do przeglądu, bez samoczynnego scalania). Alarmy mailowe nadal oceniane przez właściciela (etykiety `ocena-trafny`, `ocena-pomylka`). | wdrożone | 2.0.0 | #13 |
| CR-007 | 2026-11-04 | właściciel | Analogia 2021/22 myli sens: rosyjskie oskarżenia Polski liczone jako ostrzeżenie zachodniego wywiadu, europejskie ćwiczenia w Polsce jako ćwiczenia Rosji | Kryterium odpowiednika przy każdym kamieniu + weryfikacja modelem sonnet każdej pary; liczą się tylko potwierdzone. Bez modelu jak dawniej, z oznaczeniem „bez sprawdzenia”. Zdanie w skrócie bez słowa „flanka”. | wdrożone | 2.0.0 | #13 |
| CR-008 | 2026-11-04 | właściciel | Nagłówki po rosyjsku na pulpicie: czytelnicy nie znają cyrylicy | Zaległe trafienia dotłumaczane przy każdym przebiegu (do 4 zapytań), zapis trwały; reguła strony działania rozumie rosyjski. | wdrożone | 2.0.0 | #13 |
