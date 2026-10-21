# FilmPulse Weekly Campaign Reporting
# Save as marimo_app.py

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell
def _():
    import pandas as pd
    import plotly.express as px
    import marimo as mo


    from src.data import load_datasets
    from src.reporting import generate_weekly_report

    return generate_weekly_report, load_datasets, mo, pd, px


@app.cell
def _(mo):
    mo.md("""
    # FilmPulse
    ### Weekly film campaign reporting

    Track search interest, owned social performance, audience conversation,
    and practical actions for the next reporting period.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    **Data note:** Demo data is synthetic. Replace it with your own CSV files
    or authorised platform exports before using the results for real decisions.
    Search interest is a relative index, not absolute search volume.
    """)
    return


@app.cell
def _(load_datasets, mo):
    datasets = load_datasets()
    demo_notice = mo.md(
        "Using the project's configured datasets. Check the README for CSV formats."
    )
    return datasets, demo_notice


@app.cell
def _(datasets, mo, pd):
    search = datasets["search_interest"].copy()
    posts = datasets["social_posts"].copy()
    comments = datasets["comments"].copy()
    events = datasets["campaign_events"].copy()

    for frame in [search, posts, comments, events]:
        if "date" in frame.columns:
            frame["date"] = pd.to_datetime(frame["date"], errors="coerce")

    films = sorted(
        set(search["film"].dropna())
        | set(posts["film"].dropna())
        | set(comments["film"].dropna())
    )

    if not films:
        mo.stop(
            True,
            mo.md(
                "## No film titles found\n"
                "Check your input CSV files and confirm that they contain a `film` column."
            ),
        )
    return comments, events, films, posts, search


@app.cell
def _(films, mo):
    film_ui = mo.ui.dropdown(
        options=films,
        value=films[0],
        label="Focus film",
    )
    return (film_ui,)


@app.cell
def _(film_ui, films, mo):
    comparison_options = [
        film for film in films if film != film_ui.value
    ]

    comparison_ui = mo.ui.multiselect(
        options=comparison_options,
        value=comparison_options[:2],
        label="Comparable titles",
    )
    return (comparison_ui,)


@app.cell
def _(mo):
    mo.md("""
    ## Reporting period
    """)
    return


@app.cell
def _(mo, search):
    valid_dates = search["date"].dropna()

    if valid_dates.empty:
        mo.stop(
            True,
            mo.md(
                "No valid dates were found in the search-interest data. "
                "Check the `date` column in your CSV."
            ),
        )

    date_min = valid_dates.min().date()
    date_max = valid_dates.max().date()

    date_ui = mo.ui.date_range(
        start=date_min,
        stop=date_max,
        value=(date_min, date_max),
        label="Reporting period",
    )
    return (date_ui,)


@app.cell
def _(comparison_ui, date_ui, demo_notice, film_ui, mo):
    mo.vstack(
        [
            demo_notice,
            mo.hstack(
                [film_ui, comparison_ui],
                justify="start",
                gap=2,
            ),
            date_ui,
        ]
    )
    return


@app.cell
def _(comparison_ui, date_ui, events, film_ui, posts, search):
    focus_film = film_ui.value
    comparison_films = comparison_ui.value

    selected_dates = date_ui.value
    if selected_dates and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = search["date"].min().date()
        end_date = search["date"].max().date()

    start_ts = __import__("pandas").Timestamp(start_date)
    end_ts = __import__("pandas").Timestamp(end_date)

    selected_films = [focus_film] + list(comparison_films)

    search_period = search[
        search["film"].isin(selected_films)
        & search["date"].between(start_ts, end_ts)
    ].copy()

    posts_period = posts[
        posts["film"].eq(focus_film)
        & posts["date"].between(start_ts, end_ts)
    ].copy()

    events_period = events[
        events["date"].between(start_ts, end_ts)
    ].copy()
    return (
        comparison_films,
        end_date,
        events_period,
        focus_film,
        posts_period,
        search_period,
        start_date,
    )


@app.cell
def _(mo):
    mo.md("""
    ## 1. Search interest and competitor comparison
    """)
    return


@app.cell
def _(mo, px, search_period):
    if search_period.empty:
        search_chart = mo.md(
            "No search-interest data is available for the selected period and titles."
        )
    else:
        search_chart = px.line(
            search_period.sort_values("date"),
            x="date",
            y="interest",
            color="film",
            markers=True,
            title="Relative search interest over time",
            labels={
                "date": "Date",
                "interest": "Relative interest index",
                "film": "Film",
            },
        )
        search_chart.update_layout(legend_title_text="Film")

    search_chart
    return


@app.cell
def _(events_period, mo):
    if events_period.empty:
        event_table = mo.md("No campaign events fall within the selected reporting period.")
    else:
        event_table = mo.ui.table(events_period, selection=None)

    mo.vstack(
        [
            mo.md("### Campaign events in this period"),
            event_table,
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 2. Owned social performance
    """)
    return


@app.cell
def _(mo, pd, posts_period):
    if posts_period.empty:
        social_summary = mo.md(
            "No social-post data was found for the focus film during this period."
        )
    else:
        metric_columns = [
            column
            for column in [
                "platform",
                "post_count",
                "impressions",
                "views",
                "likes",
                "comments",
                "shares",
                "engagements",
                "engagement_rate",
            ]
            if column in posts_period.columns
        ]

        if "platform" in posts_period.columns:
            aggregations = {
                column: "sum"
                for column in metric_columns
                if column != "platform"
                and pd.api.types.is_numeric_dtype(posts_period[column])
            }
            social_table = (
                posts_period.groupby("platform", dropna=False)
                .agg(aggregations)
                .reset_index()
                if aggregations
                else posts_period[metric_columns]
            )
        else:
            social_table = posts_period[metric_columns]

        social_summary = mo.ui.table(social_table, selection=None)

    social_summary
    return


@app.cell
def _(mo, posts_period, px):
    if posts_period.empty or "platform" not in posts_period.columns:
        social_chart = mo.md("A platform comparison chart is not available for this dataset.")
    else:
        chart_metric = (
            "engagements"
            if "engagements" in posts_period.columns
            else "views"
            if "views" in posts_period.columns
            else "likes"
            if "likes" in posts_period.columns
            else None
        )

        if chart_metric is None:
            social_chart = mo.md(
                "No compatible engagement or view metric was found in the social-post data."
            )
        else:
            platform_totals = (
                posts_period.groupby("platform", dropna=False)[chart_metric]
                .sum()
                .reset_index()
            )
            social_chart = px.bar(
                platform_totals,
                x="platform",
                y=chart_metric,
                title=f"Performance by platform: {chart_metric}",
                labels={
                    "platform": "Platform",
                    chart_metric: chart_metric.replace("_", " ").title(),
                },
            )

    social_chart
    return


@app.cell
def _(mo, posts_period):
    if posts_period.empty or "post_text" not in posts_period.columns:
        top_posts = mo.md(
            "Post-level ranking requires a `post_text` column in the social-post dataset."
        )
    else:
        ranking_metric = (
            "engagements"
            if "engagements" in posts_period.columns
            else "shares"
            if "shares" in posts_period.columns
            else "likes"
            if "likes" in posts_period.columns
            else None
        )

        if ranking_metric is None:
            top_posts = mo.md(
                "No engagement metric is available for ranking individual posts."
            )
        else:
            ranked_posts = posts_period.sort_values(
                ranking_metric, ascending=False
            ).head(10)

            display_columns = [
                column
                for column in [
                    "date",
                    "platform",
                    "post_text",
                    ranking_metric,
                    "views",
                    "likes",
                    "comments",
                    "shares",
                ]
                if column in ranked_posts.columns
            ]

            top_posts = mo.vstack(
                [
                    mo.md(f"### Top posts by {ranking_metric}"),
                    mo.ui.table(
                        ranked_posts[display_columns],
                        selection=None,
                    ),
                ]
            )

    top_posts
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3. Audience comment themes and sentiment
    """)
    return


@app.cell
def _(comments, end_date, focus_film, start_date):
    comment_period = comments.copy()

    if "date" in comment_period.columns:
        comment_period = comment_period[
            comment_period["date"].between(
                __import__("pandas").Timestamp(start_date),
                __import__("pandas").Timestamp(end_date),
            )
        ]

    if "film" in comment_period.columns:
        comment_period = comment_period[
            comment_period["film"].eq(focus_film)
        ]
    return (comment_period,)


@app.cell
def _(comment_period, mo, px):
    if comment_period.empty:
        comment_summary = mo.md(
            "No audience comments were found for the selected film and period."
        )
    elif "theme" not in comment_period.columns:
        comment_summary = mo.md(
            "Add a `theme` column to the comments CSV to group audience conversation."
        )
    else:
        sentiment_column = (
            "sentiment"
            if "sentiment" in comment_period.columns
            else None
        )

        if sentiment_column:
            theme_summary = (
                comment_period.groupby(
                    ["theme", sentiment_column],
                    dropna=False,
                )
                .size()
                .reset_index(name="comment_count")
            )

            comment_summary = px.bar(
                theme_summary,
                x="theme",
                y="comment_count",
                color=sentiment_column,
                barmode="stack",
                title="Comment themes by supplied sentiment labels",
                labels={
                    "theme": "Theme",
                    "comment_count": "Number of comments",
                    sentiment_column: "Sentiment",
                },
            )
        else:
            theme_summary = (
                comment_period.groupby("theme", dropna=False)
                .size()
                .reset_index(name="comment_count")
                .sort_values("comment_count", ascending=False)
            )

            comment_summary = px.bar(
                theme_summary,
                x="theme",
                y="comment_count",
                title="Most common audience themes",
                labels={
                    "theme": "Theme",
                    "comment_count": "Number of comments",
                },
            )

    comment_summary
    return


@app.cell
def _(comment_period, mo):
    if comment_period.empty:
        comment_examples = mo.md("No comment examples are available.")
    else:
        example_columns = [
            column
            for column in [
                "date",
                "platform",
                "theme",
                "sentiment",
                "comment_text",
            ]
            if column in comment_period.columns
        ]

        if not example_columns:
            comment_examples = mo.md(
                "The comments dataset does not contain recognised display columns."
            )
        else:
            comment_examples = mo.vstack(
                [
                    mo.md("### Comment examples"),
                    mo.ui.table(
                        comment_period[example_columns].head(30),
                        selection=None,
                    ),
                ]
            )

    comment_examples
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Weekly takeaway and recommended actions
    """)
    return


@app.cell
def _(comparison_films, focus_film, mo, posts_period, search_period):
    takeaway_input = mo.ui.text_area(
        label="Weekly takeaway",
        placeholder=(
            "What changed this week? What appears to be driving audience interest?"
        ),
        full_width=True,
    )

    actions_input = mo.ui.text_area(
        label="Recommended actions (2–3)",
        placeholder=(
            "1. Action to take\n"
            "2. Action to take\n"
            "3. Optional action"
        ),
        full_width=True,
    )

    mo.vstack(
        [
            mo.md(
                f"**Focus film:** {focus_film}  \n"
                f"**Comparables:** {', '.join(comparison_films) if comparison_films else 'None selected'}  \n"
                f"**Search observations:** {len(search_period)} rows  \n"
                f"**Social posts analysed:** {len(posts_period)}"
            ),
            takeaway_input,
            actions_input,
        ]
    )
    return actions_input, takeaway_input


@app.cell
def _(
    actions_input,
    comment_period,
    comparison_films,
    end_date,
    events_period,
    focus_film,
    generate_weekly_report,
    mo,
    posts_period,
    search_period,
    start_date,
    takeaway_input,
):
    report = generate_weekly_report(
        focus_film=focus_film,
        comparison_films=list(comparison_films),
        start_date=str(start_date),
        end_date=str(end_date),
        search_interest=search_period,
        social_posts=posts_period,
        comments=comment_period,
        events=events_period,
        takeaway=takeaway_input.value,
        recommended_actions=actions_input.value,
    )

    report_text = (
        report
        if isinstance(report, str)
        else str(report)
    )

    mo.vstack(
        [
            mo.md("### Generated weekly report"),
            mo.md(report_text),
            mo.download(
                data=report_text.encode("utf-8"),
                filename="filmpulse_weekly_report.md",
                mimetype="text/markdown",
                label="Download Markdown report",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
