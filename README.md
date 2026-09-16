# Caching Proxy 

A small HTTP caching proxy built on `aiohttp`. It forwards requests to an upstream and caches the responses if allowed to. Then serves repeat requests from the cache until they expire.

## Features 

- In memory Least Recently Used cache with a configurable max size.
- Async request forwarding.
- TTL that respects upstream max-age and no-store controls.
- Strips the hop by hop headers before storing and forwarding the response.
- Adds a `X-Cache` header so you can see if the proxy cache hit or not from the header.

## Requirements 
- Python 3.10+
- `aiohttp`

```bash
pip install aiohttp
```

## Usage
```bash
python caching_proxy.py [-s SIZE] [-t TTL] [-u URL]
```
Proxy listens on `http://localhost:3000`.

### Options
| Flag | Default | Description |
| --- | --- | --- |
|`-s`,`--size` | `-1` | Max number of cached entries. Negative means unlimited. |
|`-t`, `--ttl` | `86400` | Default time to live in seconds for cached entries. Negative means they won't expire. Will respect upstream caching max-age and no-store regardless of this value. |
|`-u`, `--url` | `https://httpbin.org` | Sets the upstream to proxy requests to. |

### Example
```bash
# Proxies example.com, keep at most 100 cached entries, and expire them after 60 seconds.
python caching_proxy.py -u https://example.com -s 100 -t 60
```
Then send requests to the proxy instead of the origin using browser or curl.

Curl:
```bash
# add .exe after curl if using PowerShell.
curl -i http://localhost:3000/get     # X-Cache: Miss
curl -i http://localhost:3000/get     # X-Cache: Hit
```

## How it works
1. A request arrives and the proxy checks to see if that path is in the cache.
2. On hit, checks to see if it has expired if not it is removed and reinserted into the cache to update the LRU, then is forwarding to the requester.
3. On miss or expired, the request is forwarded upstream. The response is cached if there isn't a `no-store` in the cache control header and is sent to the requester.
4. The expiry age uses the upstream `max-age` if there is one, else it uses the set ttl.
5. When the cache exceeds its `--size` it evicts the LRU response.
 
The cache lives in memory and isn't written to disk so stopping the proxy clears it.
## Notes / Limitations
- Only works on `GET` requests.
- Many headers aren't taken into consideration. Ex `private`, `Accept-Language`, etc


