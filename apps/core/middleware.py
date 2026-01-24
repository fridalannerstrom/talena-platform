class AuthTraceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # super-tydlig logg, så vi ser om du "tappar" sessionen mellan sidor
        sessionid = request.COOKIES.get("sessionid")
        print(
            f"🔎 {request.method} {request.get_full_path()} | "
            f"host={request.get_host()} secure={request.is_secure()} | "
            f"auth={request.user.is_authenticated} | sessionid={'YES' if sessionid else 'NO'}"
        )
        return self.get_response(request)