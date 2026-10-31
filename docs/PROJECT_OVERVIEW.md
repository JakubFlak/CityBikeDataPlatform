# CityBikeDataPlatform — analiza dostępności Wrocławskiego Roweru Miejskiego

## Od snapshotów GBFS do pytań operacyjnych

Zbudowałem lokalną platformę danych, która zbiera obserwacje systemu
Wrocławskiego Roweru Miejskiego udostępniane przez Nextbike w feedach GBFS.
Zamiast patrzeć tylko na pojedynczy stan systemu, mogę porównywać dostępność
rowerów i stacji pomiędzy zebranymi snapshotami oraz wskazywać miejsca
warte dalszej weryfikacji.

Projekt jest demonstratorem analitycznym, nie wdrożonym narzędziem
operacyjnym. Nie dowodzi, dlaczego stacja jest pusta, czy występuje tam
niezaspokojony popyt ani czy zmiana rozmieszczenia rowerów poprawi wyniki.
Pokazuje natomiast, jak dane o obserwowanym stanie można zamienić w
konkretne hipotezy do sprawdzenia przez miasto, operatora i Nextbike.

## Co może zyskać miasto i Wydział Inżynierii Miejskiej

Miasto może wykorzystać taką analizę jako dodatkowy kontekst przy ocenie
rozmieszczenia stacji i planowaniu przestrzeni:

- porównać, które stacje były puste w większej części zebranych obserwacji;
- sprawdzić, czy rowery zgłaszane poza stacjami skupiają się w określonych
  rejonach;
- wskazać lokalizacje do wizji terenowej, konsultacji z mieszkańcami lub
  rozmowy z operatorem;
- porównać przyszłe warianty lokalizacji stacji po zebraniu dłuższej historii
  i dodatkowych danych.

To może pomóc ustalić, **gdzie warto zadać następne pytanie**. Sama analiza
GBFS nie wystarcza do decyzji inwestycyjnej ani do stwierdzenia, że dana
lokalizacja wymaga nowej stacji.

## Co może zyskać zespół Wrocławskiego Roweru Miejskiego i operator

Dla zespołu operacyjnego raport może być punktem wyjścia do przeglądu
rozmieszczenia rowerów i planowania testów:

- wytypować stacje do sprawdzenia pod kątem częstego braku rowerów;
- porównać stany stacji między wybranymi okresami i obszarami;
- sprawdzić, czy obserwacje poza stacjami powtarzają się w tych samych
  rejonach;
- zaplanować ograniczony test relokacji lub uzupełniania rowerów, a następnie
  porównać obserwacje przed i po teście.

Takie działania są hipotezami operacyjnymi. Snapshoty nie zawierają
informacji o zgłoszeniach użytkowników, przejazdach, przyczynach braku
roweru ani o wykonanych relokacjach.

## Lokalizacje do sprawdzenia

Wstępna analiza zebranych obserwacji wskazała następujące stacje jako
kandydatów do sprawdzenia pod kątem częstego stanu zerowej dostępności:

1. Kosmonautów / Fieldorfa, szpital wojewódzki
2. Kołłątaja / Podwale
3. 3M
4. Gajowicka
5. Aleja Bielany

To lista priorytetów do weryfikacji, a nie stwierdzenie, że te stacje zawsze
są puste lub że brakuje tam rowerów z powodu popytu. Przed zmianą operacyjną
warto porównać liczbę pustych obserwacji z liczbą wszystkich obserwacji danej
stacji, sprawdzić pokrycie czasowe oraz rozbić wynik na dni i pory dnia.

W danych `free_bike_status` występują też obserwacje rowerów z pustym
`station_id`. Wskazane rejony mogą być kandydatami do terenowego sprawdzenia,
czy przydałaby się tam oficjalna stacja lub inne rozwiązanie parkowania:

- okolice ul. Kwiatkowskiego;
- ul. Wyścigowa;
- okolice ul. Balonowej;
- Wrocławski Park Przemysłowy (budynki B1/D1);
- ul. Tęczowa;
- ul. Mieszczańska (Kępa Mieszczańska);
- okolice przystanku Kromera (Czajkowskiego).

Pusty `station_id` oznacza wyłącznie, że feed nie przypisał obserwowanego
roweru do stacji. Nie dowodzi, że rower został nieprawidłowo zaparkowany,
że jest tam stały popyt ani że lokalizacja spełnia warunki techniczne lub
prawne. Lista wymaga sprawdzenia na mapie i w terenie; warto też potwierdzić
ją z operatorem i mieszkańcami.

## Przykładowe działania, które można przetestować

### 1. Pilotaż uzupełniania stacji

Na wybranych stacjach z listy można przetestować czasowe zwiększenie liczby
rowerów lub zmianę planu relokacji. Przed testem warto uzgodnić z operatorem
okres, dostępne zasoby, miernik sukcesu i stacje porównawcze. Wynik należy
oceniać na podstawie porównywalnych okien czasowych, nie pojedynczych
snapshotów.

### 2. Wizja lokalna dla skupisk rowerów poza stacjami

Operator i miasto mogą zweryfikować wskazane rejony: warunki postoju,
dostępność przestrzeni publicznej, istniejące stacje, połączenia piesze i
rowerowe oraz możliwość bezpiecznego serwisu. Dopiero po takim przeglądzie
można rozważyć pilotaż nowej stacji lub innego rozwiązania.

### 3. Wspólny przegląd miejsc o niskiej dostępności

Miasto, zespół Wrocławskiego Roweru Miejskiego i Nextbike mogą wspólnie
przejrzeć listę miejsc, zakres i jakość danych, a następnie uzgodnić, które
lokalizacje wymagają danych uzupełniających, inspekcji lub testu
operacyjnego. Raport może służyć jako wspólny punkt startowy do rozmowy, nie
jako automatyczny system dyspozytorski.

### 4. Rozszerzenie analizy danymi o przejazdach i operacjach

Jeśli dostępne będą wiarygodne dane, warto połączyć snapshoty z historią
wypożyczeń, zgłoszeniami awarii i zapisami relokacji. Pozwoliłoby to
sprawdzić, czy powtarzające się puste stany współwystępują z dużą liczbą
wypożyczeń, czy rowery poza stacjami wiążą się z określonymi zakończeniami
przejazdów i czy pilotaż zmienił uzgodnione wskaźniki. Takich analiz obecna
wersja jeszcze nie obsługuje.

## Co pokazuje raport

Raport Power BI ma trzy strony:

- **System Overview** — stan systemu w wybranym/najnowszym snapshotcie:
  liczbę rowerów zgłoszonych na stacjach, liczbę obserwowanych stacji,
  puste stacje i rowery zgłoszone poza stacjami oraz trendy snapshotów.
- **Station Analysis** — porównanie dostępności obserwacji stacji, z
  możliwością filtrowania według stacji, regionu i wybranego okresu.
- **Bikes Analysis** — obserwowane rowery i typy pojazdów, udział e-bike’ów
  w rowerach stacyjnych oraz mapę rowerów widocznych w ograniczonym zakresie
  lokalizacji i typów.

„Dostępny rower” oznacza tu wartość raportowaną przez feed w chwili
obserwacji. „Pusta stacja” oznacza obserwowany rekord stacji z liczbą
dostępnych rowerów równą zero. Brak rekordu nie jest liczony jako pusta
stacja. „Free bike” z pustym `station_id` nie jest tym samym co rower
dostępny na stacji. Wskaźniki okresowe są oparte na obserwacjach, a nie na
ciągłym pomiarze każdej minuty ani na przejazdach. Szczegóły definicji
znajdują się w [katalogu KPI](POWER_BI_ANALYTICS.md).

## Jakie kompetencje pokazuje projekt

Zbudowałem rozwiązanie end-to-end, obejmujące:

- pobieranie i walidację API GBFS, obsługę błędów HTTP i ponawianie
  przejściowych żądań;
- zachowanie źródłowych snapshotów w Raw oraz typowanie i modelowanie danych
  w warstwach Silver i Gold;
- projektowanie ziarnistości tabel, kluczy, lineage i semantyki czasu UTC
  oraz `Europe/Warsaw`;
- przyrostowe, idempotentne przetwarzanie ze stanem pipeline’u i bezpiecznym
  zapisem wyników;
- kontrole jakości danych oraz testy jednostkowe i integracyjne;
- model analityczny i raport Power BI z miarami DAX;
- CI dla testów i Ruff oraz dokumentację uruchamiania i ograniczeń.

Implementacja używa Python, PyArrow/Parquet, pytest, Ruff, GitHub Actions i
Power BI. Obecna wersja jest lokalnym projektem portfolio, a nie wdrożeniem
produkcyjnym. Testy weryfikują zachowanie kodu na przygotowanych przypadkach;
nie są dowodem trwałego monitoringu ani wyników operacyjnych miasta lub
operatora.

## Zakres i ograniczenia — ważne przed decyzją

- GBFS opisuje stany widoczne w feedzie; nie zawiera autorytatywnej historii
  przejazdów, popytu, klientów, przychodów ani faktycznego wykorzystania.
- Dane i stan pipeline’u są przechowywane lokalnie; nie ma trwałego backupu,
  monitoringu produkcyjnego ani alertów.
- Eksport harmonogramu Windows jest skonfigurowany godzinowo, ale jego
  faktyczna rejestracja i historia uruchomień zależą od lokalnej maszyny.
  Taki interwał nie pokazuje zmian zachodzących między pobraniami.
- Raport Power BI korzysta z lokalnych, bezwzględnych ścieżek do plików Gold
  i wymaga dostosowania na innym komputerze.
- Mapa rowerów ma filtry Power Query na zakres szerokości geograficznej i
  dwa identyfikatory typu pojazdu; nie przedstawia pełnego, nieprzefiltrowanego
  zbioru floty.
- Bieżące wskaźniki wymagają przeglądu semantycznego przed użyciem jako
  formalnych KPI. Niektóre miary różnią się obsługą wartości null, a jedna
  miara e-bike ma niespójną nazwę. Szczegóły opisuję w
  [dokumentacji KPI](POWER_BI_ANALYTICS.md).

## Mój dalszy plan — v2.0

W v2.0 planuję najpierw ustalić wymagania dotyczące częstotliwości,
retencji, dostępności i kosztów, a następnie ocenić chmurowe przechowywanie
danych i uruchamianie pipeline’u. Chcę też przygotować monitoring, obsługę
błędów, bezpieczną konfigurację, połączenie Power BI z docelowym modelem
oraz automatyzację wdrożeń. Wybór usług Azure/Fabric uzależnię od tych
wymagań — nie jest jeszcze decyzją architektoniczną.

GitHub nadal może służyć do wersjonowania kodu i dokumentacji, review oraz
CI/CD, nawet jeśli runtime i dane zostaną przeniesione do chmury. Szczegóły
planu są w [roadmapie v2.0](../tasks/ROADMAP.md).
