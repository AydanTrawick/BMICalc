import streamlit as st

st.set_page_config(page_title="Recovery Guide", page_icon="🤕", layout="centered")

st.page_link("BMI2.py", label="← Back to Home")

st.markdown("## 🤕 So You Had a Big Night...")
st.markdown("No judgment here. Let's get you back to a functioning human.")

st.divider()

st.info("⚠️ This guide is for general wellness tips only. If you're experiencing severe symptoms, please seek medical attention.")

st.markdown("")

# --- What's Happening ---
st.markdown("### What's Actually Going On In There")
st.markdown("""
Before we fix you up, here's why you feel like this.

- **You're dehydrated** — alcohol is a diuretic, meaning your kidneys were working overtime all night flushing out fluids. That's the headache and dry mouth.
- **Your electrolytes are gone** — sodium, potassium, and magnesium left with all that fluid. That's the weakness and brain fog.
- **Acetaldehyde is the real villain** — when your liver breaks down alcohol it produces a toxic compound called acetaldehyde. That's what's causing the nausea and general feeling of doom.
- **Your blood sugar is low** — alcohol disrupts glucose production. That's the shakiness and irritability.
- **Your sleep was garbage** — alcohol suppresses REM sleep, so even if you slept 10 hours you woke up exhausted.
""")

st.divider()

# --- Severity Check ---
st.markdown("### First, Figure Out Where You're At")

stage = st.radio("How are you feeling right now?", [
    "🟡 Rough — headache, dry mouth, tired",
    "🔴 Bad — nauseous, dizzy, can't look at light",
    "⚫ Send help — I haven't moved in hours",
], index=0)

st.markdown("")

if stage == "🟡 Rough — headache, dry mouth, tired":
    st.success("Good news — you're in standard hangover territory. You've got this.")
    st.markdown("""
    **Your game plan:**
    - 💧 Drink a large glass of water immediately. Then another one. Your body lost up to a liter of fluid overnight.
    - 🧂 Add electrolytes — a sports drink, Pedialyte, or Liquid IV will rehydrate you faster than plain water alone
    - 🥚 Eat eggs when you can — they contain cysteine, an amino acid that actually helps your liver break down acetaldehyde (the toxic stuff making you feel awful)
    - 🍌 Banana for potassium — one of the main electrolytes you flushed out last night
    - 🛌 Another hour of sleep if you can get it — your body is still doing repair work
    - ☕ Coffee is fine but hydrate first — caffeine on an empty dehydrated stomach will make the headache worse
    - 🚶 A short walk outside once you're upright helps circulation and gets fresh air in — more effective than it sounds
    """)

elif stage == "🔴 Bad — nauseous, dizzy, can't look at light":
    st.warning("Okay, this one's going to take some patience. You pushed it last night.")
    st.markdown("""
    **Your game plan:**
    - 💧 Sip water slowly — your stomach is irritated and chugging will trigger nausea. 
    - 🧂 Electrolytes over plain water — Pedialyte is genuinely the best option. It's designed for fluid replacement and has the right balance of sodium and glucose to actually absorb.
    - 🍞 When you can stomach it — plain toast, crackers, or a banana. Nothing heavy yet. Your stomach lining is inflamed and greasy food will make things worse, not better (yes, that's a myth).
    - 🛌 Darkness, silence, horizontal. Your blood vessels are dilated from the alcohol which is why light sensitivity is so intense right now.
    - 💊 Ibuprofen for the headache — take it with food to protect your stomach. **Avoid Tylenol/acetaminophen** — when alcohol is still being metabolized, acetaminophen puts serious stress on your liver.
    - ⏳ Hydration and time are the only real cure. There's no shortcut — your liver processes alcohol at a fixed rate of about one drink per hour.
    """)

else:
    st.error("Okay, full recovery mode. No heroics today — and that's completely fine.")
    st.markdown("""
    **Your game plan:**
    - 🚨 If you're experiencing chest pain, seizures, confusion, or can't keep any fluids down for several hours — please seek medical attention. Severe dehydration and alcohol poisoning are serious.
    - 💧 Tiny sips of water or Pedialyte only. Your stomach will reject anything aggressive right now.
    - 🛌 You are not leaving that couch and that is the correct decision. Your body is redirecting all available energy to processing and eliminating toxins.
    - 📵 Put your phone down — screens stimulate your nervous system and make nausea and light sensitivity worse
    - 🧊 Cool cloth on the forehead if you're overheating — alcohol can cause your body temperature to fluctuate
    - 🕐 Give it at least 2-3 hours before attempting any food. Start with a few crackers or plain toast when you're ready.
    - 📱 Text someone you trust to check on you if things feel severe
    """)

st.divider()

# --- Recovery Timeline ---
st.markdown("### ⏱ Rough Recovery Timeline")
st.markdown("Most hangovers peak 6–8 hours after your last drink and resolve within 24 hours. Here's what to focus on at each stage:")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Hours 0–2", "Hydrate", "Water + electrolytes first")
col2.metric("Hours 2–4", "Rest", "Sleep if possible")
col3.metric("Hours 4–6", "Eat", "Light food only")
col4.metric("Hours 6+", "Move", "Fresh air + short walk")

st.divider()

# --- Do's and Don'ts ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### ✅ Do This")
    st.markdown("""
- **Water + electrolytes** — both, not just one
- **Eggs** — cysteine helps break down acetaldehyde
- **Bananas** — replenish potassium
- **Toast or oats** — stabilize blood sugar
- **Sleep** — your body repairs during rest
- **Ibuprofen** — safe with food for headache relief
- **Short walk** — boosts circulation and mood
- **B vitamins** — alcohol depletes B1, B6, B12
    """)

with col2:
    st.markdown("### ❌ Skip This")
    st.markdown("""
- **Alcohol** — delays recovery, doesn't fix it
- **Greasy food first thing** — irritates an already inflamed stomach
- **Tylenol/acetaminophen** — dangerous while alcohol is metabolizing
- **Intense exercise** — you're dehydrated and your heart rate is already elevated
- **Caffeine before hydrating** — worsens dehydration and headache
- **Energy drinks** — high sugar + caffeine is rough on an irritated stomach
- **Big decisions** — your cortisol is elevated and judgment is impaired
    """)

st.divider()

# --- Workout Note ---
st.markdown("### 🏋️ What About Working Out?")
st.markdown("""
Short answer: **not today, and here's why that's actually the right call.**

When you're hungover your body is dehydrated, your electrolytes are depleted, your blood sugar is low, and your liver is still processing. Exercise on top of that raises your heart rate, increases dehydration, and puts extra stress on a system that's already working hard.

**What's actually fine:**
- A 15–30 minute walk — helps circulation, gets fresh air, releases endorphins without overloading your system
- Light stretching or gentle yoga
- Rest — recovery is not wasted time, it's part of training

**What to avoid:**
- High intensity cardio or HIIT
- Heavy strength training — performance will be significantly impaired and injury risk goes up

Your gains are not going anywhere. Come back tomorrow fully fueled and you'll have a better session than you would've had today anyway.
""")

st.divider()

# --- When to Seek Help ---
st.markdown("### 🚨 When to Get Actual Help")
st.error("""
Go to urgent care or call someone if you experience:

- Persistent vomiting that prevents keeping any fluids down
- Chest pain or irregular heartbeat
- Seizures or extreme confusion
- Difficulty breathing
- Bluish tint to lips or fingernails

These can be signs of alcohol poisoning — a genuine medical emergency.
""")

st.divider()
st.caption("⚠️ This page is for general wellness information only and is not medical advice. Always consult a healthcare professional for personal medical guidance.")
