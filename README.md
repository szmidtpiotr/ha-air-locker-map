# Air Locker Map — integracja Home Assistant

Jakość powietrza z czujników w paczkomatach InPost w Home Assistancie: PM1, PM2.5, PM4, PM10
i ciśnienie, pobierane z serwera [air-locker-map](https://github.com/szmidtpiotr/air-locker-map)
(mapa: <https://air-locker-map.studio-colorbox.com/>).

> Dane pochodzą z nieoficjalnego źródła (czujniki w paczkomatach InPost). Projekt hobbystyczny,
> niezwiązany z InPostem, bez gwarancji dostępności.

## Instalacja (HACS)

1. HACS → menu ⋮ → **Custom repositories** → `https://github.com/szmidtpiotr/ha-air-locker-map`, typ **Integration**.
2. Zainstaluj **Air Locker Map** i zrestartuj Home Assistanta.
3. **Ustawienia → Urządzenia i usługi → Dodaj integrację → Air Locker Map.**

Potrzebny jest **klucz API** — wydaje go administrator serwera (panel `/admin` → Klucze API).
Każdy klucz można unieważnić osobno; wtedy integracja poprosi o nowy (bez usuwania encji).

## Tryby

| Tryb | Co robi |
|---|---|
| **Najbliższy czujnik do domu** | Lokalizacja z ustawień HA. Gdy najbliższy czujnik się zepsuje, bierze następny. |
| **Najbliższy do paczkomatu** | Podajesz dowolny kod (np. `KAP01M`, także bez czujnika) — bierze najbliższy działający. |
| **Konkretny czujnik** | Zawsze ten sam paczkomat z czujnikiem, bez zastępowania. |

Każdy wpis to osobne urządzenie, więc możesz mieć np. dom i działkę.

## Encje

- **PM1, PM2.5, PM10, ciśnienie (n.p.m.)** — włączone.
- **PM4** (tylko nowsze czujniki), **ciśnienie na miejscu**, **wilgotność i temperatura** — domyślnie wyłączone.
  Wilgotność i temperatura są mierzone **w obudowie paczkomatu**; w słońcu temperatura bywa mocno zawyżona.
- **Paczkomat z czujnikiem** — kod źródła; w atrybutach adres, współrzędne, flagi.
- **Podejrzany odczyt** (problem) — czujnik wygląda na zepsuty (zawieszony, zalany, nierealny, martwy,
  odstający od sąsiadów).
- **Odległość do czujnika**, **ostatni odczyt** — diagnostyczne.

- **Przekroczenie normy** — włącza się, gdy PM2.5 przekroczy próg z opcji (13, 35, 55 albo 75 µg/m³; domyślnie 35),
  wyłącza poniżej 80% progu (histereza, żeby nie migało przy wartościach na granicy). Zepsute odczyty są ignorowane.

## Alert smogowy — blueprint

Gotowa automatyzacja: powiadomienie na telefon przy smogu i po poprawie, plus dowolne akcje
(włącz oczyszczacz, zamknij okna, wyłącz rekuperację).

[![Importuj blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fszmidtpiotr%2Fha-air-locker-map%2Fblob%2Fdevelop%2Fblueprints%2Fautomation%2Fair_locker_map%2Fsmog_alert.yaml)

Albo ręcznie: Ustawienia → Automatyzacje → Blueprinty → Importuj → adres pliku
`blueprints/automation/air_locker_map/smog_alert.yaml` z tego repo.

Opcje: częstotliwość odpytywania (domyślnie 15 min; serwer odświeża dane mniej więcej co godzinę)
i dopuszczanie podejrzanych czujników.

## Adres serwera

Domyślnie publiczny `https://air-locker-map.studio-colorbox.com`. Jeśli serwer stoi w Twojej sieci,
wpisz adres lokalny (np. `http://192.168.1.66:8080`) — działa tak samo, bez wychodzenia do internetu.

## Testy

```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest -q
```
