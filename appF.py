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
st.set_page_config(page_title="YouTUBE AXE", page_icon="🪓", layout="wide")

st.markdown("""
    <style>
    /* Main Theme */
    .stApp { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #0a0a0a; border-right: 1px solid #333; }
    
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
    .hud-card:hover { border-color: #FF0000; transform: translateY(-2px); }
    
    .hud-value { font-size: 26px; font-weight: 700; color: #FFFFFF; font-family: 'Courier New', monospace; }
    .hud-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px; }
    
    /* Custom Branding */
    .brand-text { color: #FF0000; font-weight: bold; letter-spacing: 1px; font-size: 12px; }
    
    /* Custom Button */
    div.stButton > button {
        background-color: #CC0000;
        color: white;
        border: none;
        font-weight: bold;
        width: 100%;
        height: 42px; /* Ensure vertical alignment */
        margin-top: 2px;
    }
    div.stButton > button:hover {
        background-color: #FF0000;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE
# ==========================================
if 'search_done' not in st.session_state: st.session_state.search_done = False
if 'df' not in st.session_state: st.session_state.df = pd.DataFrame()
if 'all_tags' not in st.session_state: st.session_state.all_tags = []

# ==========================================
# 3. SIDEBAR (BRANDED)
# ==========================================
with st.sidebar:
    st.title("🪓 YouTUBE AXE")
    st.markdown("<div class='brand-text'>Version A.X.G -Abhi1 Edition</div>", unsafe_allow_html=True)
    st.divider()
    
    # KEY HANDLING (Works with Secrets OR Manual Input)
    if "YOUTUBE_API_KEY" in st.secrets:
        api_key = st.secrets["YOUTUBE_API_KEY"]
        st.success("✅ SYSTEM ONLINE")
    else:
        api_key = st.text_input("🔑 YouTube API Key", type="password")

    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        ai_enabled = True
        st.success("✅ AI AGENT ACTIVE")
    else:
        gemini_key = st.text_input("✨ Gemini API Key", type="password")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            ai_enabled = True
        else:
            ai_enabled = False
            st.warning("⚠️ AI OFFLINE")
    
    st.divider()
    country_code = st.selectbox("TARGET REGION", ["US", "IN", "GB", "CA", "AU"], index=0)
    rpm = st.slider("RPM CALIBRATOR ($)", 0.5, 20.0, 3.0)

# ==========================================
# 4. CORE FUNCTIONS
# ==========================================
@st.cache_data(show_spinner=False)
def get_market_data(api_key, query, max_results=50):
    youtube = build('youtube', 'v3', developerKey=api_key)
    search_req = youtube.search().list(part="snippet", q=query, type="video", regionCode=country_code, maxResults=max_results, order="viewCount").execute()
    video_ids = [item['id']['videoId'] for item in search_req.get('items', [])]
    
    stats_req = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(video_ids)).execute()
    
    data, all_tags = [], []
    for item in stats_req.get('items', []):
        stats, snippet, content = item['statistics'], item['snippet'], item['contentDetails']
        
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        tags = snippet.get('tags', [])
        if tags: all_tags.extend(tags)
        
        try:
            duration_iso = content['duration']
            duration_mins = round(isodate.parse_duration(duration_iso).total_seconds() / 60, 2)
        except:
            duration_mins = 0
        
        thumb_url = snippet['thumbnails'].get('maxres', snippet['thumbnails']['high'])['url']
        
        data.append({
            'Video ID': item['id'],
            'Thumbnail': thumb_url,
            'Title': snippet['title'],
            'Views': views,
            'Likes': likes,
            'Engagement': round(((likes + comments) / views * 100) if views > 0 else 0, 2),
            'Earnings': round((views / 1000) * rpm, 2),
            'Virality Raw': (views * 0.5) + (likes * 50) + (comments * 100),
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
    except:
        return None

def ai_forensic_audit(transcript, title, duration):
    # --- MODEL FIXED TO STABLE PRO ALIAS ---
    model = genai.GenerativeModel('gemini-1.0-pro') 
    prompt = f"""
    Act as a Senior Video Editor (Premiere Pro Expert).
    Analyze this script density to reverse-engineer the editing timeline.
    
    METADATA:
    Title: {title}
    Duration: {duration} Mins
    Script: "{transcript[:8000]}..."
    
    OUTPUT FORMAT (Strict Markdown):
    ### ✂️ EDITING DIAGNOSTICS
    * **Pacing:** (Fast/Hyperactive vs Slow/Cinematic)
    * **Est. Cuts Per Minute:** (Based on word count density)
    * **Editor Skill Level:** (Beginner vs Masterclass)
    
    ### 🛠️ TECH STACK
    * **Software:** (e.g. CapCut, Premiere, After Effects)
    * **Effects Used:** (e.g. Rotoscoping, J-Cuts, Motion Blur)
    
    ### 🎞️ TIMELINE BLUEPRINT
    * **00:00 - Hook:** (Visual strategy)
    * **Middle:** (Retention tactics used)
    * **Ending:** (CTA strategy)
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
# 6. DASHBOARD UI (FIXED LAYOUT)
# ==========================================
st.title("🪓 YouTUBE AXE")

# 1. DEFINE COLUMNS AND INPUT/BUTTON LOGIC (Fixed NameError)
c1, c2 = st.columns([4, 1])

with c1:
    query = st.text_input("TARGET VECTOR", placeholder="e.g. 'MrBeast', 'AI News'", label_visibility="collapsed")

with c2:
    if st.button("🚀 INITIALIZE SCAN", type="primary", use_container_width=True):
        if api_key:
            if not query:
                st.warning("⚠️ Enter a topic")
            else:
                with st.spinner('🛰️ CONNECTING TO SATELLITE...'):
                    try:
                        st.session_state.df, st.session_state.all_tags = get_market_data(api_key, query, 50)
                        st.session_state.search_done = True
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.error("❌ KEYS MISSING")

# 4. SHOW RESULTS IF SEARCH IS DONE
if st.session_state.search_done:
    df = st.session_state.df
    st.write("") 
    
    # --- HUD METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f"<div class='hud-card'><div class='hud-label'>Total Views</div><div class='hud-value'>{df['Views'].sum():,}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='hud-card'><div class='hud-label'>Market Value</div><div class='hud-value'>${df['Earnings'].sum():,.0f}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='hud-card'><div class='hud-label'>Avg Duration</div><div class='hud-value'>{df['Duration'].mean():.1f}m</div></div>", unsafe_allow_html=True)
    with m4: st.markdown(f"<div class='hud-card'><div class='hud-label'>Max Virality</div><div class='hud-value'>{df['Virality Score'].max():.0f}</div></div>", unsafe_allow_html=True)

    st.write("")
    tabs = st.tabs(["📂 DATABASE", "✂️ EDITING LAB", "🕵️ TAG SPY", "🎬 DEEP DIVE"])
    
    # TAB 1: DB
    with tabs[0]:
        st.dataframe(
            df[['Thumbnail', 'Title', 'Views', 'Duration', 'Virality Score', 'Link']], 
            column_config={
                "Thumbnail": st.column_config.ImageColumn("Preview"), 
                "Virality Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                "Link": st.column_config.LinkColumn("▶️ WATCH") # Clickable Link Fix
            }, 
            use_container_width=True, height=600)

    # TAB 2: THE NEW EDITING LAB
    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        
        with c1:
            st.markdown("### 🎯 TARGET ACQUISITION")
            target = st.selectbox("Select Video:", df['Title'].tolist(), label_visibility="collapsed")
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
            st.info("AI Agent Standing By...")
            
            if ai_enabled:
                if st.button("🔍 RUN EDITING AUTOPSY", type="primary", use_container_width=True):
                    open_forensic_lab(row['Video ID'], row['Title'], row['Duration'])
            else:
                st.warning("AI MODULE OFFLINE")

    # TAB 3: TAGS
    with tabs[2]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### 📋 SEO DATA")
            tag_counts = Counter(st.session_state.all_tags).most_common(30)
            tags_text = ", ".join([t[0] for t in tag_counts])
            st.text_area("Tags", tags_text, height=300)
        with c2:
            if st.session_state.all_tags:
                wc = WordCloud(width=800, height=400, background_color='#000000', colormap='Greens').generate_from_frequencies(dict(tag_counts))
                fig, ax = plt.subplots(); plt.imshow(wc, interpolation='bilinear'); plt.axis("off"); fig.patch.set_facecolor('#000000'); st.pyplot(fig)
    
    # TAB 4: DEEP DIVE (Video Player)
    with tabs[3]:
        # Uses the currently selected video from the Editing Lab's radio button for consistency
        st.video(df[df['Title'] == target].iloc[0]['Link'])
