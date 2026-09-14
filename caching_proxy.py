import os 
from http.server import HTTPServer, BaseHTTPRequestHandler

import aiohttp
from aiohttp import web
import requests
from multidict import CIMultiDict

HOP_BY_HOP_HEADERS = ("server", "connection", "keep-alive","te", 
                          "transfer-encoding", "trailer", "upgrade", 
                          "proxy-authenticate", "proxy-authorization",
                          "content-length", "content-encoding")


class Handler(web.View):
    url: str = "https://dummyjson.com"
    lru_cache = {} 
    session: aiohttp.ClientSession
    max_size: int = -1
    
    @classmethod
    def set_url(cls, url):
        if not cls.url:
            cls.url = url

    @classmethod
    async def setup(cls, server):
        cls.session = aiohttp.ClientSession()
        yield
        await cls.session.close()

    @classmethod
    def set_size(cls, max_size):
        cls.max_size = max_size

    async def get(self) -> web.Response:
        r = Handler.lru_cache.pop(self.request.rel_url, None)

        if r is not None:  
            # Add it back to the to the most recent used
            Handler.lru_cache[self.request.rel_url] = r
            print(f"{self.request.rel_url} Cache hit \n")
            return web.Response(status=r[0], headers=r[1], body=r[2])
        
        full_url = Handler.url + str(self.request.rel_url)
        return await self.fetch(full_url)

    async def fetch(self, url) -> web.Response:
        async with Handler.session.get(url) as r:
            status = r.status
            headers = CIMultiDict(r.headers)
            body = await r.read()

        for h in HOP_BY_HOP_HEADERS:
            headers.popall(h, None)
        # Just in case it is in the cache
        Handler.lru_cache.pop(self.request.rel_url, None)
        Handler.lru_cache[self.request.rel_url] = (status, headers, body)
        print(f"{url} added to cache")
        if Handler.max_size != - 1 and len(Handler.lru_cache) > Handler.max_size:
            lru = next(iter(Handler.lru_cache))
            Handler.lru_cache.pop(lru)
            print(f"{lru} removed from cache")
        print(f"Cache: {len(Handler.lru_cache)}/{Handler.max_size} \n")
        return web.Response(status=status, headers=headers, body=body)
    
if __name__ =="__main__":
    server = web.Application()
    server.router.add_route("*", "/{tail:.*}", Handler)
    Handler.set_size(10)
    server.cleanup_ctx.append(Handler.setup)
    web.run_app(server, host="localhost", port=3000)