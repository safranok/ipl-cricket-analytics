import io
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="IPL Match Analytics", page_icon="🏏", layout="wide")

# ---------- Palette (clean corporate: one blue accent + neutral greys) ----------
BLUE, NAVY, ORANGE, TEAL = "#0F6CBD", "#1B2A41", "#E8833A", "#2A9D8F"
GREY, GRID, BG = "#6B7280", "#E5E7EB", "#F5F7FA"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family:'Inter','Segoe UI',sans-serif; }}
.stApp {{ background:{BG}; color:{NAVY}; }}
header[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ padding-top:1.5rem; padding-bottom:3rem; max-width:1400px; }}
.topbar {{ background:white; border:1px solid {GRID}; border-left:5px solid {BLUE};
  border-radius:8px; padding:16px 22px; margin-bottom:18px; }}
.topbar h1 {{ font-size:1.5rem; font-weight:700; margin:0; color:{NAVY}; }}
.topbar p {{ margin:4px 0 0; color:{GREY}; font-size:.92rem; }}
.card {{ background:white; border:1px solid {GRID}; border-radius:8px; padding:16px 20px; min-height:112px; }}
.card .l {{ color:{GREY}; font-size:.75rem; font-weight:600; text-transform:uppercase; letter-spacing:.6px; }}
.card .v {{ color:{NAVY}; font-size:1.7rem; font-weight:700; margin-top:6px; line-height:1.15; }}
.card .n {{ color:{GREY}; font-size:.78rem; margin-top:4px; }}
.card.accent {{ border-top:3px solid {BLUE}; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background:white; border-radius:8px; border-color:{GRID}; }}
.ctitle {{ font-size:1rem; font-weight:600; color:{NAVY}; margin:0; }}
.csub {{ font-size:.8rem; color:{GREY}; margin:2px 0 8px; }}
label[data-testid="stWidgetLabel"] p {{ font-size:.74rem !important; color:{GREY} !important; font-weight:600; }}
.stTabs [data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid {GRID}; }}
.stTabs [data-baseweb="tab"] {{ padding:8px 18px; font-weight:600; color:{GREY}; }}
.stTabs [aria-selected="true"] {{ color:{BLUE}; }}
.note {{ color:{GREY}; font-size:.8rem; }}
[data-testid="stFileUploader"] section {{ background:white; border:1px dashed #9CA3AF; }}
[data-testid="stFileUploader"] section * {{ color:{NAVY} !important; }}
[data-testid="stFileUploader"] button {{ background:white; border:1px solid {BLUE}; color:{BLUE} !important; }}
div[data-baseweb="select"] > div {{ background:white; border-color:{GRID}; }}
div[data-baseweb="select"] * {{ color:{NAVY} !important; }}
div[data-baseweb="popover"] ul {{ background:white; }}
div[data-baseweb="popover"] li {{ color:{NAVY}; }}
.stTabs [data-baseweb="tab"] p {{ color:inherit; }}
</style>
""", unsafe_allow_html=True)


# ---------- Helpers ----------
def card(label, value, note="", accent=False):
    cls = "card accent" if accent else "card"
    st.markdown(f'<div class="{cls}"><div class="l">{label}</div><div class="v">{value}</div>'
                f'<div class="n">{note}</div></div>', unsafe_allow_html=True)


def head(title, sub=""):
    st.markdown(f'<p class="ctitle">{title}</p><p class="csub">{sub}</p>', unsafe_allow_html=True)


def style(fig, height=320, legend=True):
    fig.update_layout(
        height=height, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=NAVY),
        margin=dict(l=10, r=10, t=10, b=10), showlegend=legend,
        legend=dict(orientation="h", y=1.12, x=0, title=None),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=GREY))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=GREY))
    return fig


def season_axis(fig):
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=seasons)
    return fig


def wilson(k, n, z=1.96):
    if n == 0:
        return 0, 0, 0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - w, c + w


REQUIRED = ["match_id", "season", "match_date", "team1", "team2", "venue", "toss_winner",
            "toss_decision", "match_winner", "win_by_runs", "win_by_wickets", "result"]
OPTIONAL = ["city", "player_of_match"]


@st.cache_data(show_spinner=False)
def read_raw(raw: bytes):
    try:
        d = pd.read_csv(io.BytesIO(raw))
    except UnicodeDecodeError:
        d = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    d.columns = [str(c).strip() for c in d.columns]
    return d


@st.cache_data(show_spinner=False)
def prepare(d):
    d = d.copy()
    for c in OPTIONAL:
        if c not in d.columns:
            d[c] = pd.NA
    d["match_date"] = pd.to_datetime(d["match_date"], errors="coerce")
    d["season"] = d["season"].astype(str)
    d["win_by_runs"] = pd.to_numeric(d["win_by_runs"], errors="coerce")
    d["win_by_wickets"] = pd.to_numeric(d["win_by_wickets"], errors="coerce")
    d["chase_win"] = d["win_by_wickets"].notna()
    d["defend_win"] = d["win_by_runs"].notna()
    return d


st.markdown('<div class="topbar"><h1>IPL Match Analytics</h1>'
            '<p>How scoring patterns, chasing and toss decisions have shaped IPL matches.</p></div>',
            unsafe_allow_html=True)

# ---------- Data source: nothing is shown until a valid file is uploaded ----------
with st.container(border=True):
    head("Upload data", "Upload the IPL matches.csv file to start. No data is shown until you do.")
    up = st.file_uploader("matches.csv", type=["csv"], label_visibility="collapsed")

if up is None:
    st.info("Upload your matches.csv file above to see the dashboard.")
    st.stop()

try:
    raw_df = read_raw(up.getvalue())
except Exception:
    st.error("This file could not be read as a CSV. Please upload a valid matches.csv file.")
    st.stop()

if raw_df.empty:
    st.error("This file has no rows. Please upload a matches.csv file with match records.")
    st.stop()

missing = [c for c in REQUIRED if c not in raw_df.columns]
if missing:
    st.error(f"This does not look like the IPL matches file ({up.name}). "
             f"Missing columns: {', '.join(missing)}.")
    st.caption("Please upload matches.csv, not another table such as deliveries.csv.")
    st.stop()

df = prepare(raw_df)
if df["match_date"].isna().all():
    st.error("The match_date column could not be read as dates. Please check the file.")
    st.stop()

seasons = list(df.groupby("season")["match_date"].min().sort_values().index)
teams = sorted(set(df["team1"].dropna()) | set(df["team2"].dropna()))


def subset(d, rng=None, season=None, team=None):
    if rng:
        i0, i1 = seasons.index(rng[0]), seasons.index(rng[1])
        d = d[d["season"].isin(seasons[i0:i1 + 1])]
    if season and season != "All seasons":
        d = d[d["season"] == season]
    if team and team != "All teams":
        d = d[(d["team1"] == team) | (d["team2"] == team)]
    return d



tab_over, tab_match = st.tabs(["Overview", "Match"])

# =====================================================================
# TAB 1 - OVERVIEW
# =====================================================================
with tab_over:
    decided = df[df["chase_win"] | df["defend_win"]]
    k, n = int(decided["chase_win"].sum()), len(decided)
    p, lo, hi = wilson(k, n)
    try:
        from scipy.stats import binomtest
        pv = binomtest(k, n, 0.5).pvalue
        ptxt = "p < 0.001" if pv < 0.001 else f"p = {pv:.3f}"
    except Exception:
        ptxt = "p-value n/a"

    c1, c2, c3 = st.columns(3)
    with c1:
        card("Matches &amp; seasons", f"{len(df):,} &middot; {len(seasons)}",
             "Fixed - does not change with filters", True)
    with c2:
        tw = df[df["result"] == "win"]
        share = (tw["toss_winner"] == tw["match_winner"]).mean() * 100
        card("Toss winner also wins match", f"{share:.1f}%", f"{len(tw):,} decided matches", True)
    with c3:
        card("Chasing teams win", f"{p*100:.1f}%",
             f"95% CI {lo*100:.1f}-{hi*100:.1f}% &middot; binomial test vs 50%, {ptxt}", True)

    st.write("")

    # --- Hero: chase win rate by season ---
    with st.container(border=True):
        head("Chasing win rate by season",
             "Share of decided matches won by the team batting second. Dashed line = 50%.")
        f1, f2 = st.columns(2)
        rng = f1.select_slider("Seasons", options=seasons, value=(seasons[0], seasons[-1]), key="h_rng")
        tm = f2.selectbox("Team", ["All teams"] + teams, key="h_team")
        d = subset(decided, rng=rng, team=tm)
        if d.empty:
            st.info("No matches for this filter.")
        else:
            g = d.groupby("season").agg(rate=("chase_win", "mean"), n=("chase_win", "size")).reindex(
                [s for s in seasons if s in d["season"].unique()]).reset_index()
            fig = go.Figure(go.Scatter(
                x=g["season"], y=g["rate"] * 100, mode="lines+markers",
                line=dict(color=BLUE, width=3), marker=dict(size=8),
                customdata=g["n"], hovertemplate="%{x}<br>%{y:.1f}% chased wins<br>n=%{customdata}<extra></extra>"))
            fig.add_hline(y=50, line_dash="dash", line_color=GREY)
            fig.update_yaxes(title="Chasing win %", range=[0, 100])
            st.plotly_chart(season_axis(style(fig, 400, False)), use_container_width=True)

    st.write("")
    a, b = st.columns(2)

    # --- Runs vs wickets ---
    with a.container(border=True):
        head("Wins by runs vs wickets", "Defending teams win by runs, chasing teams win by wickets.")
        f1, f2 = st.columns(2)
        rng = f1.select_slider("Seasons", options=seasons, value=(seasons[0], seasons[-1]), key="rw_rng")
        tm = f2.selectbox("Team", ["All teams"] + teams, key="rw_team")
        d = subset(decided, rng=rng, team=tm)
        if d.empty:
            st.info("No matches for this filter.")
        else:
            g = d.groupby("season").agg(runs=("defend_win", "sum"), wk=("chase_win", "sum")).reindex(
                [s for s in seasons if s in d["season"].unique()]).reset_index()
            fig = go.Figure([go.Bar(x=g["season"], y=g["runs"], name="Won by runs", marker_color=BLUE),
                             go.Bar(x=g["season"], y=g["wk"], name="Won by wickets", marker_color=ORANGE)])
            fig.update_layout(barmode="stack")
            st.plotly_chart(season_axis(style(fig)), use_container_width=True)

    # --- Toss decision ---
    with b.container(border=True):
        head("Toss decision by season", "What the toss winner chose to do.")
        f1, f2 = st.columns(2)
        rng = f1.select_slider("Seasons", options=seasons, value=(seasons[0], seasons[-1]), key="t_rng")
        tm = f2.selectbox("Team", ["All teams"] + teams, key="t_team")
        d = subset(df, rng=rng, team=tm)
        if tm != "All teams":
            d = d[d["toss_winner"] == tm]
        if d.empty:
            st.info("No matches for this filter.")
        else:
            g = d.groupby(["season", "toss_decision"]).size().unstack(fill_value=0).reindex(
                [s for s in seasons if s in d["season"].unique()]).reset_index()
            fig = go.Figure()
            for col, colr in (("bat", TEAL), ("field", BLUE)):
                if col in g:
                    fig.add_bar(x=g["season"], y=g[col], name=col.capitalize(), marker_color=colr)
            fig.update_layout(barmode="stack")
            st.plotly_chart(season_axis(style(fig)), use_container_width=True)

    st.write("")
    a, b = st.columns(2)

    # --- Wins by team ---
    with a.container(border=True):
        head("Most successful teams", "Total match wins.")
        f1, f2 = st.columns(2)
        se = f1.selectbox("Season", ["All seasons"] + seasons, key="w_season")
        top = f2.selectbox("Show top", [5, 8, 10, 15], index=2, key="w_top")
        d = subset(df[df["result"] == "win"], season=se)
        if d.empty:
            st.info("No matches for this filter.")
        else:
            g = d["match_winner"].value_counts().head(top).sort_values().reset_index()
            g.columns = ["team", "wins"]
            fig = go.Figure(go.Bar(x=g["wins"], y=g["team"], orientation="h", marker_color=BLUE,
                                   text=g["wins"], textposition="outside"))
            st.plotly_chart(style(fig, 340, False), use_container_width=True)

    # --- Venues ---
    with b.container(border=True):
        head("Busiest venues", "Matches hosted.")
        f1, f2 = st.columns(2)
        se = f1.selectbox("Season", ["All seasons"] + seasons, key="v_season")
        top = f2.selectbox("Show top", [5, 8, 10, 15], index=2, key="v_top")
        d = subset(df, season=se)
        if d.empty:
            st.info("No matches for this filter.")
        else:
            g = d["venue"].value_counts().head(top).sort_values().reset_index()
            g.columns = ["venue", "matches"]
            fig = go.Figure(go.Bar(x=g["matches"], y=g["venue"], orientation="h", marker_color=TEAL,
                                   text=g["matches"], textposition="outside"))
            st.plotly_chart(style(fig, 340, False), use_container_width=True)

# =====================================================================
# TAB 2 - MATCH
# =====================================================================
with tab_match:
    with st.container(border=True):
        head("Select a match", "Season and team narrow the list; every card and chart below updates.")
        f1, f2, f3 = st.columns([1, 1, 2.4])
        se = f1.selectbox("Season", ["All seasons"] + seasons, key="m_season")
        pool = subset(df, season=se)
        tl = sorted(set(pool["team1"].dropna()) | set(pool["team2"].dropna()))
        tm = f2.selectbox("Team", ["All teams"] + tl, key="m_team")
        pool = subset(pool, team=tm).sort_values("match_date", ascending=False)
        if pool.empty:
            f3.selectbox("Match", ["-"], disabled=True)
            st.warning("No matches for this season and team.")
            st.stop()
        labels = {r.match_id: f"{r.team1} vs {r.team2} | {r.venue} | {r.season}" for r in pool.itertuples()}
        mid = f3.selectbox("Match", list(labels), format_func=labels.get, key=f"m_pick_{se}_{tm}")

    m = df[df["match_id"] == mid].iloc[0]
    if m["result"] == "win":
        if pd.notna(m["win_by_runs"]):
            res = f"{m['match_winner']} won by {int(m['win_by_runs'])} runs"
        else:
            res = f"{m['match_winner']} won by {int(m['win_by_wickets'])} wickets"
    elif m["result"] == "tie":
        res = "Match tied"
    else:
        res = "No result"

    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1:
        card("Result", res, f"{m['match_date']:%d %b %Y} &middot; {m['venue']}", True)
    with c2:
        card("Toss", f"{m['toss_winner']}", f"Chose to {m['toss_decision']}", True)
    with c3:
        card("Player of the match", f"&#9733; {m['player_of_match'] if pd.notna(m['player_of_match']) else 'Not awarded'}",
             "Award winner", True)

    st.write("")
    a, b = st.columns(2)
    t1, t2 = m["team1"], m["team2"]

    with a.container(border=True):
        head(f"Head to head: {t1} vs {t2}", "Wins in all IPL meetings between these two teams.")
        rng = st.select_slider("Seasons", options=seasons, value=(seasons[0], seasons[-1]), key="hh_rng")
        d = subset(df, rng=rng)
        d = d[((d["team1"] == t1) & (d["team2"] == t2)) | ((d["team1"] == t2) & (d["team2"] == t1))]
        if d.empty:
            st.info("No meetings in this range.")
        else:
            w = d["match_winner"].value_counts()
            vals = [int(w.get(t1, 0)), int(w.get(t2, 0)), int(len(d) - w.get(t1, 0) - w.get(t2, 0))]
            fig = go.Figure(go.Bar(x=[t1, t2, "No result / tie"], y=vals,
                                   marker_color=[BLUE, ORANGE, "#B8C0CC"], text=vals, textposition="outside"))
            st.plotly_chart(style(fig, 300, False), use_container_width=True)
            st.caption(f"{len(d)} meetings")

    with b.container(border=True):
        head(f"At {m['venue']}", "Does batting first or chasing win more here?")
        rng = st.select_slider("Seasons", options=seasons, value=(seasons[0], seasons[-1]), key="vn_rng")
        d = subset(df, rng=rng)
        d = d[(d["venue"] == m["venue"]) & (d["chase_win"] | d["defend_win"])]
        if d.empty:
            st.info("No decided matches at this venue in this range.")
        else:
            vals = [int(d["defend_win"].sum()), int(d["chase_win"].sum())]
            fig = go.Figure(go.Bar(x=["Batting first won", "Chasing won"], y=vals,
                                   marker_color=[BLUE, ORANGE], text=vals, textposition="outside"))
            st.plotly_chart(style(fig, 300, False), use_container_width=True)
            st.caption(f"{len(d)} decided matches")

    st.write("")
    with st.container(border=True):
        head("Match facts")
        facts = pd.DataFrame({
            "Item": ["Teams", "Venue", "City", "Date", "Season", "Toss", "Result", "Player of the match"],
            "Detail": [f"{t1} vs {t2}", m["venue"], m["city"], f"{m['match_date']:%d %b %Y}", m["season"],
                       f"{m['toss_winner']} chose to {m['toss_decision']}", res,
                       f"* {m['player_of_match']}" if pd.notna(m["player_of_match"]) else "Not awarded"],
        })
        st.dataframe(facts, hide_index=True, use_container_width=True)
    st.markdown('<p class="note">Runs per over, fours/sixes and top scorers need ball-by-ball data '
                '(deliveries.csv). Add it to show those charts.</p>', unsafe_allow_html=True)