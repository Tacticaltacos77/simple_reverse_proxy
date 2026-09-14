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
    cache = {} 
    session: aiohttp.ClientSession

    @classmethod
    def set_url(cls, url):
        if not cls.url:
            cls.url = url

    @classmethod
    async def setup(cls, server):
        cls.session = aiohttp.ClientSession()
        yield
        await cls.session.close()
        
    async def get(self) -> web.Response:
        r= Handler.cache.get(self.request.rel_url, None)
        print(len(Handler.cache.keys()))
        if r is not None:  
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

        Handler.cache[self.request.rel_url] = (status, headers, body)
        return web.Response(status=status, headers=headers, body=body)
    
if __name__ =="__main__":
    server = web.Application()
    server.router.add_route("*", "/{tail:.*}", Handler)
    server.cleanup_ctx.append(Handler.setup)
    web.run_app(server, host="localhost", port=3000)