"""Presentation-only styling for the offline analyst console."""

CSS = """
<style>
:root {
  --cm-bg: #071521;
  --cm-panel: #0d2433;
  --cm-border: rgba(123, 180, 190, .20);
  --cm-text: #eaf5f5;
  --cm-muted: #a6c0c8;
  --cm-teal: #43dbc6;
  --cm-amber: #f4bc6a;
}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(circle at 82% 0%, rgba(34, 102, 116, .28), transparent 34%),
    radial-gradient(circle at 4% 32%, rgba(20, 77, 86, .19), transparent 30%),
    var(--cm-bg);
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0a2130 0%, #081924 100%);
  border-right: 1px solid var(--cm-border);
}
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1460px; padding-top: 1.4rem; padding-bottom: 3rem; }
h1, h2, h3 { letter-spacing: -.025em; }
h2 { color: var(--cm-text); }
h3 { color: #d6efef; }
p, [data-testid="stCaptionContainer"] { color: var(--cm-muted); }
.cm-hero {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(79, 211, 197, .27);
  border-radius: 22px;
  background: linear-gradient(115deg, #123747 0%, #0c2937 52%, #102436 100%);
  padding: 2.2rem 2.6rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 18px 48px rgba(0, 0, 0, .20);
}
.cm-hero:after {
  content: "";
  position: absolute;
  width: 38%;
  height: 130%;
  right: -4%;
  top: -14%;
  background-image: radial-gradient(circle, rgba(90, 224, 206, .34) 1px, transparent 1.5px);
  background-size: 21px 21px;
  transform: skewY(-12deg);
  opacity: .65;
  pointer-events: none;
}
.cm-kicker {
  color: var(--cm-teal);
  font-size: .78rem;
  font-weight: 800;
  letter-spacing: .19em;
  text-transform: uppercase;
}
.cm-hero h1 {
  margin: .35rem 0 .45rem;
  font-size: clamp(2.2rem, 3.5vw, 3.7rem);
  line-height: 1.04;
  color: #f4ffff;
  font-weight: 800;
}
.cm-hero p {
  position: relative;
  z-index: 1;
  color: #b9d5da;
  max-width: 690px;
  font-size: 1rem;
  margin: 0;
}
.cm-hero-badges { display: flex; gap: .6rem; flex-wrap: wrap; margin-top: 1.3rem; }
.cm-badge {
  color: #cae9e7;
  background: rgba(67, 219, 198, .10);
  border: 1px solid rgba(67, 219, 198, .25);
  border-radius: 999px;
  padding: .28rem .7rem;
  font-size: .76rem;
  font-weight: 650;
}
.cm-section-note {
  color: var(--cm-muted);
  font-size: .89rem;
  margin: -.2rem 0 1rem;
}
.cm-eyebrow {
  color: var(--cm-teal);
  text-transform: uppercase;
  font-weight: 750;
  letter-spacing: .12em;
  font-size: .7rem;
  margin-bottom: .2rem;
}
[data-testid="stMetric"] {
  border: 1px solid var(--cm-border);
  background: linear-gradient(160deg, rgba(20, 56, 68, .86), rgba(9, 34, 48, .92));
  border-radius: 16px;
  padding: 1rem 1.15rem;
  min-height: 126px;
}
[data-testid="stMetricLabel"] { color: #a7c8cb; }
[data-testid="stMetricValue"] { color: #f3ffff; font-weight: 760; }
[data-testid="stExpander"], [data-testid="stForm"] {
  background: rgba(14, 40, 53, .76);
  border: 1px solid var(--cm-border);
  border-radius: 15px;
}
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stDownloadButton"] > button {
  background: var(--cm-teal);
  color: #05222b;
  border: 1px solid var(--cm-teal);
  font-weight: 750;
  border-radius: 10px;
}
div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {
  border-color: #9af5e8;
  color: #07303a;
}
button[data-baseweb="tab"] { font-weight: 700; }
div[data-baseweb="tab-highlight"] { background-color: var(--cm-teal); }
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stFileUploader"] { border-radius: 12px; }
hr { border-color: var(--cm-border); }
</style>
"""

HERO = """
<div class="cm-hero">
  <div class="cm-kicker">Offline threat forecasting workspace</div>
  <h1>CYBERMIND</h1>
  <p>Explore observed network traffic, inspect four-window attack-risk forecasts,
  and preserve evidence for analyst review.</p>
  <div class="cm-hero-badges">
    <span class="cm-badge">● LOCAL ANALYSIS</span>
    <span class="cm-badge">◷ CAPTURE REPLAY</span>
    <span class="cm-badge">▣ ENCRYPTED CASES</span>
  </div>
</div>
"""


def render_header(st):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(HERO, unsafe_allow_html=True)

