import streamlit as st
import pickle
import numpy as np
import pandas as pd
import altair as alt

# --- Load trained model ---
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# --- Title & Intro ---
st.title("❤️ Heart Health Risk Checker")
st.write("Answer in simple terms (smoking, exercise, stress, etc.). We'll convert to medical inputs automatically.")

st.sidebar.header("📋 Your Input Summary")

# --- Form: user-friendly questions ---
with st.form("risk_form"):
    age = st.slider("How old are you?", 18, 100, 45)
    gender = st.radio("What is your gender?", ["Male", "Female"], horizontal=True)

    smoking = st.selectbox(
        "Do you smoke?",
        ["Never", "Occasionally", "Daily"],
        help="Choose the option that best describes your smoking habit."
    )
    exercise = st.selectbox(
        "How often do you exercise?",
        ["Rarely", "1-2 days/week", "3-5 days/week", "Everyday"],
        help="Any activity that raises your heart rate counts."
    )
    diet = st.selectbox(
        "How healthy is your diet?",
        ["Poor", "Average", "Healthy"],
        help="Overall balance of fruits/vegetables vs fried/processed foods."
    )
    stress = st.selectbox(
        "Your stress level",
        ["Low", "Moderate", "High"],
        help="How stressed do you feel most days?"
    )
    family_history = st.radio(
        "Family history of heart problems?", ["No", "Yes"], horizontal=True,
    )
    weight = st.selectbox(
        "Your weight category",
        ["Underweight", "Normal", "Overweight", "Obese"],
        help="If unsure, choose what fits best."
    )
    sleep = st.selectbox(
        "Your sleep quality",
        ["Poor", "Average", "Good"],
    )

    # Optional: enter medical values directly if you have them
    with st.expander("I have my medical test values (optional)"):
        trestbps_opt = st.number_input("Resting blood pressure (mmHg)", min_value=0, max_value=300, value=0)
        chol_opt = st.number_input("Cholesterol (mg/dL)", min_value=0, max_value=800, value=0)
        fbs_opt = st.selectbox("Fasting blood sugar > 120 mg/dL?", ["Unknown", "No", "Yes"], index=0)
        restecg_opt = st.selectbox("Resting ECG", ["Unknown", "Normal", "ST-T wave abnormality", "Left ventricular hypertrophy"], index=0)
        thalach_opt = st.number_input("Max heart rate (bpm)", min_value=0, max_value=230, value=0)
        exang_opt = st.selectbox("Chest pain during exercise?", ["Unknown", "No", "Yes"], index=0)
        oldpeak_opt = st.number_input("ST depression (oldpeak)", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
        slope_opt = st.selectbox("Slope at peak exercise", ["Unknown", "Upsloping", "Flat", "Downsloping"], index=0)
        ca_opt = st.slider("Major vessels colored by flourosopy (0-4)", 0, 4, 0)
        thal_opt = st.selectbox("Thal", ["Unknown", "Normal", "Fixed defect", "Reversible defect"], index=0)

    submitted = st.form_submit_button("Check risk")

# --- Convert friendly inputs to model features ---
sex = 1 if gender == "Male" else 0

smoke_score = {"Never": 0, "Occasionally": 1, "Daily": 2}[smoking]
exercise_score = {"Rarely": 0, "1-2 days/week": 1, "3-5 days/week": 2, "Everyday": 3}[exercise]
diet_score = {"Poor": 0, "Average": 1, "Healthy": 2}[diet]
stress_score = {"Low": 0, "Moderate": 1, "High": 2}[stress]
family_score = 1 if family_history == "Yes" else 0
weight_score = {"Underweight": 0, "Normal": 1, "Overweight": 2, "Obese": 3}[weight]
sleep_score = {"Poor": 0, "Average": 1, "Good": 2}[sleep]

# Default estimates (used if optional values not provided)
def estimate_trestbps():
    base = 110 + (age - 18) * 0.2
    return int(base + stress_score * 8 + weight_score * 7)

def estimate_chol():
    base = 160 + (age - 18) * 0.8
    smoke_penalty = [0, 15, 30][smoke_score]
    diet_adjust = [25, 10, -10][diet_score]
    return int(base + smoke_penalty + diet_adjust)

def estimate_thalach():
    base = 200 - age
    exercise_bonus = [ -10, -5, 0, 5 ][exercise_score]
    return int(max(90, min(200, base + exercise_bonus - stress_score * 5)))

def estimate_oldpeak():
    return round(0.2 + stress_score * 0.6 + max(0, weight_score - 1) * 0.3, 1)

def derive_cp():
    if stress_score == 2 and exercise_score == 0:
        return 2
    if stress_score == 2 and smoke_score == 2:
        return 1
    return 0

def derive_fbs():
    if diet_score == 0 and weight_score == 3:
        return 1
    if age >= 60 and diet_score == 0:
        return 1
    return 0

def derive_restecg():
    return 0

def derive_exang():
    return 1 if (exercise_score == 0 and stress_score >= 1) else 0

def derive_slope():
    if exercise_score >= 2 and stress_score == 0:
        return 0  # upsloping
    if stress_score == 2:
        return 2  # downsloping
    return 1  # flat

def derive_ca():
    return 1 if (age >= 60 and smoke_score == 2) else 0

def derive_thal():
    return 2 if family_score == 1 else 1

# Use optional medical inputs when provided (non-zero / non-Unknown)
trestbps = int(trestbps_opt) if 'trestbps_opt' in locals() and trestbps_opt > 0 else estimate_trestbps()
chol = int(chol_opt) if 'chol_opt' in locals() and chol_opt > 0 else estimate_chol()
fbs = {"Unknown": derive_fbs(), "No": 0, "Yes": 1}[fbs_opt] if 'fbs_opt' in locals() else derive_fbs()
restecg = {"Unknown": derive_restecg(), "Normal": 0, "ST-T wave abnormality": 1, "Left ventricular hypertrophy": 2}[restecg_opt] if 'restecg_opt' in locals() else derive_restecg()
thalach = int(thalach_opt) if 'thalach_opt' in locals() and thalach_opt > 0 else estimate_thalach()
exang = {"Unknown": derive_exang(), "No": 0, "Yes": 1}[exang_opt] if 'exang_opt' in locals() else derive_exang()
oldpeak = float(oldpeak_opt) if 'oldpeak_opt' in locals() and oldpeak_opt > 0 else estimate_oldpeak()
slope = {"Unknown": derive_slope(), "Upsloping": 0, "Flat": 1, "Downsloping": 2}[slope_opt] if 'slope_opt' in locals() else derive_slope()
ca = int(ca_opt) if 'ca_opt' in locals() else derive_ca()
thal = {"Unknown": derive_thal(), "Normal": 1, "Fixed defect": 2, "Reversible defect": 3}[thal_opt] if 'thal_opt' in locals() else derive_thal()
cp = derive_cp()

# Sidebar summary in plain language
st.sidebar.markdown(f"**Age:** {age}")
st.sidebar.markdown(f"**Gender:** {gender}")
st.sidebar.markdown(f"**Smoking:** {smoking}")
st.sidebar.markdown(f"**Exercise:** {exercise}")
st.sidebar.markdown(f"**Diet:** {diet}")
st.sidebar.markdown(f"**Stress:** {stress}")
st.sidebar.markdown(f"**Family history:** {family_history}")
st.sidebar.markdown(f"**Weight:** {weight}")
st.sidebar.markdown(f"**Sleep:** {sleep}")

# Only run prediction when the button is clicked
if 'submitted' in locals() and submitted:
    X = np.array([[
        age,        # age
        sex,        # sex
        cp,         # cp
        trestbps,   # trestbps
        chol,       # chol
        fbs,        # fbs
        restecg,    # restecg
        thalach,    # thalach
        exang,      # exang
        float(oldpeak),  # oldpeak
        slope,      # slope
        ca,         # ca
        thal        # thal
    ]])

    pred_prob = float(model.predict_proba(X)[0][1])
    pred_label = "High Risk 💔" if pred_prob > 0.5 else "Low Risk ❤️"
    risk_pct = round(pred_prob * 100, 1)

    st.subheader("🩺 Your Estimated Heart Health Risk")
    st.metric("Risk Level", f"{pred_label} ({risk_pct}%)")
    st.progress(pred_prob)

    # Charts: donut and bar
    donut_df = pd.DataFrame({
        "label": ["Risk", "Safe"],
        "value": [risk_pct, max(0.0, 100 - risk_pct)]
    })
    donut = alt.Chart(donut_df).mark_arc(innerRadius=60).encode(
        theta=alt.Theta("value:Q"),
        color=alt.Color("label:N", scale=alt.Scale(range=["#e74c3c", "#2ecc71"]))
    ).properties(width=250, height=250)

    # Bar chart with proper field names
    bar_df = pd.DataFrame({"risk_percentage": [risk_pct], "category": ["Risk"]})
    bar = alt.Chart(bar_df).mark_bar(color="#e67e22", size=30).encode(
        x=alt.X("risk_percentage:Q", scale=alt.Scale(domain=[0, 100]), title="Risk Percentage (%)"),
        y=alt.Y("category:N", axis=None)
    ).properties(height=80, width=400)
    
    # Threshold line
    threshold_df = pd.DataFrame({"threshold": [50]})
    threshold = alt.Chart(threshold_df).mark_rule(color="#888", strokeDash=[4,4], size=2).encode(
        x=alt.X("threshold:Q", title="Risk Percentage (%)")
    )

    cols = st.columns(2)
    with cols[0]:
        st.altair_chart(donut, use_container_width=False)
    with cols[1]:
        st.altair_chart(bar + threshold, use_container_width=True)

    st.write("### 💡 Health Advice")
    if pred_label == "Low Risk ❤️":
        st.success("You're doing well! Keep up regular activity, balanced meals, and enough rest.")
    else:
        st.error("You may be at a higher heart risk. Consider improving diet, exercising more, and managing stress.")
        st.info("🩷 Small, steady lifestyle changes make a big difference over time.")

st.caption("⚠️ This app is for awareness and education only. It is not a medical diagnosis.")
