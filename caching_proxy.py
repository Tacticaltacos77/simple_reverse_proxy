import os 
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

NOT_NEEDED_HEADERS = ("server", "connection", "keep-alive","te", 
                          "transfer-encoding", "trailer", "upgrade", 
                          "proxy-authenticate", "proxy-authorization")

class Handler(BaseHTTPRequestHandler):
    url: str = "https://dummyjson.com"
    cache = {} 

    def set_url(self, url):
        if not Handler.url:
            Handler.url = url
        
    def do_GET(self):
        cached = Handler.cache.get(self.path, None)
        
        if isinstance(cached, requests.Response):  
            self.send(cached, True)
            return
        self.fetch()

    def fetch(self):
        response = requests.get(Handler.url + self.path, stream=True)
        headers_to_remove = []
        for k in response.headers:
            if k.lower() in NOT_NEEDED_HEADERS:
                headers_to_remove.append(k)

        for k in headers_to_remove:
            response.headers.pop(k)
            
        response.headers["content-length"] = str(len(response.raw.read(cache_content=True)))
        
        Handler.cache[self.path] = response
        self.send(response, False)

    def send(self, response: requests.Response, cached: bool):  
        print(f"Cached: {cached}: ", end="", flush=True)
        self.log_request(response.status_code)
        self.send_response_only(response.status_code)
        for k, v in response.headers.items():
            self.send_header(k, v)
        cached_status = "Hit" if cached else "Miss"
        self.send_header("X-Cache", cached_status)
        self.end_headers()
        self.wfile.write(response.raw.data)

if __name__ =="__main__":
    server = HTTPServer(("localhost", 3000), Handler)
    server.serve_forever()

