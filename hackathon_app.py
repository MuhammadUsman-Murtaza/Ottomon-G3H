import streamlit as st
import google.generativeai as genai
import io
import time
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# ==========================
# CONFIG & THEMED CSS
# ==========================
MODEL_NAME = "gemini-2.0-flash"  # Using 2.0 Flash as it's the current frontier stable, can be gemini-3-flash-preview if available

def apply_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }

        /* Glassmorphism Effect */
        .stApp {
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: #ffffff;
        }

        .main-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 20px;
            animation: fadeIn 0.8s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Styled Headings */
        h1, h2, h3 {
            color: #00d2ff !important;
            font-weight: 700 !important;
        }

        /* Input Styling */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            background-color: rgba(255, 255, 255, 0.07) !important;
            color: white !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
            border-color: #00d2ff !important;
            box-shadow: 0 0 10px rgba(0, 210, 255, 0.3) !important;
        }

        /* Button Styling */
        .stButton > button {
            background: linear-gradient(45deg, #00d2ff 0%, #3a7bd5 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px 24px !important;
            font-weight: 600 !important;
            transition: transform 0.2s, box-shadow 0.2s !important;
            width: 100%;
        }

        .stButton > button:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 15px rgba(0, 210, 255, 0.4);
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: rgba(0, 0, 0, 0.3);
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Preview Area */
        .preview-container {
            background: white;
            color: #333;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            font-family: 'Times New Roman', Times, serif;
            min-height: 500px;
            overflow-y: auto;
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); }
        ::-webkit-scrollbar-thumb { background: #00d2ff; border-radius: 10px; }

        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px 10px 0px 0px;
            color: white;
            padding: 10px 20px;
        }
        .stTabs [aria-selected="true"] {
            background-color: rgba(0, 210, 255, 0.2) !important;
            border-bottom: 2px solid #00d2ff !important;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 20px;
            font-size: 0.9rem;
            color: rgba(255,255,255,0.5);
            margin-top: 50px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .sidebar-logo {
            text-align: center;
            padding: 20px;
            margin-bottom: 20px;
        }
        .sidebar-logo h2 {
            font-size: 1.5rem;
            margin: 0;
            background: -webkit-linear-gradient(#00d2ff, #3a7bd5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================
# AI LOGIC & SUGGESTIONS
# ==========================
def init_gemini(api_key):
    try:
        genai.configure(api_key=api_key)
        # Try to use Gemini 3 if available, fallback to 2.0 Flash
        try:
            return genai.GenerativeModel("gemini-3-flash-preview")
        except:
            return genai.GenerativeModel("gemini-2.0-flash")
    except Exception as e:
        st.error(f"Error initializing Gemini: {e}")
        return None

def extract_text(resp):
    if resp is None: return ""
    try:
        return resp.text
    except Exception:
        try:
            return resp.candidates[0].content[0].text
        except:
            return str(resp)

def get_ai_suggestions(field_name, field_text, model):
    if not model: return "Please enter API key in sidebar."
    
    if not field_text.strip():
        prompt = f"Resume Field: '{field_name}'. Give 3 tips for writing this and 1 short example. Focus on impact and ATS keywords."
    else:
        prompt = f"""
        Field: {field_name}
        Content: {field_text}
        
        Task: Improve this for a professional resume. 
        1. Rewrite it to be more impactful (STAR method).
        2. Identify [MISSING: info].
        3. Suggest 2 relevant keywords for ATS.
        """
    try:
        response = model.generate_content(prompt)
        return extract_text(response)
    except Exception as e:
        return f"Suggestion unavailable: {str(e)}"

def get_ats_score(resume_text, job_desc, model):
    if not model or not job_desc.strip(): return "Please provide both resume and job description."
    prompt = f"""
    Compare the following Resume and Job Description.
    RESUME: {resume_text}
    JOB DESCRIPTION: {job_desc}
    
    1. Give an ATS Match Score (0-100%).
    2. Identify 5 missing keywords.
    3. Suggest 3 bullet point improvements to better align with this specific role.
    """
    try:
        response = model.generate_content(prompt)
        return extract_text(response)
    except Exception as e:
        return f"ATS analysis unavailable: {str(e)}"

def generate_full_resume(data, model):
    prompt = f"""
    You are a world-class executive resume writer. Your task is to transform raw data into a MAJESTIC, high-impact resume and a tailored cover letter.
    
    CRITICAL INSTRUCTIONS:
    - Use powerful action verbs (e.g., "Spearheaded", "Orchestrated", "Engineered").
    - Focus on RESULTS and METRICS (e.g., "increased efficiency by 30%").
    - Ensure the resume is 100% ATS-FRIENDLY with relevant keywords for {data['title']}.
    - If information is missing, use [MISSING: <detail>] - DO NOT INVENT FACTS.
    - Format with clear sections: HEADER, PROFESSIONAL SUMMARY, CORE SKILLS, PROFESSIONAL EXPERIENCE, PROJECTS/ACHIEVEMENTS, EDUCATION.
    
    DATA PROVIDED:
    Name: {data['name']}
    Job Title: {data['title']}
    Email: {data['email']}
    LinkedIn: {data['linkedin']}
    Summary: {data['summary']}
    Skills: {', '.join(data['skills'])} | Additional: {data['extra_skills']}
    Experience: {data['experience']}
    Education: {data['education']}
    Projects: {data['projects']}
    
    Output Format:
    RESUME CONTENT
    ...
    ===COVER_LETTER===
    Dear Hiring Manager,
    ...
    """
    try:
        response = model.generate_content(prompt)
        text = extract_text(response)
        if '===COVER_LETTER===' in text:
            resume, cover = text.split('===COVER_LETTER===')
            return resume.strip(), cover.strip()
        return text, ""
    except Exception as e:
        return f"Error: {e}", ""

# ==========================
# PDF GENERATION (Elite Templates)
# ==========================
def create_pdf(resume_text, cover_text, candidate_name, template_style="Modern"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        leftMargin=50, 
        rightMargin=50, 
        topMargin=50, 
        bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#2E3192") if template_style == "Modern" else colors.black
    secondary_color = colors.HexColor("#1BFFFF") if template_style == "Modern" else colors.grey

    styles.add(ParagraphStyle(
        name='MainHeading', 
        parent=styles['Heading1'], 
        fontSize=22, 
        leading=26, 
        textColor=primary_color,
        alignment=1,
        spaceAfter=14,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='SubHeading', 
        parent=styles['Heading2'], 
        fontSize=14, 
        leading=16, 
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
        borderWidth=1 if template_style == "Modern" else 0,
        borderColor=secondary_color if template_style == "Modern" else colors.white,
        borderPadding=2,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='NormalBody', 
        parent=styles['Normal'], 
        fontSize=10, 
        leading=13, 
        alignment=4, 
        spaceAfter=5
    ))

    story = []
    story.append(Paragraph(f"{candidate_name.upper()}", styles['MainHeading']))
    story.append(Spacer(1, 0.1*inch))
    
    lines = resume_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.isupper() or any(h in line.upper() for h in ['SUMMARY', 'EXPERIENCE', 'EDUCATION', 'SKILLS', 'PROJECTS']) and len(line) < 30:
            story.append(Paragraph(line.upper(), styles['SubHeading']))
        elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
            bullet_text = line.lstrip('-•*').strip()
            story.append(Paragraph(f"• {bullet_text}", styles['NormalBody']))
        else:
            story.append(Paragraph(line, styles['NormalBody']))
            
    story.append(PageBreak())
    
    story.append(Paragraph("COVER LETTER", styles['MainHeading']))
    story.append(Spacer(1, 0.2*inch))
    for line in cover_text.splitlines():
        if line.strip():
            story.append(Paragraph(line.strip(), styles['NormalBody']))
        else:
            story.append(Spacer(1, 0.12*inch))
            
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ==========================
# MAIN APP
# ==========================
def main():
    # Page config must be the absolute first Streamlit command
    st.set_page_config(page_title="Ottomon-G3H: Gemini 3 Resume Pro", page_icon="💎", layout="wide")
    
    if "resume_txt" not in st.session_state: st.session_state.resume_txt = ""
    if "cover_txt" not in st.session_state: st.session_state.cover_txt = ""
    apply_custom_css()

    with st.sidebar:
        st.markdown('<div class="sidebar-logo"><h2>💎 Ottomon-G3H</h2><p>Gemini 3 Hackathon Entry</p></div>', unsafe_allow_html=True)
        
        st.markdown("### 🔑 API ACCESS")
        api_key = st.text_input("Enter Gemini 3 API Key", type="password", help="Required to power the AI logic")
        if not api_key:
            st.error("⚠️ API Key required to proceed")
        else:
            st.success("✅ Key Connected")
            
        st.markdown("### 🎨 RESUME TEMPLATE")
        template_style = st.select_slider("Select Layout Style", options=["Modern", "Classic", "Executive"])
        theme_mode = st.radio("UI Theme", ["Majestic Dark", "Professional Light"], horizontal=True)
        
        st.divider()
        st.markdown("### 💡 PRO TIPS")
        st.info("✓ Quantify achievements (%, $)")
        st.info("✓ Use action verbs (Led, Created)")
        
        st.divider()
        st.write("👨‍💻 Developed by Ottoman")

    if not api_key:
        st.stop()
    
    model = init_gemini(api_key)

    if theme_mode != "Majestic Dark":
        st.markdown("<style>.stApp { background: #f0f2f6; color: #1e1e1e; } .main-card { background: white; border: 1px solid #ddd; color: #1e1e1e; } h1, h2, h3 { color: #2E3192 !important; }</style>", unsafe_allow_html=True)

    st.markdown('<div class="main-card"><h1>Gemini 3 Career Architect</h1><p>Crafting majestic professional identities with frontier AI.</p></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📝 Content Builder", "👁️ Preview Studio", "📊 ATS Matcher"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.subheader("👤 Personal Architecture")
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name", placeholder="e.g. Muhammad Usman Murtaza")
            title = c2.text_input("Proposed Job Title", placeholder="e.g. Senior Software Engineer")
            c3, c4 = st.columns(2)
            email = c3.text_input("Email", placeholder="ottoman@example.com")
            linkedin = c4.text_input("LinkedIn Profile", placeholder="linkedin.com/in/ottoman")
            st.divider()
            st.subheader("🎯 Professional Essence")
            summary = st.text_area("Summary", placeholder="Describe your professional identity...")
            st.subheader("🛠️ Technical Arsenal")
            skills = st.multiselect("Core Skills", ["Python", "React", "Node.js", "Docker", "AWS", "SQL", "Git", "Machine Learning"])
            extra_skills = st.text_input("Additional Specialized Skills")
            st.subheader("💼 Career Odyssey")
            experience = st.text_area("Work Experience", height=200)
            st.subheader("🎓 Intellectual Foundation")
            education = st.text_area("Education")
            st.subheader("🏆 Projects & Masterpieces")
            projects = st.text_area("Key Projects")
            st.markdown('</div>', unsafe_allow_html=True)
            gen_btn = st.button("✨ GENERATE MAJESTIC RESUME")
            
            if gen_btn:
                user_data = {"name": name, "title": title, "email": email, "linkedin": linkedin, "summary": summary, "skills": skills, "extra_skills": extra_skills, "experience": experience, "education": education, "projects": projects}
                with st.spinner("💎 Forging your professional masterpiece..."):
                    res, cov = generate_full_resume(user_data, model)
                    st.session_state.resume_txt, st.session_state.cover_txt = res, cov
                st.balloons()
                st.rerun()

            # Download option appears here after generation
            if st.session_state.resume_txt:
                st.markdown("---")
                st.success("✅ Document Forged!")
                pdf = create_pdf(st.session_state.resume_txt, st.session_state.cover_txt, name or "Candidate", template_style=template_style)
                st.download_button(
                    label="📥 Download Majestic Package (PDF)", 
                    data=pdf, 
                    file_name=f"{(name or 'Candidate').replace(' ', '_')}_Resume.pdf", 
                    mime="application/pdf"
                )

        with col2:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.subheader("🤖 AI Mentor")
            helper_field = st.selectbox("Get advice for:", ["Summary", "Experience", "Skills", "Projects", "Education"])
            field_data_map = {"Summary": summary, "Experience": experience, "Skills": ", ".join(skills) + " " + extra_skills, "Projects": projects, "Education": education}
            if st.button("Get Live Feedback"):
                with st.spinner("Analyzing..."):
                    st.markdown(get_ai_suggestions(helper_field, field_data_map[helper_field], model))
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.subheader("📈 Profile Strength")
            completion = 0
            if name: completion += 10
            if title: completion += 10
            if summary: completion += 20
            if skills: completion += 20
            if experience: completion += 20
            if projects: completion += 20
            st.progress(completion / 100)
            st.write(f"Strength Score: {completion}%")
            st.markdown('</div>', unsafe_allow_html=True)



    with tab2:
        if st.session_state.resume_txt:
            c_r, c_c = st.columns(2)
            c_r.markdown(f'<div class="preview-container">{st.session_state.resume_txt.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            c_c.markdown(f'<div class="preview-container">{st.session_state.cover_txt.replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else: st.info("Generate your content first.")

    with tab3:
        st.subheader("📊 Intelligence ATS Matcher")
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        job_desc = st.text_area("Target Job Description", height=200)
        if st.button("🔍 Analyze ATS Match"):
            if st.session_state.resume_txt:
                with st.spinner("Analyzing..."):
                    st.markdown(get_ats_score(st.session_state.resume_txt, job_desc, model))
            else: st.warning("Generate your resume first!")
        st.markdown('</div>', unsafe_allow_html=True)


    st.markdown('<div class="footer">Built with 💎 by Ottoman | Powered by Gemini 3</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
