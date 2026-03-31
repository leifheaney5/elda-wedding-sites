"""
FAQ retrieval source chunks.
Answers shown on /about/faq are selected from these chunks only.
"""

FAQ_SOURCE_CHUNKS = {
    "best_time": (
        "A common recommendation is scheduling ceremonies 1–2 hours before sunset for comfortable "
        "lighting and guest experience. Final timing should align with venue rules and seasonal conditions.",
        "FAQ content archive",
    ),
    "payment_process": (
        "Depending on the package you choose, a $500-$2500 non-refundable initial payment secures "
        "your date and applies toward your total. The final balance is due 30 days before your wedding.",
        "FAQ content archive",
    ),
    "license": (
        "Marriage licenses must be obtained in the local jurisdiction where the ceremony is held. "
        "Confirm waiting periods and validity windows early in the planning timeline.",
        "FAQ content archive",
    ),
    "remote_planning": (
        "Nearly 90% of couples plan from out of town. Full access to the online planning portal, "
        "email/phone support, and optional FaceTime meetings is available.",
        "FAQ content archive",
    ),
    "efficiency": (
        "Most wedding planners average 420hr for a full service wedding. They do 10-15hr in total.",
        "Client notes provided (ELDA Wedding Sites High Level Overview)",
    ),
    "workflow": (
        "The lead should come directly from the website, then the user should be able to book. "
        "An upsell feature would be useful as well.",
        "Client notes provided (User Interface and Functionality Planning Meeting)",
    ),
    "portal_scope": (
        "I am only developing the PORTAL, NOT the external-facing WEBSITE.",
        "Client notes provided (ELDA Wedding Sites High Level Overview)",
    ),
    "coordination": (
        "We handle it all. From securing permits and setting up ceremony decor to "
        "providing your officiant, flowers, and photographer, everything is seamlessly managed under one roof.",
        "Vow renewal content archive",
    ),
    "sunset_window": (
        "Common ceremony windows are tied to natural light and guest comfort. Typical recommendations are late afternoon to early evening.",
        "Planning and FAQ content archive",
    ),
    "backup_weather": (
        "Every outdoor wedding should include an inclement weather backup plan to keep timelines and guest experience on track.",
        "Planning guide content archive",
    ),
    "noise_music": (
        "Music and noise rules vary by location and timing, so final entertainment plans should be confirmed against local requirements.",
        "Planning guide content archive",
    ),
    "alcohol_rules": (
        "Alcohol service and consumption permissions are venue and location dependent and must be confirmed in advance.",
        "Planning guide content archive",
    ),
    "menu_scope": (
        "Catering options include BBQ, Taco, Traditional, Pasta Bar, Italian, Brunch, and Premium enhancements with customization options.",
        "Catering content archive",
    ),
    "timeline_focus": (
        "A sample timeline should be finalized before wedding week, including setup, ceremony flow, photos, and reception transitions.",
        "Planning timeline content archive",
    ),
    "remote_clients": (
        "Most couples plan from out of town and can coordinate through portal workflows, messaging, and scheduled virtual updates.",
        "Client notes and FAQ content archive",
    ),
}


def get_faq_entries():
    return [
        {
            "question": "What is the best time of day for a ceremony?",
            "answer": FAQ_SOURCE_CHUNKS["best_time"][0],
            "source": FAQ_SOURCE_CHUNKS["best_time"][1],
        },
        {
            "question": "How do payments work?",
            "answer": FAQ_SOURCE_CHUNKS["payment_process"][0],
            "source": FAQ_SOURCE_CHUNKS["payment_process"][1],
        },
        {
            "question": "How do we handle licenses and legal filing?",
            "answer": FAQ_SOURCE_CHUNKS["license"][0],
            "source": FAQ_SOURCE_CHUNKS["license"][1],
        },
        {
            "question": "Can we plan remotely?",
            "answer": FAQ_SOURCE_CHUNKS["remote_planning"][0],
            "source": FAQ_SOURCE_CHUNKS["remote_planning"][1],
        },
        {
            "question": "What makes your planning process different?",
            "answer": FAQ_SOURCE_CHUNKS["efficiency"][0],
            "source": FAQ_SOURCE_CHUNKS["efficiency"][1],
        },
        {
            "question": "How should inquiry-to-booking flow work?",
            "answer": FAQ_SOURCE_CHUNKS["workflow"][0],
            "source": FAQ_SOURCE_CHUNKS["workflow"][1],
        },
        {
            "question": "What has been the focus for portal planning?",
            "answer": FAQ_SOURCE_CHUNKS["portal_scope"][0],
            "source": FAQ_SOURCE_CHUNKS["portal_scope"][1],
        },
        {
            "question": "Do you coordinate vendors and setup details?",
            "answer": FAQ_SOURCE_CHUNKS["coordination"][0],
            "source": FAQ_SOURCE_CHUNKS["coordination"][1],
        },
        {
            "question": "What ceremony time is most recommended?",
            "answer": FAQ_SOURCE_CHUNKS["sunset_window"][0],
            "source": FAQ_SOURCE_CHUNKS["sunset_window"][1],
        },
        {
            "question": "Do we need a weather backup plan for outdoor ceremonies?",
            "answer": FAQ_SOURCE_CHUNKS["backup_weather"][0],
            "source": FAQ_SOURCE_CHUNKS["backup_weather"][1],
        },
        {
            "question": "How are music and sound rules handled?",
            "answer": FAQ_SOURCE_CHUNKS["noise_music"][0],
            "source": FAQ_SOURCE_CHUNKS["noise_music"][1],
        },
        {
            "question": "How is alcohol planning handled?",
            "answer": FAQ_SOURCE_CHUNKS["alcohol_rules"][0],
            "source": FAQ_SOURCE_CHUNKS["alcohol_rules"][1],
        },
        {
            "question": "What menu options are available for catering?",
            "answer": FAQ_SOURCE_CHUNKS["menu_scope"][0],
            "source": FAQ_SOURCE_CHUNKS["menu_scope"][1],
        },
        {
            "question": "When should timeline details be finalized?",
            "answer": FAQ_SOURCE_CHUNKS["timeline_focus"][0],
            "source": FAQ_SOURCE_CHUNKS["timeline_focus"][1],
        },
        {
            "question": "Can we plan everything remotely?",
            "answer": FAQ_SOURCE_CHUNKS["remote_clients"][0],
            "source": FAQ_SOURCE_CHUNKS["remote_clients"][1],
        },
    ]
