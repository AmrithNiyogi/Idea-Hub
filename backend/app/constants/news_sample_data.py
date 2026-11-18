"""Fictional placeholder AI Newsletter content, used until the Kompass agent is attached.

Every organisation, product, publication and number below is invented. Do not
present this as real news; the UI labels these categories as sample data.
"""

from __future__ import annotations

# slug -> (brief, [(title, summary, why_it_matters, source_name, hours_ago)])
NEWS_SAMPLE_STORIES: dict[str, tuple[str, list[tuple[str, str, str, str, int]]]] = {
    "ai": (
        "Open-weight models and cheaper inference dominated the week. Kestrel Labs released a "
        "70B model with a very long context window, Orbis Silicon pitched a lower cost per token, "
        "and an independent test suite questioned how well agent frameworks hold up on long tasks.",
        [
            (
                "Kestrel Labs releases Tern-2, an open-weight 70B model with a 256K context window",
                "The model ships under a permissive license with weights and a reference inference "
                "stack. The lab's technical report shows competitive results on public reasoning and "
                "coding benchmarks.",
                "Teams that must run models on their own infrastructure get a stronger starting point "
                "without a licensing negotiation.",
                "Brightwater Tech Daily",
                3,
            ),
            (
                "Orbis Silicon says its next accelerator cuts inference cost per token by about 40%",
                "The company compared its new part against its previous generation on a mix of "
                "chat and retrieval workloads. Independent numbers are not yet available.",
                "Inference is now the largest cost for many AI products, so hardware efficiency "
                "changes unit economics directly.",
                "Meridian Ledger",
                7,
            ),
            (
                "Independent test suite finds agent frameworks fail on long multi-step tasks more "
                "often than vendors report",
                "Researchers ran 12 frameworks on 300 tasks of 20 or more steps. Success rates fell "
                "sharply after step 10, mostly from lost context and repeated tool errors.",
                "Anyone planning to automate multi-step work should test at realistic length, "
                "not on short demos.",
                "Brightwater Tech Daily",
                20,
            ),
            (
                "Lumen Assist adds an on-device mode that keeps prompts off the cloud",
                "The assistant now runs a compact model locally for drafting and summarising, and "
                "only calls the cloud model when the user opts in per request.",
                "Regulated teams that could not use cloud assistants now have a path to adopt one.",
                "Meridian Ledger",
                30,
            ),
            (
                "Study of 2,400 engineering teams links AI code review to faster merges, with caveats",
                "Teams using AI review merged changes about 18% faster, but the gain disappeared on "
                "teams without strong test coverage, where more defects reached production.",
                "Speed gains depend on the safety net around the tool, not the tool alone.",
                "Brightwater Tech Daily",
                52,
            ),
            (
                "Open-source speech model closes the gap with paid transcription across 40 languages",
                "A community-trained model matched a commercial service on word error rate in most "
                "of the languages tested and is small enough to run on a laptop.",
                "Cheaper, private transcription becomes realistic for meetings and support calls.",
                "Meridian Ledger",
                90,
            ),
        ],
    ),
    "ai-business": (
        "Vendors are turning AI agents into default features, and the money is following. A large "
        "software suite bundled agents at no extra charge, a procurement startup raised a growth "
        "round, and a workplace survey showed adoption outpacing training.",
        [
            (
                "Vantora bundles AI agents into its enterprise suite at no extra charge",
                "Customers on existing plans get agents for ticket triage, invoice matching and "
                "report drafting. Usage beyond a monthly allowance is billed per task.",
                "Bundling moves AI from a pilot budget line to a default feature procurement teams "
                "must evaluate.",
                "Meridian Ledger",
                4,
            ),
            (
                "Procurement startup Haldane raises $85M to automate supplier negotiations",
                "The round was led by a growth fund and will fund expansion into manufacturing "
                "and logistics. The company says its agent handles first-round price talks.",
                "Investors are backing narrow, workflow-specific agents over general assistants.",
                "Harbor Business Review",
                26,
            ),
            (
                "Survey: 7 in 10 employees use AI tools weekly, but fewer than 3 in 10 have had training",
                "The poll of 5,000 workers across 11 countries also found that most use tools their "
                "employer has not approved.",
                "Unsanctioned use is a security and quality risk that policy alone has not fixed.",
                "Harbor Business Review",
                49,
            ),
            (
                "Retailer reports 22% fewer support escalations after rolling out an AI help agent",
                "The agent resolves order and returns questions and hands off with a summary when "
                "it is unsure. Customer satisfaction scores were flat.",
                "Flat satisfaction with fewer escalations is the result most support leaders want.",
                "Meridian Ledger",
                70,
            ),
            (
                "Consulting firm cuts junior analyst hiring as AI drafts first-pass research",
                "The firm said it will hire fewer entry-level analysts next year and retrain others "
                "to review and verify AI-produced work.",
                "Entry-level roles are changing first, which affects how future experts get trained.",
                "Harbor Business Review",
                120,
            ),
        ],
    ),
    "ai-sports": (
        "Officiating and training were the story in sports AI this week. A football league began "
        "testing computer-vision offside calls, a club published injury-risk results, and a "
        "broadcaster launched personalised highlights.",
        [
            (
                "Premier-tier football league trials AI-assisted offside calls in 12 matches",
                "Cameras and pose-tracking produce a ruling in under 4 seconds. Human officials "
                "make the final decision during the trial.",
                "Faster, more consistent calls could shorten stoppages that fans complain about most.",
                "Northgate Sports Desk",
                5,
            ),
            (
                "Club's player-tracking model flags injury risk two weeks earlier than staff alone",
                "Over one season the model flagged 61% of soft-tissue injuries before they happened, "
                "with a false-alarm rate the medical team described as manageable.",
                "Earlier warnings let coaches adjust training load before a player is lost for weeks.",
                "Northgate Sports Desk",
                30,
            ),
            (
                "Broadcaster launches personalised highlight reels generated within minutes of full time",
                "Viewers choose a team or player and get a cut that follows what they care about.",
                "Highlights built per viewer change how leagues package and sell their content.",
                "Brightwater Tech Daily",
                56,
            ),
            (
                "Marathon organisers use crowd-flow forecasts to reduce start-line bottlenecks",
                "A model trained on past races predicted pace clusters and let organisers stagger "
                "start waves, cutting average wait time by about a third.",
                "Operational AI quietly improves participant experience at large events.",
                "Northgate Sports Desk",
                95,
            ),
        ],
    ),
    "ai-healthcare": (
        "Clinical evidence arrived this week. A hospital trial of an imaging assistant reported "
        "earlier detections, a drug-discovery model produced candidates now entering lab testing, "
        "and a regulator outlined how it will review adaptive clinical AI.",
        [
            (
                "Hospital trial of an AI imaging assistant finds 11% more early-stage cases",
                "Across 40,000 screening scans, radiologists using the assistant flagged more early "
                "findings without a rise in recalls. The study has not yet been peer reviewed.",
                "Evidence from real screening workflows matters more than benchmark accuracy.",
                "Clinical Futures Digest",
                6,
            ),
            (
                "Ostrava Bio moves three AI-designed compounds into lab testing",
                "The candidates target a rare inflammatory condition and were selected from several "
                "million virtual molecules. Lab results will show whether predictions hold.",
                "Faster candidate selection shortens the earliest and most expensive stage of discovery.",
                "Clinical Futures Digest",
                30,
            ),
            (
                "Regulator outlines review path for clinical AI that updates after approval",
                "Developers can pre-agree a change plan, so approved models can be retrained within "
                "set limits without a new submission each time.",
                "Predictable rules for updates make it easier for hospitals to adopt models that improve.",
                "Harbor Business Review",
                52,
            ),
            (
                "Nurses report saving about 40 minutes a shift with AI-drafted handover notes",
                "A six-ward pilot found the drafts needed edits on roughly one note in five. "
                "Staff said accuracy checks were still essential.",
                "Documentation time is a leading driver of clinician burnout.",
                "Clinical Futures Digest",
                78,
            ),
            (
                "Researchers show a speech model can flag early signs of cognitive decline in phone calls",
                "In a 900-person study the model separated early cases from controls with moderate "
                "accuracy. The authors caution it is a screening aid, not a diagnosis.",
                "Low-cost screening could reach people who rarely see a specialist.",
                "Brightwater Tech Daily",
                110,
            ),
        ],
    ),
    "ai-finance": (
        "Banks are moving from experiments to production. A large lender deployed an adviser "
        "assistant, a payments firm cut false fraud alerts, and a supervisor asked firms to "
        "document how AI-driven credit decisions are explained.",
        [
            (
                "Corvane Bank deploys an AI assistant to 6,000 financial advisers",
                "Advisers use it to prepare client meetings and summarise portfolios. Every "
                "client-facing output is reviewed by a person before it is sent.",
                "A regulated rollout at this scale shows where compliance teams are comfortable.",
                "Harbor Business Review",
                5,
            ),
            (
                "Payments firm Tallis cuts false fraud alerts by 30% with a new detection model",
                "The model looks at behaviour across a session instead of single transactions. "
                "Confirmed fraud catch rates were unchanged.",
                "Fewer false alerts means fewer blocked legitimate payments and less manual review.",
                "Meridian Ledger",
                40,
            ),
            (
                "Supervisor asks lenders to document how AI credit decisions are explained to customers",
                "The guidance does not ban any technique but expects firms to show reasons a customer "
                "can understand when an application is declined.",
                "Explainability is becoming a compliance requirement, not a nice-to-have.",
                "Harbor Business Review",
                66,
            ),
            (
                "Asset manager tests AI summaries of earnings calls across 3,000 companies",
                "Analysts review the summaries for errors before use. The firm says the main gain is "
                "coverage of smaller companies that previously got little attention.",
                "Wider coverage can surface opportunities human teams never had time to read.",
                "Meridian Ledger",
                100,
            ),
        ],
    ),
    "ai-policy": (
        "Rules and safety testing moved forward together. A regulator published draft guidance for "
        "general-purpose models, a safety lab released evaluation results across several models, "
        "and a court heard its first case on AI-generated training data.",
        [
            (
                "Regulator publishes draft guidance for general-purpose AI model providers",
                "The draft asks providers to document training data sources, test for misuse and "
                "report serious incidents. A public comment period runs for eight weeks.",
                "It sets the compliance baseline builders will be measured against.",
                "Harbor Business Review",
                24,
            ),
            (
                "Independent safety lab releases evaluation results for six leading models",
                "Models were tested on resistance to misuse and on honest reporting of uncertainty. "
                "Results varied widely, and the lab published its methods for others to repeat.",
                "Shared, repeatable tests give buyers something better than vendor claims.",
                "Brightwater Tech Daily",
                48,
            ),
            (
                "Court hears first case over use of AI-generated data to train new models",
                "The dispute centres on whether outputs of one model can be used to train a "
                "competitor under the original service terms. A ruling is expected next quarter.",
                "The outcome could shape how companies source training data.",
                "Harbor Business Review",
                80,
            ),
            (
                "Standards body opens work on a common format for AI incident reports",
                "A working group of vendors and auditors will define the fields an incident report "
                "should contain so reports can be compared across organisations.",
                "A common format makes it possible to learn from failures across the industry.",
                "Brightwater Tech Daily",
                120,
            ),
        ],
    ),
}
