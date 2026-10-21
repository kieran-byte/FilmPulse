"""Data loading for the FilmPulse weekly reporting app.

``load_datasets()`` reads the four project CSV files from ``data/`` when they
exist and falls back to built-in synthetic demo data for any file that is
missing, so the app always runs out of the box.

Expected CSV columns (see README.md):

- ``search_interest.csv``: date, film, interest
- ``social_posts.csv``: post_id, date, film, platform, post_label,
  post_type, likes, comments_count, shares, views, url
- ``comments.csv``: date, film, platform, theme, sentiment, comment_text,
  source_url
- ``campaign_events.csv``: date, film, event_type, description, source_url
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATASET_NAMES = ("search_interest", "social_posts", "comments", "campaign_events")

_DEMO_FILMS = ("Harbour of Light", "Nullarbor Run", "The Paper Coast", "Wintering")
_FOCUS_FILM = "Harbour of Light"
_DEMO_PLATFORMS = ("Instagram", "TikTok", "Facebook", "YouTube")

_POST_TEMPLATES = (
    ("Teaser trailer launch", "video"),
    ("Behind-the-scenes featurette", "video"),
    ("Cast interview clip", "video"),
    ("Poster reveal", "image"),
    ("Fan Q&A announcement", "image"),
    ("Countdown reminder", "image"),
    ("Review roundup", "carousel"),
    ("Cinema spot", "video"),
)

_COMMENT_SNIPPETS = {
    "Cast": (
        "The lead performance looks incredible, awards-worthy.",
        "Not sure about this casting choice for the role.",
        "Love seeing more Australian actors in big releases.",
        "The supporting cast announcement got me interested.",
    ),
    "Story": (
        "The trailer gives away too much of the plot.",
        "Really intrigued by the story premise.",
        "Hope the screenplay does the book justice.",
        "Confused by the timeline in the teaser.",
    ),
    "Release date": (
        "When does it open in Australian cinemas?",
        "Is there a Sydney premiere screening?",
        "Release date keeps moving, which is frustrating.",
        "Finally, a release date we can plan around.",
    ),
    "Soundtrack": (
        "That track in the trailer is stunning.",
        "Who composed the score? It sounds familiar.",
        "The music really lifts the teaser.",
        "Not a fan of the song choice in the latest spot.",
    ),
    "Visuals": (
        "The cinematography looks gorgeous.",
        "Outback landscapes look unreal on the big screen.",
        "Visual effects seem a bit rough in places.",
        "Beautiful colour grade in the trailer.",
    ),
}

_EVENT_SPECS = (
    (-80, "Teaser release", "30-second teaser released across owned channels."),
    (-63, "Cast interview", "Lead cast interview on national breakfast television."),
    (-49, "Trailer release", "Full trailer launched on YouTube and social channels."),
    (-35, "Paid media", "Paid social and search flight begins nationally."),
    (-21, "Partnership", "Co-promotion announced with a national cinema chain."),
    (-14, "Premiere", "Sydney premiere and red-carpet event."),
    (-6, "Advance screenings", "Word-of-mouth advance screenings in capital cities."),
)


def load_datasets(data_dir: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Return the four project datasets keyed by dataset name.

    Each dataset is read from ``<data_dir>/<name>.csv`` when the file exists;
    otherwise synthetic demo data is used for that dataset.
    """
    directory = Path(data_dir) if data_dir is not None else DATA_DIR
    demo = _demo_datasets()
    datasets: dict[str, pd.DataFrame] = {}
    for name in DATASET_NAMES:
        frame = _read_csv(directory / f"{name}.csv")
        datasets[name] = frame if frame is not None else demo[name]
    return datasets


def _read_csv(path: Path) -> pd.DataFrame | None:
    """Read a CSV if present, parsing the ``date`` column when it exists."""
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame


def _demo_datasets() -> dict[str, pd.DataFrame]:
    """Build a coherent set of synthetic demo datasets (deterministic)."""
    rng = np.random.default_rng(42)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=84, freq="D")
    return {
        "search_interest": _demo_search_interest(rng, dates),
        "social_posts": _demo_social_posts(rng, dates),
        "comments": _demo_comments(rng, dates),
        "campaign_events": _demo_campaign_events(dates),
    }


def _demo_search_interest(
    rng: np.random.Generator, dates: pd.DatetimeIndex
) -> pd.DataFrame:
    # (base level, daily trend) per film; the focus title rises over the period.
    profiles = {
        "Harbour of Light": (36.0, 0.38),
        "Nullarbor Run": (52.0, 0.02),
        "The Paper Coast": (29.0, 0.08),
        "Wintering": (47.0, -0.06),
    }
    positions = np.arange(len(dates))
    weekly_wave = 5.0 * np.sin(positions / 7.0 * 2 * np.pi)
    frames = []
    for film in _DEMO_FILMS:
        base, slope = profiles[film]
        interest = (
            base
            + slope * positions
            + weekly_wave
            + rng.normal(0.0, 3.5, len(dates))
        )
        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "film": film,
                    "interest": np.clip(interest, 1, 100).round().astype(int),
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def _demo_social_posts(
    rng: np.random.Generator, dates: pd.DatetimeIndex
) -> pd.DataFrame:
    rows = []
    post_number = 0
    for film in _DEMO_FILMS:
        post_count = 26 if film == _FOCUS_FILM else 8
        for _ in range(post_count):
            post_number += 1
            label, post_type = _POST_TEMPLATES[rng.integers(len(_POST_TEMPLATES))]
            platform = _DEMO_PLATFORMS[rng.integers(len(_DEMO_PLATFORMS))]
            views = int(rng.integers(2_000, 120_000))
            likes = int(views * rng.uniform(0.01, 0.08))
            rows.append(
                {
                    "post_id": f"P{post_number:03d}",
                    "date": dates[rng.integers(len(dates))],
                    "film": film,
                    "platform": platform,
                    "post_label": label,
                    "post_type": post_type,
                    "likes": likes,
                    "comments_count": int(likes * rng.uniform(0.05, 0.25)),
                    "shares": int(likes * rng.uniform(0.10, 0.40)),
                    "views": views,
                    "url": f"https://social.example.com/{platform.lower()}/{post_number:03d}",
                }
            )
    return pd.DataFrame(rows).sort_values("date", ignore_index=True)


def _demo_comments(
    rng: np.random.Generator, dates: pd.DatetimeIndex
) -> pd.DataFrame:
    themes = tuple(_COMMENT_SNIPPETS)
    rows = []
    for film in _DEMO_FILMS:
        comment_count = 90 if film == _FOCUS_FILM else 24
        for _ in range(comment_count):
            theme = themes[rng.integers(len(themes))]
            snippets = _COMMENT_SNIPPETS[theme]
            rows.append(
                {
                    "date": dates[rng.integers(len(dates))],
                    "film": film,
                    "platform": _DEMO_PLATFORMS[rng.integers(len(_DEMO_PLATFORMS))],
                    "theme": theme,
                    "sentiment": rng.choice(
                        ["positive", "neutral", "negative"], p=[0.5, 0.3, 0.2]
                    ),
                    "comment_text": snippets[rng.integers(len(snippets))],
                    "source_url": "https://comments.example.com/demo",
                }
            )
    return pd.DataFrame(rows).sort_values("date", ignore_index=True)


def _demo_campaign_events(dates: pd.DatetimeIndex) -> pd.DataFrame:
    period_end = dates[-1]
    rows = [
        {
            "date": period_end + pd.Timedelta(days=offset),
            "film": _FOCUS_FILM,
            "event_type": event_type,
            "description": description,
            "source_url": "https://press.example.com/demo",
        }
        for offset, event_type, description in _EVENT_SPECS
    ]
    rows.append(
        {
            "date": period_end - pd.Timedelta(days=30),
            "film": "Nullarbor Run",
            "event_type": "Trailer release",
            "description": "Official trailer launch for the comparable title.",
            "source_url": "https://press.example.com/demo",
        }
    )
    return pd.DataFrame(rows).sort_values("date", ignore_index=True)
