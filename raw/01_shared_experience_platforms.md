# notes on experience-based social platforms

read the patientslikeme paper today. interesting model — people document their treatment journeys and the platform finds others on similar paths. but it's really structured around disease categories which feels limiting. what if the experience doesn't fit a category neatly?

7 cups model: volunteer listeners matched to people seeking support. uses structured conversation flows. feels a bit scripted when i've tried it. the matching is pretty rough — mostly just "are you available right now."

key insight from today: the fundamental claim is that empathy is most effectively transmitted between people who have navigated the same territory. this feels right intuitively but is it actually true? need to find research on this.

---

reddit communities do this at massive scale with zero algorithm. r/cancer r/grief r/survivorship — people just self-select into their category. works surprisingly well because the signal (shared experience) is so strong. the community itself does the matching implicitly.

togetherall is interesting — anonymous, licensed to universities. they say anonymity reduces stigma. but also reduces the ability to build actual relationships? tradeoff.

---

data problem: how do you represent "experience" in a machine-readable form? three approaches seem to exist:
- tag taxonomies (pick your experience from a list) — queryable but loses nuance. "divorce" doesn't capture "divorce after 20 year marriage with 3 kids"
- free text narratives (just write your story) — rich but hard to query
- structured interview (platform asks guided questions) — middle ground

we're probably going with some hybrid. LLM can extract structure from free text. best of both?

---

metrics for matching quality: this is hard. you can't just measure accuracy the way you do for product recommendation because both parties have to be satisfied. relevant metrics:
- did they actually start a conversation?
- how long did they talk?
- did the mentee come back?
- did the mentor report feeling useful?

also thinking about mentor burnout. this is underrated. if you match someone with too many needy people they'll just stop showing up. need capacity limits.

---

privacy is a big deal here. these are people sharing their worst moments. need:
- opt-in anonymity per experience (some things you'll share publicly, others never)
- time-decay on experiences (your 2019 divorce shouldn't define your profile forever)
- consent-first for any research use

TODO: think more about the federated identity question — can we have a profile that's only visible to matched users? feels right.
