"""Abstract base class for all research/scraping providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawPost:
    platform: str
    external_id: str | None
    content_url: str | None
    author_handle: str | None
    caption: str | None
    hashtags: list[str] = field(default_factory=list)
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: int = 0
    followers: int = 0
    raw_metadata: dict = field(default_factory=dict)

    def engagement_score(self) -> float:
        """Weighted engagement rate normalised by reach."""
        weighted = self.likes * 1 + self.comments * 3 + self.saves * 4 + self.shares * 5
        reach = max(self.views, self.followers, 1)
        return weighted / reach


class ResearchProvider(ABC):
    platform: str = ""

    @abstractmethod
    async def fetch_trending(self, keywords: list[str], limit: int = 20) -> list[RawPost]:
        """Fetch trending posts for the given keywords."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is operational."""
        ...
