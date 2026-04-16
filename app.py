import os
import streamlit as st
from dotenv import load_dotenv
from .agent import agent_app
from .schema import StoryAngle

load_dotenv()

st.set_page_config(page_title="Volta PR Story Agent", layout="wide", page_icon="⚡")

st.title("⚡ Volta AI Story Angle Generator")
st.markdown("Generate 3-5 strategic PR story angles from the latest EV charging industry news.")

with st.sidebar:
    st.header("🔑 API Keys")
    google_key = st.text_input("GOOGLE_API_KEY", type="password", value=os.getenv("GOOGLE_API_KEY", ""))
    tavily_key = st.text_input("TAVILY_API_KEY", type="password", value=os.getenv("TAVILY_API_KEY", ""))
    
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    query_input = st.text_input("Query", "EV charging network industry news")
    
if google_key:
    os.environ["GOOGLE_API_KEY"] = google_key
if tavily_key:
    os.environ["TAVILY_API_KEY"] = tavily_key

if st.button("🚀 Scout News & Generate Angles", use_container_width=True):
    if not google_key or not tavily_key:
        st.error("Please provide both Google and Tavily API keys in the sidebar.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        initial_state = {
            "query": query_input,
            "raw_news": [],
            "competitor_mentions": [],
            "generated_angles": []
        }
        
        try:
            status_text.info("Starting agent workflow...")
            
            final_state = initial_state.copy()
            for s in agent_app.stream(initial_state):
                # LangGraph stream yields {node_name: {updates}}
                for node_name, updates in s.items():
                    final_state.update(updates)
                    
                if "fetch" in s:
                    status_text.info("News fetched. Analyzing competitors...")
                    progress_bar.progress(33)
                elif "analyze" in s:
                    status_text.info("Competitors analyzed. Generating angles with Gemini...")
                    progress_bar.progress(66)
                elif "generate" in s:
                    status_text.success("PR Angles Generated Successfully!")
                    progress_bar.progress(100)
            
            if not final_state:
                st.error("Agent failed to return a valid state.")
            else:
                st.markdown("### 📰 Tavily Search References")
                if final_state.get("raw_news"):
                    import re
                    for article in final_state.get("raw_news"):
                        raw_title = article.get('title', 'Unknown Title') or 'Unknown Title'
                        # Limpiar el título para que no rompa el Markdown
                        clean_title = str(raw_title).replace('\n', ' ').replace('\r', '')
                        clean_title = clean_title.replace('[', '(').replace(']', ')')
                        clean_title = re.sub(r'<!--.*?-->', '', clean_title)
                        clean_title = " ".join(clean_title.split())
                        
                        st.markdown(f"- [{clean_title}]({article.get('url', '#')})")
                else:
                    st.write("No news found or Tavily returned empty.")
                    
                st.markdown("### 🎯 Generated PR Angles")
                angles = final_state.get("generated_angles", [])
                
                mention_text = ", ".join(final_state.get('competitor_mentions', [])) if final_state.get('competitor_mentions') else 'None'
                st.info(f"**Competitors detected in news:** {mention_text}")
                
                if angles:
                    for i, a in enumerate(angles):
                        st.markdown(f"#### {i+1}. {a.headline if hasattr(a, 'headline') else a.get('headline')}")
                        st.markdown(f"**Rationale:** {a.rationale if hasattr(a, 'rationale') else a.get('rationale')}")
                        st.markdown(f"**Why Now:** {a.why_now if hasattr(a, 'why_now') else a.get('why_now')}")
                        
                        spec = a.outlet_specific if hasattr(a, 'outlet_specific') else a.get('outlet_specific')
                        cat = a.outlet_category if hasattr(a, 'outlet_category') else a.get('outlet_category')
                        
                        # Badge for outlet type
                        st.markdown(f"<span style='background-color: #f0f2f6; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; color: #31333F;'>📍 {spec}</span> <span style='background-color: #e1f5fe; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; color: #01579b;'>📂 {cat}</span>", unsafe_allow_html=True)
                        
                        # Show Source URLs
                        sources = a.source_urls if hasattr(a, 'source_urls') else a.get('source_urls', [])
                        if sources:
                            st.markdown("")
                            st.markdown("**Sources:**")
                            for url in sources:
                                st.markdown(f"- [{url}]({url})")
                                
                        st.markdown("---")
                else:
                    st.error("No angles generated.")
                
        except Exception as e:
            st.error(f"Error executing agent: {e}")
