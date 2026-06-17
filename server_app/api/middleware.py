import time


class ApiRequestDebugLogMiddleware:
    """
    Понятные логи API-запросов в консоль Django runserver.
    Показывает:
      - метод и путь
      - статус
      - время обработки
      - тип ответа
      - применилось ли gzip-сжатие
      - размер ответа
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Чтобы не зашумлять консоль, логируем в основном API.
        if request.path.startswith("/api/"):
            encoding = response.get("Content-Encoding", "none")
            content_type = response.get("Content-Type", "unknown")
            content_length = response.get("Content-Length")

            if content_length is not None:
                size_info = f"{content_length} B"
            elif hasattr(response, "content"):
                size_info = f"{len(response.content)} B"
            else:
                size_info = "streaming/unknown"

            gzip_state = "yes" if encoding.lower() == "gzip" else "no"

            print(
                "[API] "
                f"{request.method} {request.path} -> {response.status_code} | "
                f"{elapsed_ms:.1f} ms | "
                f"gzip: {gzip_state} | "
                f"size: {size_info} | "
                f"type: {content_type}"
            )

        return response
