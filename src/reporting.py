from __future__ import annotations

import re

import pandas as pd


def _pct_change(first: float, last: float):
    if first == 0:
        return None
    return (last - first) / first * 100


def build_weekly_report(film, search, posts, comments, events, start_date, end_date, demo=False):
    evidence = []
    caveats = []
    actions = []

    focus = search[search["film"] == film].sort_values("date") if not search.empty else pd.DataFrame()
    change = None
    if len(focus) >= 4:
        quarter = max(1, len(focus) // 4)
        first = float(focus.head(quarter)["interest"].mean())
        last = float(focus.tail(quarter)["interest"].mean())
        change = _pct_change(first, last)
        evidence.append({
            "Finding": "Search interest",
            "Evidence": f"Average relative interest changed from {first:.1f} to {last:.1f} ({change:+.1f}%).",
            "Interpretation": "Directional change in relative search interest; not absolute search volume."
        })
    else:
        caveats.append("Not enough search observations to calculate a stable period comparison.")

    if not posts.empty:
        p = posts.copy()
        for col in ["likes", "comments_count", "shares", "views"]:
            p[col] = pd.to_numeric(p[col], errors="coerce").fillna(0)
        p["engagements"] = p["likes"] + p["comments_count"] + p["shares"]
        top = p.sort_values("engagements", ascending=False).iloc[0]
        total_eng = float(p["engagements"].sum())
        total_views = float(p["views"].sum())
        rate = total_eng / total_views * 100 if total_views > 0 else None
        evidence.append({
            "Finding": "Social engagement",
            "Evidence": f"{len(p)} posts; {int(total_eng):,} total likes/comments/shares; highest post: {top['post_label']} ({int(top['engagements']):,} interactions).",
            "Interpretation": f"Aggregate engagement rate {rate:.2f}% using interactions/views." if rate is not None else "Views unavailable, so rate cannot be calculated."
        })
        actions.append(f"Review the creative and format of “{top['post_label']}” and test a follow-up variant; verify performance against each platform's own baseline.")
    else:
        caveats.append("No social post data is available for the selected period.")

    if not comments.empty:
        sentiments = comments["sentiment"].astype(str).str.lower()
        positive = float((sentiments == "positive").mean() * 100)
        theme_counts = comments["theme"].fillna("Unclassified").value_counts()
        top_theme = theme_counts.index[0]
        evidence.append({
            "Finding": "Audience conversation",
            "Evidence": f"{len(comments)} comments classified; {positive:.1f}% labelled positive; most common theme: {top_theme} ({int(theme_counts.iloc[0])} comments).",
            "Interpretation": "Sentiment reflects the supplied labels and sample, not necessarily the full Australian audience."
        })
        if top_theme.lower() == "cast":
            actions.append("Share the cast-discussion summary with publicity and assess whether the most-discussed cast members are suitable for upcoming interviews.")
        elif top_theme.lower() in {"story", "plot"}:
            actions.append("Review recurring story or plot questions and consider whether approved campaign materials can answer them clearly.")
        elif top_theme.lower() in {"release date", "availability"}:
            actions.append("Check that Australian release-date and availability information is easy to find across owned channels.")
        else:
            actions.append(f"Review examples from the “{top_theme}” conversation theme and decide whether campaign messaging should respond to it.")
    else:
        caveats.append("No audience comment data is available; sentiment and themes cannot be inferred.")

    if change is not None:
        if change >= 20:
            takeaway = f"**Key takeaway:** Search interest for {film} rose materially across the selected period ({change:+.1f}% comparing the first and last quarters). Check the timing against campaign events before attributing the change to a specific activity."
            actions.append("Overlay paid-media delivery and other campaign beats by date, then compare the pattern with comparable titles before drawing conclusions about what drove the increase.")
        elif change <= -20:
            takeaway = f"**Key takeaway:** Search interest for {film} declined across the selected period ({change:+.1f}% comparing the first and last quarters). Review campaign timing and competitor activity to determine whether the decline is unusual."
            actions.append("Check whether upcoming campaign beats provide a reason to expect renewed interest; if not, test creative or messaging options and measure their results.")
        else:
            takeaway = f"**Key takeaway:** Search interest for {film} was broadly stable across the selected period ({change:+.1f}% comparing the first and last quarters). Use social performance and audience themes to identify which campaign elements merit further testing."
            actions.append("Keep monitoring search interest against comparable titles and look for sustained changes around the next scheduled campaign beat.")
    else:
        takeaway = f"**Key takeaway:** The available data for {film} is not sufficient to calculate a robust search-interest change. Use social performance and audience comments as provisional signals, and improve search-data coverage."

    if not events.empty:
        event_list = ", ".join(events.sort_values("date")["event_type"].dropna().astype(str).unique()[:4])
        evidence.append({
            "Finding": "Campaign context",
            "Evidence": f"{len(events)} campaign events recorded in period; event types include: {event_list}.",
            "Interpretation": "Timing may help contextualise changes, but temporal overlap alone does not prove causation."
        })
    else:
        caveats.append("No campaign events were recorded for the selected titles and period.")

    if len(actions) < 2:
        actions.append("Improve data coverage for the next report by checking missing dates, platform exports and source links.")
    actions = actions[:3]

    caveats.extend([
        "Engagement definitions and available metrics vary by platform; compare like with like.",
        "Search-interest indices are relative and should not be described as absolute search volume.",
        "Comment samples may be incomplete, duplicated or not representative of Australian audiences."
    ])
    if demo:
        caveats.insert(0, "This is synthetic demo data. All findings and recommendations are illustrative only.")

    markdown = [
        f"# Weekly campaign report: {film}",
        f"**Period:** {start_date.date()} to {end_date.date()}",
        "",
        takeaway,
        "",
        "## Recommended actions",
    ]
    markdown.extend([f"{i}. {action}" for i, action in enumerate(actions, 1)])
    markdown += ["", "## Evidence"]
    markdown.extend([f"- **{row['Finding']}:** {row['Evidence']} {row['Interpretation']}" for row in evidence])
    markdown += ["", "## Caveats"]
    markdown.extend([f"- {note}" for note in caveats])

    return {
        "takeaway": takeaway,
        "actions": actions,
        "caveats": caveats,
        "evidence": pd.DataFrame(evidence, columns=["Finding", "Evidence", "Interpretation"]),
        "markdown": "\n".join(markdown),
    }


def _parse_action_lines(text):
    """Split free-text recommended actions (one per line) into a clean list."""
    actions = []
    for line in (text or "").splitlines():
        cleaned = re.sub(r"^\s*(?:\d+[.)]|[-*•>])\s*", "", line).strip()
        if cleaned:
            actions.append(cleaned)
    return actions


def generate_weekly_report(
    focus_film,
    comparison_films=None,
    start_date=None,
    end_date=None,
    search_interest=None,
    social_posts=None,
    comments=None,
    events=None,
    takeaway="",
    recommended_actions="",
):
    """Build the weekly report as a Markdown string.

    Keyword-friendly wrapper around :func:`build_weekly_report` used by the
    marimo app. A user-entered takeaway and recommended actions (one per
    line) override the generated ones when provided; missing datasets are
    treated as empty.
    """
    search = search_interest if search_interest is not None else pd.DataFrame()
    posts = social_posts if social_posts is not None else pd.DataFrame()
    comment_frame = comments if comments is not None else pd.DataFrame()
    event_frame = events if events is not None else pd.DataFrame()

    if start_date is None and not search.empty:
        start_date = search["date"].min()
    if end_date is None and not search.empty:
        end_date = search["date"].max()
    start_ts = (
        pd.Timestamp(start_date)
        if start_date is not None
        else pd.Timestamp.today().normalize()
    )
    end_ts = pd.Timestamp(end_date) if end_date is not None else start_ts

    result = build_weekly_report(
        film=focus_film,
        search=search,
        posts=posts,
        comments=comment_frame,
        events=event_frame,
        start_date=start_ts,
        end_date=end_ts,
    )

    takeaway_text = (takeaway or "").strip()
    if takeaway_text and not takeaway_text.startswith("**Key takeaway:**"):
        takeaway_text = f"**Key takeaway:** {takeaway_text}"
    if not takeaway_text:
        takeaway_text = result["takeaway"]

    actions = _parse_action_lines(recommended_actions) or result["actions"]

    markdown = [
        f"# Weekly campaign report: {focus_film}",
        f"**Period:** {start_ts.date()} to {end_ts.date()}",
    ]
    if comparison_films:
        markdown.append(
            f"**Comparable titles:** {', '.join(str(f) for f in comparison_films)}"
        )
    markdown += ["", takeaway_text, "", "## Recommended actions"]
    markdown.extend(f"{i}. {action}" for i, action in enumerate(actions, 1))
    markdown += ["", "## Evidence"]
    evidence = result["evidence"]
    if evidence.empty:
        markdown.append(
            "- No evidence summaries could be generated for this selection."
        )
    else:
        markdown.extend(
            f"- **{row['Finding']}:** {row['Evidence']} {row['Interpretation']}"
            for _, row in evidence.iterrows()
        )
    markdown += ["", "## Caveats"]
    markdown.extend(f"- {note}" for note in result["caveats"])
    return "\n".join(markdown)
