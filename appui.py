import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from googleapiclient.discovery import build
from textblob import TextBlob
from wordcloud import WordCloud
from collections import Counter
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import isodate

# ==========================================
# 1. CONFIG & THEME
# ==========================================
st.set_page_config(page_title="YouTUBE AXE – AI Edition", page_icon="🪓", layout="wide")

st.markdown("""
    <style>
    /* Main Theme */
    .stApp { 
        background-color: #000000; 
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] { 
        background-color: #0a0a0a; 
        border-right: 1px solid #333; 
    }
    
    /* High-Tech HUD Cards */
    .hud-card { 
        background-color: #1a1a1a; 
        border: 1px solid #333;
        border-radius: 8px; 
        padding: 15px;
        margin-bottom: 10px;
        transition: all 0.3s ease;
        box-shadow: 0 0 10px rgba(0,0,0,0.5);
    }
    .hud-card:hover { 
        border-color: #FF0000; 
        transform: translateY(-2px); 
    }
    
    .hud-value { 
        font-size: 26px; 
        font-weight: 700; 
        color: #FFFFFF; 
        font-family: 'Courier New', monospace; 
    }
    .hud-label { 
        font-size: 11px; 
        color: #888; 
        text-transform: uppercase; 
        letter-spacing: 2px; 
        margin-bottom: 5px; 
    }
    
    /* Custom Branding */
    .brand-text { 
        color: #FF0000; 
        font-weight: bold; 
        letter-spacing: 1px; 
        font-size: 12px; 
    }

    .sub-brand { 
        color: #AAAAAA; 
        font-size: 11px; 
        text-transform: uppercase; 
        letter-spacing: 1px; 
    }
    
    /* Custom Button */
    div.stButton > button {
        background-color: #CC0000;
        color: white;
        border: none;
        font-weight: bold;
        width: 100%;
        height: 42px;
        margin-top: 2px;
        border-radius: 999px;
    }
    div.stButton > button:hover {
        background-color: #FF0000;
        color: white;
    }

    /* Chat messages */
    .chat-user { 
        background-color: #111; 
        padding: 10px 12px; 
        border-radius: 8px;
        margin-bottom: 5px;
        border: 1px solid #333;
    }
    .chat-bot { 
        background-color: #151515; 
        padding: 10px 12px; 
        border-radius: 8px;
        margin-bottom: 5px;
        border: 1px solid #444;
    }
    .chat-user-label { color: #ff4b4b; font-size: 11px; text-transform: uppercase; }
    .chat-bot-label { color: #4b9bff; font-size: 11px; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE
# ==========================================
if 'search_done' not in st.session_state:
    st.session_state.search_done = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'all_tags' not in st.session_state:
    st.session_state.all_tags = []
if 'selected_title' not in st.session_state:
    st.session_state.selected_title = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []  # list of dicts: {"role": "user"/"bot", "content": str}

# ==========================================
# 3. SIDEBAR (BRANDED)
# ==========================================
with st.sidebar:
    st.title("🪓 YouTUBE AXE – AI")
    st.markdown("<div class='brand-text'>Version A.X.G - Abhi1 Edition</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-brand'>AI Market Brain • Niche Intelligence • Edit Forensics</div>", unsafe_allow_html=True)
    st.divider()
    
    # KEY HANDLING (Works with Secrets OR Manual Input)
    if "YOUTUBE_API_KEY" in st.secrets:
        api_key = st.secrets["YOUTUBE_API_KEY"]
        st.success("✅ YOUTUBE SYSTEM ONLINE")
    else:
        api_key = st.text_input("🔑 YouTube API Key", type="password")

    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        ai_enabled = True
        st.success("✅ GEMINI AI AGENT ACTIVE")
    else:
        gemini_key = st.text_input("✨ Gemini API Key", type="password")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            ai_enabled = True
        else:
            ai_enabled = False
            st.warning("⚠️ AI OFFLINE – Add Gemini key to unlock full features")
    
    st.divider()
    country_code = st.selectbox("TARGET REGION", ["US", "IN", "GB", "CA", "AU"], index=0)
    rpm = st.slider("RPM CALIBRATOR ($)", 0.5, 20.0, 3.0)
    st.caption("RPM ~ rough revenue per 1000 views.")

    st.divider()
    if st.button("♻️ RESET SESSION"):
        st.session_state.search_done = False
        st.session_state.df = pd.DataFrame()
        st.session_state.all_tags = []
        st.session_state.selected_title = None
        st.session_state.chat_history = []
        st.success("Session cleared.")

# ==========================================
# 4. CORE FUNCTIONS
# ==========================================
@st.cache_data(show_spinner=False)
def get_market_data(api_key, query, region_code, rpm_value, max_results=50):
    youtube = build('youtube', 'v3', developerKey=api_key)
    search_req = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        regionCode=region_code,
        maxResults=max_results,
        order="viewCount"
    ).execute()
    video_ids = [item['id']['videoId'] for item in search_req.get('items', [])]
    
    if not video_ids:
        return pd.DataFrame(), []

    stats_req = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()
    
    data, all_tags = [], []
    for item in stats_req.get('items', []):
        stats, snippet, content = item['statistics'], item['snippet'], item['contentDetails']
        
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        tags = snippet.get('tags', [])
        if tags:
            all_tags.extend(tags)
        
        try:
            duration_iso = content['duration']
            duration_mins = round(isodate.parse_duration(duration_iso).total_seconds() / 60, 2)
        except Exception:
            duration_mins = 0
        
        thumb_url = snippet['thumbnails'].get(
            'maxres',
            snippet['thumbnails'].get('high', list(snippet['thumbnails'].values())[0])
        )['url']
        
        engagement = round(((likes + comments) / views * 100) if views > 0 else 0, 2)
        earnings = round((views / 1000) * rpm_value, 2)
        virality_raw = (views * 0.5) + (likes * 50) + (comments * 100)
        
        data.append({
            'Video ID': item['id'],
            'Thumbnail': thumb_url,
            'Title': snippet['title'],
            'Views': views,
            'Likes': likes,
            'Comments': comments,
            'Engagement': engagement,
            'Earnings': earnings,
            'Virality Raw': virality_raw,
            'Link': f"https://www.youtube.com/watch?v={item['id']}",
            'Published': snippet['publishedAt'][:10],
            'Duration': duration_mins
        })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df['Virality Score'] = (df['Virality Raw'] / df['Virality Raw'].max()) * 100
        df['Virality Score'] = df['Virality Score'].round(0)
    return df, all_tags

def get_transcript_text(video_id):
    try:
        return " ".join([t['text'] for t in YouTubeTranscriptApi.get_transcript(video_id)])
    except Exception:
        return None

def ai_forensic_audit(transcript, title, duration):
    model = genai.GenerativeModel('gemini-1.0-pro') 
    prompt = f"""
    Act as a Senior YouTube Video Editor & Premiere Pro Expert.
    Analyze this script density to reverse-engineer the editing timeline.

    METADATA:
    Title: {title}
    Duration: {duration} minutes
    Script (truncated): "{transcript[:8000]}..."

    OUTPUT FORMAT (Strict Markdown):
    ### ✂️ EDITING DIAGNOSTICS
    * Pacing Style:
    * Est. Cuts Per Minute:
    * Editor Skill Level (1–10):
    * Rhythm / Silence Usage:

    ### 🧠 CONTENT & HOOK
    * Hook Strength (0–10) & why
    * Retention tactics used
    * Drop-off risk moments

    ### 🛠️ TECH STACK GUESS
    * Likely Editing Software
    * Likely Effects (J-cuts, speed ramps, masking, etc.)

    ### 🎞️ TIMELINE BLUEPRINT
    * 00:00 - Hook:
    * Mid Section:
    * Ending & CTA:

    ### 🚀 UPGRADE RECOMMENDATIONS
    * 3 edit changes to improve retention
    * 3 ideas to repurpose into Shorts/Reels
    """
    return model.generate_content(prompt).text

def analyze_title_sentiment(df):
    if df.empty:
        return df
    sentiments = []
    for t in df['Title']:
        tb = TextBlob(t)
        sentiments.append(tb.sentiment.polarity)
    df = df.copy()
    df['Sentiment'] = sentiments
    df['Sentiment Label'] = pd.cut(
        df['Sentiment'],
        bins=[-1.0, -0.05, 0.05, 1.0],
        labels=['Negative', 'Neutral', 'Positive']
    )
    return df

def ai_niche_for_video(title, tags, description="", transcript=""):
    """Classify niche of a single video using AI."""
    model = genai.GenerativeModel('gemini-1.0-pro')
    prompt = f"""
    You are a YouTube niche classifier.

    Given this data, identify the primary niche + 2 sub-niches:

    Title: {title}
    Tags: {tags}
    Description: {description[:500]}
    Transcript snippet: {transcript[:1000]}

    Return strictly in this markdown format:

    **Main Niche:** <one line>
    **Sub Niches:** <comma separated>
    **Audience Type:** <who is this mainly for?>
    **Content Style:** <e.g. educational / storytelling / vlog / challenge / news / commentary>
    """
    return model.generate_content(prompt).text

def ai_niche_strategy(df, query):
    if df.empty:
        return "No data available."
    model = genai.GenerativeModel('gemini-1.0-pro')
    sample = df.sort_values('Views', ascending=False).head(15)
    rows = []
    for _, r in sample.iterrows():
        rows.append(f"- {r['Title']} | {r['Views']} views | {r['Duration']} mins | {r['Engagement']}% engagement")
    meta_block = "\n".join(rows)
    prompt = f"""
    You are a YouTube Growth Consultant.

    Topic / query scanned: "{query}"

    Here are some of the top videos:
    {meta_block}

    Based on this, return a strategy in markdown:
    - Overall niche summary
    - Common patterns (length, titles, thumbnails, pacing)
    - Recommended video lengths & formats for a new creator
    - 5 advanced video ideas with angle + hook
    - Suggested posting schedule for growth
    """
    return model.generate_content(prompt).text

def ai_title_ideas(base_idea, niche_desc):
    model = genai.GenerativeModel('gemini-1.0-pro')
    prompt = f"""
    Act as a viral YouTube title copywriter.

    Base idea: "{base_idea}"
    Niche/channel description: "{niche_desc}"

    Generate 8 viral title variations with:
    - Curiosity
    - Stakes or payoff
    - Some emotion

    Return in markdown with a short note under each about why it can work.
    """
    return model.generate_content(prompt).text

def ai_chat_about_niche(question, df, query):
    """Chatbot that knows about this market and explains niche, strategy, video types, etc."""
    model = genai.GenerativeModel('gemini-1.0-pro')
    if df.empty:
        context = "No videos scanned yet."
    else:
        # compress market into brief context
        top = df.sort_values('Views', ascending=False).head(12)
        ctx_rows = []
        for _, r in top.iterrows():
            ctx_rows.append(
                f"- {r['Title']} | {r['Views']} views | {r['Duration']} mins | "
                f"{r['Engagement']}% engagement | Virality {r['Virality Score']} | Sentiment {r.get('Sentiment Label','NA')}"
            )
        context = "\n".join(ctx_rows)

    prompt = f"""
    You are an AI YouTube Niche Analyst and Growth Mentor.

    The user has scanned this topic: "{query}".

    Here is a snapshot of top videos in this space:
    {context}

    The user asks: "{question}"

    Answer like a smart YouTube consultant:
    - Explain clearly in human language
    - Use examples from the kind of videos in this niche
    - If user asks about what niche this is, explain niche, audience, money potential
    - If user asks about content ideas, give angles + hooks
    - If user asks about how to grow, give step-by-step.

    Reply in markdown.
    """
    return model.generate_content(prompt).text

# ==========================================
# 5. HUD MODAL
# ==========================================
@st.dialog("✂️ EDITING LAB: A.X.G PRO", width="large")
def open_forensic_lab(vid, title, duration):
    st.markdown(f"### TARGET: {title}")
    transcript = get_transcript_text(vid)
    
    if transcript:
        with st.spinner("⚙️ REVERSE ENGINEERING EDITING TIMELINE..."):
            analysis = ai_forensic_audit(transcript, title, duration)
        st.success("✅ BLUEPRINT EXTRACTED")
        st.markdown(analysis)
    else:
        st.error("⚠️ DATA CORRUPT: No Transcript available for deep editing analysis.")

# ==========================================
# 6. DASHBOARD UI
# ==========================================
st.title("🪓 YouTUBE AXE – FULL AI")
st.caption("AI-powered YouTube market scanner • niche detector • edit lab • strategy chatbot")

# Search row
c1, c2 = st.columns([4, 1])

with c1:
    query = st.text_input(
        "TARGET VECTOR",
        placeholder="e.g. 'Dubai AI business', 'MrBeast challenge', 'AI News'",
        label_visibility="collapsed"
    )

with c2:
    if st.button("🚀 INITIALIZE SCAN", type="primary", use_container_width=True):
        if api_key:
            if not query:
                st.warning("⚠️ Enter a topic")
            else:
                with st.spinner('🛰️ CONNECTING TO SATELLITE...'):
                    try:
                        df_raw, all_tags = get_market_data(api_key, query, country_code, rpm, 50)
                        df = analyze_title_sentiment(df_raw)
                        st.session_state.df = df
                        st.session_state.all_tags = all_tags
                        st.session_state.search_done = not df.empty
                        st.session_state.selected_title = df.iloc[0]['Title'] if not df.empty else None
                        st.session_state.chat_history = []
                        if df.empty:
                            st.error("No videos found for this query.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.error("❌ KEYS MISSING – Add your YouTube API key in the sidebar.")

# MAIN BODY
if st.session_state.search_done:
    df = st.session_state.df
    
    # HUD
    st.write("")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"<div class='hud-card'><div class='hud-label'>Total Views</div>"
            f"<div class='hud-value'>{df['Views'].sum():,}</div></div>",
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            f"<div class='hud-card'><div class='hud-label'>Market Value</div>"
            f"<div class='hud-value'>${df['Earnings'].sum():,.0f}</div></div>",
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            f"<div class='hud-card'><div class='hud-label'>Avg Duration</div>"
            f"<div class='hud-value'>{df['Duration'].mean():.1f}m</div></div>",
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            f"<div class='hud-card'><div class='hud-label'>Max Virality</div>"
            f"<div class='hud-value'>{df['Virality Score'].max():.0f}</div></div>",
            unsafe_allow_html=True
        )

    st.write("")
    tabs = st.tabs([
        "📂 DATABASE",
        "✂️ EDITING LAB",
        "🕵️ TAG SPY",
        "📊 ANALYTICS",
        "💡 AI IDEAS",
        "🤖 AI NICHE CHAT",
        "🎬 DEEP DIVE"
    ])

    # TAB 1: DATABASE
    with tabs[0]:
        st.markdown("### 📂 Market Database")
        st.dataframe(
            df[['Thumbnail', 'Title', 'Views', 'Duration', 'Virality Score', 'Engagement', 'Sentiment Label', 'Link']], 
            column_config={
                "Thumbnail": st.column_config.ImageColumn("Preview"), 
                "Virality Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                "Engagement": st.column_config.NumberColumn("Engagement %", format="%.2f"),
                "Sentiment Label": st.column_config.TextColumn("Sentiment"),
                "Link": st.column_config.LinkColumn("▶️ WATCH")
            }, 
            use_container_width=True,
            height=600
        )

    # TAB 2: EDITING LAB
    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        
        with c1:
            st.markdown("### 🎯 TARGET ACQUISITION")
            target = st.selectbox("Select Video:", df['Title'].tolist(), label_visibility="collapsed")
            st.session_state.selected_title = target
            row = df[df['Title'] == target].iloc[0]
            
            st.image(row['Thumbnail'], use_container_width=True)
            
            st.markdown(f"""
            <div style='display: flex; justify-content: space-between; margin-top: 10px;'>
                <div class='hud-card' style='flex:1; margin-right:5px;'>
                    <div class='hud-label'>DURATION</div>
                    <div class='hud-value'>{row['Duration']}m</div>
                </div>
                <div class='hud-card' style='flex:1; margin-left:5px;'>
                    <div class='hud-label'>VIRALITY</div>
                    <div class='hud-value'>{row['Virality Score']:.0f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown("### 🧬 FORENSIC TOOLS")
            st.info("AI Editor is ready to break down the timeline and edit style.")
            
            if ai_enabled:
                if st.button("🔍 RUN EDITING AUTOPSY", type="primary", use_container_width=True):
                    open_forensic_lab(row['Video ID'], row['Title'], row['Duration'])
            else:
                st.warning("AI MODULE OFFLINE")

    # TAB 3: TAG SPY
    with tabs[2]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### 📋 SEO DATA")
            tag_counts = Counter(st.session_state.all_tags).most_common(50)
            tags_text = ", ".join([t[0] for t in tag_counts]) if tag_counts else ""
            st.text_area("Tags", tags_text, height=300)
        with c2:
            st.markdown("### ☁️ Tag Cloud")
            if st.session_state.all_tags:
                wc = WordCloud(
                    width=800, 
                    height=400, 
                    background_color='#000000', 
                    colormap='Greens'
                ).generate_from_frequencies(dict(tag_counts))
                fig, ax = plt.subplots()
                plt.imshow(wc, interpolation='bilinear')
                plt.axis("off")
                fig.patch.set_facecolor('#000000')
                st.pyplot(fig)
            else:
                st.info("No tags detected.")

    # TAB 4: ANALYTICS
    with tabs[3]:
        st.markdown("### 📊 Market Analytics")
        a1, a2 = st.columns(2)
        with a1:
            st.subheader("Views Distribution")
            fig, ax = plt.subplots()
            sns.histplot(df['Views'], bins=20, ax=ax)
            ax.set_xlabel("Views")
            ax.set_ylabel("Count")
            st.pyplot(fig)

        with a2:
            st.subheader("Virality vs Engagement")
            fig2, ax2 = plt.subplots()
            ax2.scatter(df['Virality Score'], df['Engagement'])
            ax2.set_xlabel("Virality Score")
            ax2.set_ylabel("Engagement %")
            st.pyplot(fig2)

        st.subheader("Top 10 Videos by Virality")
        top10 = df.sort_values('Virality Score', ascending=False).head(10)[
            ['Title', 'Views', 'Virality Score', 'Engagement', 'Earnings']
        ]
        st.dataframe(top10, use_container_width=True)

        st.subheader("Title Sentiment Breakdown")
        st.write(df['Sentiment Label'].value_counts())

        if ai_enabled:
            st.subheader("🧠 AI Niche Strategy Summary")
            if st.button("Generate Niche Strategy"):
                with st.spinner("Analyzing niche pattern with AI..."):
                    strat = ai_niche_strategy(df, query)
                st.markdown(strat)

    # TAB 5: AI IDEAS
    with tabs[4]:
        st.markdown("### 💡 AI Idea Lab – Titles & Concepts")
        col_idea, col_niche = st.columns(2)
        with col_idea:
            base_idea = st.text_input("Your rough video idea", placeholder="e.g. 'AI will replace X in Dubai'")
        with col_niche:
            niche_desc = st.text_input("Your channel niche", placeholder="e.g. 'AI & Business in Dubai'")
        
        if ai_enabled:
            if st.button("⚡ Generate Title Pack"):
                if not base_idea:
                    st.warning("Please enter a base idea.")
                else:
                    with st.spinner("Summoning title wizard..."):
                        ideas = ai_title_ideas(base_idea, niche_desc)
                    st.markdown(ideas)
        else:
            st.warning("AI MODULE OFFLINE – Add Gemini key in sidebar.")

    # TAB 6: AI NICHE CHATBOT
    with tabs[5]:
        st.markdown("### 🤖 AI Niche Chat – Ask Anything")
        st.caption("Ask the AI about what niche this is, who the audience is, how to grow, what to post, etc.")
        
        # Show chat history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f"<div class='chat-user'><div class='chat-user-label'>You</div>{msg['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='chat-bot'><div class='chat-bot-label'>YouTube AXE AI</div>{msg['content']}</div>",
                    unsafe_allow_html=True
                )

        user_q = st.text_input("Ask the AI about this niche, videos, growth, etc.", key="chat_input")
        col_send, col_clear = st.columns([1, 1])
        with col_send:
            send_clicked = st.button("Send")
        with col_clear:
            clear_chat = st.button("Clear Chat")

        if clear_chat:
            st.session_state.chat_history = []
            st.experimental_rerun()

        if send_clicked and user_q:
            st.session_state.chat_history.append({"role": "user", "content": user_q})
            if not ai_enabled:
                bot_reply = "⚠️ AI offline – please add a Gemini API key in the sidebar."
            else:
                with st.spinner("Thinking about this niche..."):
                    bot_reply = ai_chat_about_niche(user_q, df, query)
            st.session_state.chat_history.append({"role": "bot", "content": bot_reply})
            st.experimental_rerun()

    # TAB 7: DEEP DIVE
    with tabs[6]:
        st.markdown("### 🎬 Deep Dive Player & Niche Breakdown")
        if st.session_state.selected_title and st.session_state.selected_title in df['Title'].values:
            vid_row = df[df['Title'] == st.session_state.selected_title].iloc[0]
        else:
            vid_row = df.iloc[0]

        st.write(f"**Now playing:** {vid_row['Title']}")
        st.video(vid_row['Link'])

        if ai_enabled:
            st.markdown("#### 🔍 AI Niche Classification for This Video")
            if st.button("Classify Niche for Selected Video"):
                transcript = get_transcript_text(vid_row['Video ID'])
                tags_subset = ", ".join(df[df['Video ID'] == vid_row['Video ID']].index.astype(str))
                with st.spinner("Classifying niche with AI..."):
                    niche_text = ai_niche_for_video(
                        title=vid_row['Title'],
                        tags=tags_subset,
                        description="",  # could fetch from API if needed
                        transcript=transcript or ""
                    )
                st.markdown(niche_text)
        else:
            st.info("Add Gemini key to unlock AI niche classification.")
else:
    st.info("Enter a topic above and hit **INITIALIZE SCAN** to start the AI analysis.")
