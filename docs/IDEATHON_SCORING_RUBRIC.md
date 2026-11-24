# Ideathon Scoring Rubric

Attach this file to the Kompass agents `ideathon-rank` (primary) and `ideathon-pitch` (for the scores they carry over).

The rubric sets the criteria, the scale, the weighting, the ranking order and the output keys. Agents must follow it exactly. Do not add, rename or drop criteria.

## 1. Scale

Every score is a number from 0 to 10, to one decimal place at most. The anchors below describe 2, 5, 8 and 10. Use the values between them for the middle of each band.

## 2. Criteria

### Relevance: does the idea answer the challenge statements?

- **2:** touches the theme in passing. The idea would not change any challenge.
- **5:** answers one challenge statement, but the link needs an assumption.
- **8:** answers a challenge statement directly. The mechanism is named and the people it helps are clear.
- **10:** answers every challenge statement, and the entry's own words make the link.

Score the fit to the challenge. A link to a company priority is a suggestion for the author and does not lower Relevance.

### Feasibility: can a small team build a first version within the ideathon window?

- **2:** depends on data, hardware or approvals with no route to them.
- **5:** needs data or access the team must request, but the first step is clear.
- **8:** needs tools and data the team can reach. A first version can be described in a few steps.
- **10:** a working prototype is plausible within days, with existing tools and access.

### Impact: how much does the outcome matter if it works?

- **2:** small, local benefit. Few people affected.
- **5:** clear benefit for one group. Not measured.
- **8:** clear benefit for a large group, or a business or customer outcome the entry states.
- **10:** large, measurable benefit, using a measure the entry itself names.

Score only what the entry states. Do not add figures.

### Originality: is the approach new to this organisation?

- **2:** a repeat of something already in use.
- **5:** a known approach applied in a new place.
- **8:** a new combination or mechanism for this problem.
- **10:** a new approach that the entry explains and the organisation has not tried.

Unusual ideas are not marked down on Feasibility or Relevance for being unusual. Creativity comes first.

## 3. Panel and audience scores

Each criterion gets two scores, both 0 to 10:

- **panelScore:** the agent's score for the criterion, from the anchors above, read from the entry's own text.
- **audienceScore:** the same value for every criterion of an entry, taken from its audience votes. Set `audienceScore = 10 × entry votes ÷ highest votes among the ideathon's entries`, rounded to one decimal place. If no entry has any votes yet, use 0 and say "no audience votes yet" in the rationale.

The entries data gives each entry `audience_votes` (a count) and `panel_avg` with `panel_n` (the human panel's average and number of scores, on a 1 to 10 scale). The human panel average is context for the rationale only. Do not put it into the formulas.

## 3a. Entries without text

If an entry has no problem or solution text, do not score it. Set every `panelScore`, `audienceScore` and `weightedScore` to `null`, set `overall.weightedTotal` to `null`, and write "entry text not available" as the rationale. Rank these entries last. Never fill in a score for an entry you cannot read.

## 4. Weighted scores

Weights come from the run input as `weights.panel` and `weights.audience`. Typical values are 0.7 and 0.3. If they do not sum to 1, divide each by their total first.

For each criterion:

`weightedScore = panelScore × weights.panel + audienceScore × weights.audience` (round to one decimal place)

For the whole entry:

`overall.weightedTotal = mean of the four weightedScore values` (round to two decimal places)

Relevance gate: if the Relevance score is below 3, cap `overall.weightedTotal` at 4 and say so in the rationale. An entry that does not answer the challenge cannot rank high on its other criteria alone. IdeaKonnekt applies the same gate when it saves scores.

### Worked example

Panel 8, audience 7, weights panel 0.7 and audience 0.3:

`weightedScore = 8 × 0.7 + 7 × 0.3 = 5.6 + 2.1 = 7.7`

## 5. Ranking

Rank every entry the tool returns, highest `overall.weightedTotal` first. Rank 1 is the best. If two entries tie, the one with the higher Impact `weightedScore` ranks first. Do not drop any entry from the list.

## 6. Pitch rules

These apply to the pitch agent.

- Do not re-score. If `shortlist_suggestion` is in the input, copy it unchanged.
- If it is not in the input, score the entries with this rubric. Use the weights from the input, or 0.7 and 0.3 if none are given, and say which weights you used in the rationale.
- Use only figures written in the entry. Where a success measure needs a number the entry does not give, write "to be set by the team". Never write placeholders such as [X], [weekly / daily] or TBD.
- `oneLiner`: under 20 words. States the problem and the outcome.
- `problem`, `solution`, `ask`: one or two sentences each, in the author's terms. `ask` says what the team needs to go forward.
- `successCriteria`: two to four items, each one checkable against the entry.

## 7. Output rules

- Reply with a single JSON object. No markdown fence. No text before or after it.
- Use only the keys in the agent prompt. Do not add keys.
- Never invent entries. Use only ideaIds returned by the tools or present in the input.
- Never name people. Never de-anonymise an entry.
