"""Polite HTTP access to startup.jobs: robots.txt, fixed pace, honest identity."""

import logging
import threading
import time
from typing import Self
from urllib.robotparser import RobotFileParser

import httpx

from app.crawler.urls import ROBOTS_URL, is_forbidden

log = logging.getLogger(__name__)


class CrawlerError(Exception):
    """A problem that stops the current crawl run."""


class CrawlCancelled(CrawlerError):
    """The user asked to stop (dashboard Stop button)."""


class BlockedError(CrawlerError):
    """HTTP 403 or 429: the site asked us to stop.

    We never work around this (no browser disguise, no stealth plugins, no proxy
    rotation). The pipeline may switch to the official API instead.
    """


class PoliteFetcher:
    """Downloads pages one at a time, waiting `delay` seconds between requests."""

    def __init__(
        self,
        user_agent: str,
        delay: float,
        timeout: float = 30.0,
        stop_event: threading.Event | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.delay = delay
        self.stop_event = stop_event or threading.Event()
        self._last_request = 0.0
        self._robots: RobotFileParser | None = None
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml",
            },
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    # -- robots.txt ---------------------------------------------------------
    def load_robots(self) -> None:
        """Read robots.txt once. Refuse to crawl if it cannot be read (fail safe)."""
        response = self._request(ROBOTS_URL)
        if response is None:
            raise CrawlerError("Could not read robots.txt - not crawling without it.")
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        self._robots = parser
        site_delay = parser.crawl_delay(self.user_agent)
        if site_delay and float(site_delay) > self.delay:
            log.info("robots.txt asks for %ss between requests; using it.", site_delay)
            self.delay = float(site_delay)

    def allowed(self, url: str) -> bool:
        if self._robots is None:
            raise CrawlerError("load_robots() must be called before crawling.")
        return self._robots.can_fetch(self.user_agent, url) and not is_forbidden(url)

    # -- downloading --------------------------------------------------------
    def get_html(self, url: str) -> str | None:
        """Return the page HTML, or None if this one page could not be fetched."""
        if not self.allowed(url):
            log.info("Skipping %s (disallowed by robots.txt or our own rules)", url)
            return None
        response = self._request(url)
        return response.text if response is not None else None

    def _request(self, url: str, retries: int = 2) -> httpx.Response | None:
        for attempt in range(1, retries + 2):
            wait = max(0.0, self.delay - (time.monotonic() - self._last_request))
            # Event.wait sleeps like time.sleep, but wakes up at once if Stop is pressed.
            if self.stop_event.wait(wait):
                raise CrawlCancelled("Stopped by user")
            try:
                response = self._client.get(url)
            except httpx.TransportError as error:
                log.warning(
                    "Network problem on %s (attempt %d): %s", url, attempt, error
                )
                continue
            finally:
                self._last_request = time.monotonic()

            if response.status_code in (403, 429):
                raise BlockedError(f"Server answered {response.status_code} for {url}")
            if response.status_code >= 500:
                log.warning(
                    "Server error %s on %s (attempt %d)",
                    response.status_code,
                    url,
                    attempt,
                )
                continue
            if response.status_code != 200:
                log.warning("Skipping %s (HTTP %s)", url, response.status_code)
                return None
            return response
        return None
