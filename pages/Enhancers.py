from pathlib import Path

import pandas as pd
import streamlit as st



st.set_page_config(
    page_title="Enhancer Guide",
    page_icon="🧬",
    layout="wide",
)


# CUSTOM CSS

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .page-subtitle {
            color: #aeb6c2;
            font-size: 1.05rem;
            margin-bottom: 1.5rem;
        }

        .enhancer-number {
            color: #8c96a5;
            font-size: 1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08rem;
            margin-bottom: 0;
        }

        .enhancer-title {
            font-size: 2.4rem;
            font-weight: 800;
            margin-top: 0;
            margin-bottom: 1.4rem;
        }

        .info-label {
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .info-text {
            color: #d6dae0;
            font-size: 1rem;
            line-height: 1.65;
            margin-top: 0;
            margin-bottom: 1.2rem;
        }

        .image-placeholder {
            border: 2px dashed #4e5663;
            border-radius: 16px;
            min-height: 930px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #8f98a6;
            padding: 1.5rem;
            margin-top: 1rem;
        }

        .score-text {
            font-weight: 700;
            margin-top: 0.4rem;
        }

        hr {
            margin-top: 3rem !important;
            margin-bottom: 3rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)



PROJECT_FOLDER = Path(__file__).resolve().parent.parent
IMAGE_FOLDER = PROJECT_FOLDER / "images"


st.markdown("<div style='margin-top: 45px;'></div>", unsafe_allow_html=True)

st.page_link("Toolkit.py", label="← Back to Home")
st.title("🧬 10 Trending Enhancers")

st.markdown(
    """
    <p class="page-subtitle">
        A general overview of commonly discussed hormones,
        peptides, steroids, and performance-enhancing compounds.
    </p>
    """,
    unsafe_allow_html=True,
)

st.warning(
    """
    **Educational information only:** This page is not medical advice.
    Some of these substances may be illegal, unapproved, counterfeit, or
    dangerous when used without qualified medical supervision.
    """
)



st.subheader("Non FDA Approved")

not_fda_approved = pd.DataFrame(
    {
        "Enhancer": [
            "Retatrutide",
            "Trenbolone",
            "GHK-Cu injections",
            "Anavar",
            "Dianabol for bodybuilding",
            "SARMs",
            "Winstrol"
        ],
    }
)

st.dataframe(
    not_fda_approved,
    hide_index=True,
    width="stretch",
)

st.divider()



enhancers = [
    {
        "name": "Testosterone",
        "image": "TEST.PNG",
        "reason": "Build muscle, boost energy, and support sex drive.",
        "fact": (
            "Testosterone is one of the most extensively studied hormones "
            "used in clinical medicine."
        ),
        "side_effects": (
            "Suppression of natural testosterone production, acne, hair loss, "
            "increased red-blood-cell levels, cardiovascular strain, testicular "
            "shrinkage, and fertility problems."
        ),
        "score": 9,
        "score_description": "Extensive human and clinical research",
    },
    {
        "name": "Retatrutide",
        "image": "RETA.PNG",
        "reason": (
            "Investigational treatment for weight loss and metabolic conditions."
        ),
        "fact": (
            "Retatrutide is still being studied and has shown promising results "
            "in clinical trials, but it is not currently FDA approved."
        ),
        "side_effects": (
            "Nausea, vomiting, diarrhea, constipation, stomach discomfort, "
            "and other effects that are still being investigated."
        ),
        "score": 4,
        "score_description": "Early but promising clinical research",
    },
    {
        "name": "Anavar",
        "image": "VAR.PNG",
        "reason": (
            "Often discussed for maintaining lean mass, strength, and a drier "
            "appearance."
        ),
        "fact": (
            "Oxandrolone has legitimate prescription uses for certain medical "
            "conditions involving severe weight loss and recovery."
        ),
        "side_effects": (
            "Liver stress, altered cholesterol, hormonal suppression, and "
            "potential irreversible masculinizing effects in women."
        ),
        "score": 6,
        "score_description": (
            "Medical research exists, but bodybuilding use carries added risks"
        ),
    },
    {
        "name": "Trenbolone",
        "image": "TREN.PNG",
        "reason": (
            "Commonly discussed for rapid muscle gain, strength, and fat loss."
        ),
        "fact": (
            "Trenbolone was developed for veterinary use and is not approved "
            "for human use."
        ),
        "side_effects": (
            "Sleep disruption, night sweats, anxiety or mood changes, "
            "cardiovascular strain, kidney stress, and increased blood pressure."
        ),
        "score": 3,
        "score_description": "Limited reliable human research",
    },
    {
        "name": "Human Growth Hormone (HGH)",
        "image": "HGH.PNG",
        "reason": (
            "Used medically for certain growth-hormone disorders and discussed "
            "for muscle growth, recovery, and anti-aging."
        ),
        "fact": (
            "Prescription HGH is approved for specific diagnosed medical "
            "conditions, not general bodybuilding or anti-aging use."
        ),
        "side_effects": (
            "Joint pain, swelling, numbness, carpal-tunnel symptoms, insulin "
            "resistance, and possible abnormal tissue growth."
        ),
        "score": 6,
        "score_description": (
            "Strong medical research for approved uses, less support for enhancement"
        ),
    },
    {
        "name": "GHK-Cu",
        "image": "GHK.PNG",
        "reason": (
            "Commonly discussed for skin appearance, wound healing, and hair care."
        ),
        "fact": (
            "GHK-Cu is a copper-binding peptide studied for tissue-repair and "
            "skin-related effects."
        ),
        "side_effects": (
            "Topical products may cause irritation or allergic reactions. "
            "Injected forms are less studied and may cause pain, swelling, "
            "infection, or other unknown effects."
        ),
        "score": 5,
        "score_description": "Some laboratory and topical-use research",
    },
    {
        "name": "Semaglutide",
        "image": "SEMA.PNG",
        "reason": (
            "Used for blood-sugar control and, in certain formulations, "
            "long-term weight management."
        ),
        "fact": (
            "Semaglutide is the active ingredient in prescription medicines "
            "such as Ozempic and Wegovy, which have different approved uses."
        ),
        "side_effects": (
            "Nausea, vomiting, diarrhea, constipation, abdominal discomfort, "
            "gallbladder problems, and rare but serious complications."
        ),
        "score": 10,
        "score_description": "Extensive clinical testing and approved medical uses",
    },
    {
        "name": "Dianabol",
        "image": "DIANABOL.PNG",
        "reason": (
            "Commonly discussed for rapid increases in muscle size and strength."
        ),
        "fact": (
            "Methandrostenolone is an oral anabolic steroid with significant "
            "health risks and no approved modern bodybuilding use."
        ),
        "side_effects": (
            "Liver injury, fluid retention, high blood pressure, altered "
            "cholesterol, hormonal suppression, and breast-tissue development."
        ),
        "score": 4,
        "score_description": "Older research exists, but modern safety data are limited",
    },
    {
        "name": "SARMs",
        "image": "SARMS.PNG",
        "reason": (
            "Marketed as compounds that may produce muscle-building effects "
            "with fewer androgenic effects than traditional steroids."
        ),
        "fact": (
            "SARMs are not FDA-approved bodybuilding drugs, and products sold "
            "online may contain incorrect or undisclosed ingredients."
        ),
        "side_effects": (
            "Hormonal suppression, liver injury, altered cholesterol, sexual "
            "health problems, mood changes, and possible cardiovascular risks."
        ),
        "score": 2,
        "score_description": "Limited long-term human safety research",
    },
    {
        "name": "Winstrol",
        "image": "WIN.PNG",
        "reason": (
            "Commonly discussed for strength, a leaner appearance, and less "
            "water retention."
        ),
        "fact": (
            "Stanozolol is an anabolic steroid that has had limited medical uses "
            "but carries substantial risks when used for physique enhancement."
        ),
        "side_effects": (
            "Joint discomfort, liver stress, altered cholesterol, cardiovascular "
            "risk, hormonal suppression, and hair loss."
        ),
        "score": 4,
        "score_description": "Some medical data, but limited support for enhancement use",
    },
]



def display_enhancer(enhancer: dict, number: int) -> None:
    image_column, information_column = st.columns(
        [2, 2.4],
        gap="large",
        vertical_alignment="top",
    )

    with image_column:
        image_path = IMAGE_FOLDER / enhancer["image"]

        if image_path.exists():
            st.image(
                str(image_path),
                caption=enhancer["name"],
                width="stretch",
            )
        else:
            st.markdown(
                f"""
                <div class="image-placeholder">
                    <div>
                        <strong>Image space</strong><br><br>
                        Add this file:<br>
                        <code>images/{enhancer["image"]}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with information_column:
        st.markdown(
            f'<p class="enhancer-number">Enhancer {number}</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<p class="enhancer-title">{enhancer["name"]}</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p class="info-label">🎯 Reason for use</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="info-text">{enhancer["reason"]}</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p class="info-label">🧠 Key fact</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="info-text">{enhancer["fact"]}</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p class="info-label">⚠️ Possible side effects</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p class="info-text">{enhancer["side_effects"]}</p>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<p class="info-label">📚 Research score</p>',
            unsafe_allow_html=True,
        )

        st.progress(enhancer["score"] / 10)

        st.markdown(
            f"""
            <p class="score-text">
                {enhancer["score"]}/10 — {enhancer["score_description"]}
            </p>
            """,
            unsafe_allow_html=True,
        )



for index, enhancer in enumerate(enhancers, start=1):
    display_enhancer(enhancer, index)

    if index < len(enhancers):
        st.divider()



st.divider()

st.caption(
    "Research scores are simple educational ratings for this app, not official "
    "medical or regulatory rankings."
)
