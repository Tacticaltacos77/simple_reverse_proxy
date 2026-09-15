import argparse
import time
from typing import NamedTuple
import aiohttp
from aiohttp import web
from multidict import CIMultiDict

HOP_BY_HOP_HEADERS = ("server", "connection", "keep-alive","te", 
                          "transfer-encoding", "trailer", "upgrade", 
                          "proxy-authenticate", "proxy-authorization",
                          "content-length", "content-encoding")


class CachedResponse(NamedTuple):
    status: int
    headers: CIMultiDict[str]
    body: bytes
    expire_at: float

class Handler(web.View):
    url: str
    lru_cache = {} 
    session: aiohttp.ClientSession
    max_size: int
    ttl: int


    @classmethod
    async def setup_session(cls, server):
        cls.session = aiohttp.ClientSession()
        yield
        await cls.session.close()


    @classmethod
    def setup(cls, *, max_size, ttl, url):
        cls.url = url
        cls.ttl = ttl
        cls.max_size = max_size

    async def get(self) -> web.Response:
        r = Handler.lru_cache.pop(self.request.rel_url, None)
        
        if isinstance(r, CachedResponse) and time.monotonic() <= r.expire_at:  
            # Add it back to the to the most recent used
            Handler.lru_cache[self.request.rel_url] = r
            print(f"{self.request.rel_url} Cache hit \n")
            return web.Response(status=r.status, headers=r.headers, body=r.body)
        
        full_url = Handler.url + str(self.request.rel_url)
        return await self.fetch(full_url)

    
    @classmethod
    def parse_cache_control(cls, cache_control: str|None) -> dict:
        out = {"no-store": False, "max-age": cls.ttl}
        if not cache_control:
            return out
        for ccv in cache_control.split(","):
            nv = ccv.strip().lower()
            if nv.startswith("max-age="):
                try:
                    max_age = int(nv.split("=")[-1])
                    out["max-age"] = max_age
                except ValueError:
                    print(f"Failed to parse: {nv}")
            else:
                out[nv] = True
        return out


    async def fetch(self, url) -> web.Response:
        async with Handler.session.get(url) as r:
            status = r.status
            headers = CIMultiDict(r.headers)
            body = await r.read()

        for h in HOP_BY_HOP_HEADERS:
            headers.popall(h, None)
        
        cache_headers = self.parse_cache_control(headers.get("cache-control", None))
        
        # Respect upstream max-age if possible
        if cache_headers["max-age"] >= 0:
            expire_at = time.monotonic() + cache_headers["max-age"]
        else:
            expire_at = float("inf")

        if not cache_headers["no-store"]:
            # Pop to be sure we are updating the lru if two of the same request come in near same time. 
            Handler.lru_cache.pop(self.request.rel_url, None)
            cache_resp = CachedResponse(status, headers, body, expire_at)
            cache_resp.headers["X-Cache"] = "Hit"
            Handler.lru_cache[self.request.rel_url] = cache_resp
            print(f"{url} added to cache")

        if Handler.max_size >= 0 and len(Handler.lru_cache) > Handler.max_size:
            lru = next(iter(Handler.lru_cache))
            Handler.lru_cache.pop(lru)
            print(f"{lru} removed from cache")

        print(f"Cache: {len(Handler.lru_cache)}/{Handler.max_size} \n")
        resp = web.Response(status=status, headers=headers, body=body)
        resp.headers["X-Cache"] = "Miss"
        return resp



if __name__ =="__main__":
    arg_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument("-s", "--size",type=int, default=-1, help="Set the max size of the cache. Negative is unlimited")
    arg_parser.add_argument("-t", "--ttl",type=int, default=86400, help="Set the time to live for caches. Negative is unlimited")
    arg_parser.add_argument("-u", "--url",type=str, default="https://httpbin.org", help="Set the website to proxy for. ")
    args = arg_parser.parse_args()


    server = web.Application()
    server.router.add_route("*", "/{tail:.*}", Handler)
    Handler.setup(max_size=args.size, ttl=args.ttl, url=args.url)
    server.cleanup_ctx.append(Handler.setup_session)
    web.run_app(server, host="localhost", port=3000)