# === Importowanie niezbędnych bibliotek ===
import json  # Do obsługi JSON
import logging  # Logowanie błędów i informacji
import time  # Zarządzanie opóźnieniami czasowymi
import requests  # Wykonywanie żądań HTTP

# === Klasa JsonHttpClient ===
class JsonHttpClient(object):
    """
    Prosty klient HTTP do wykonywania żądań REST, zwracający dane JSON.
    Obsługuje automatyczne ponawianie prób w razie błędów.
    """

    def __init__(self, host: str):
        # Inicjalizacja klienta z adresem bazowym serwera
        self.host = host

    def get_json(self, path: str, retry: int = -1, method: str = 'GET', **kwargs) -> dict:
        """
        Wysyła żądanie HTTP na wskazany adres URL (path) względem hosta.
        Automatycznie ponawia żądanie w przypadku błędów.

        Parametry:
        - path: ścieżka endpointu serwera.
        - retry: liczba prób ponawiania (-1 oznacza nieskończenie wiele).
        - method: metoda HTTP (GET, POST, itp.).
        - **kwargs: dodatkowe argumenty przekazywane do requests.

        Zwraca:
        - Odpowiedź JSON jako słownik.
        """
        url = join_url(self.host, path)
        retry_times = 0
        while retry_times != retry:
            try:
                # Wysyłanie żądania HTTP
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()  # Rzuca wyjątkiem przy błędnym statusie HTTP

                if retry_times:
                    # Logowanie informacji o sukcesie po ponowieniu próby
                    logging.warning(f'Sukces po {retry_times} próbach, URL: {url}')

                return json.loads(response.text)  # Parsowanie odpowiedzi JSON
            except Exception as e:
                # Logowanie błędu przy każdej nieudanej próbie
                logging.debug(e)
                retry_times += 1
                if retry_times % 100 == 0:
                    logging.error(f'Niepowodzenie po {retry_times} próbach: {e}')
                time.sleep(0.1)  # Odczekanie przed ponowieniem próby

# === Funkcja pomocnicza join_url ===
def join_url(lhs, rhs):
    """
    Skleja bazowy URL (lhs) ze ścieżką (rhs), dbając o poprawność formatu.

    Parametry:
    - lhs: bazowy URL.
    - rhs: ścieżka endpointu.

    Zwraca:
    - Połączony URL jako string.
    """
    if len(rhs) and rhs[0] != '/':
        rhs = '/' + rhs
    return lhs + rhs
