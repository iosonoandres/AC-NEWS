from dataclasses import dataclass


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str


CATEGORY_FEEDS: dict[str, list[FeedSource]] = {
    "SPORT": [
        FeedSource(name="Gazzetta", url="https://www.gazzetta.it/rss/home.xml"),
        FeedSource(name="ANSA Sport", url="https://www.ansa.it/sito/notizie/sport/sport_rss.xml"),
        FeedSource(name="Sky Sport", url="https://sport.sky.it/rss/sport.xml"),
    ],
    "MODA": [
        FeedSource(name="Vanity Fair", url="https://www.vanityfair.it/feed"),
    ],
    "ECONOMIA": [
        FeedSource(name="Il Sole 24 Ore", url="https://www.ilsole24ore.com/rss/economia.xml"),
        FeedSource(name="ANSA Economia", url="https://www.ansa.it/sito/notizie/economia/economia_rss.xml"),
        FeedSource(name="Wall Street Italia", url="https://www.wallstreetitalia.com/feed/"),
    ],
    "TECNOLOGIA": [
        FeedSource(name="Wired Italia", url="https://www.wired.it/feed/rss"),
        FeedSource(name="ANSA Tecnologia", url="https://www.ansa.it/sito/notizie/tecnologia/tecnologia_rss.xml"),
        FeedSource(name="Agenda Digitale", url="https://www.agendadigitale.eu/feed/"),
    ],
    "CUCINA": [
        FeedSource(name="GialloZafferano", url="https://www.giallozafferano.it/feed/"),
        FeedSource(name="Cookist", url="https://www.cookist.it/feed/"),
    ],
    "ARTE": [
        FeedSource(name="Artribune", url="https://www.artribune.com/feed/"),
        FeedSource(name="Exibart", url="https://www.exibart.com/feed/"),
        FeedSource(name="ANSA Cultura", url="https://www.ansa.it/sito/notizie/cultura/cultura_rss.xml"),
    ],
    "MUSICA": [
        FeedSource(name="Rolling Stone Italia", url="https://www.rollingstone.it/feed/"),
        FeedSource(name="All Music Italia", url="https://www.allmusicitalia.it/feed"),
        FeedSource(name="Soundsblog", url="https://www.soundsblog.it/feed"),
    ],
}
