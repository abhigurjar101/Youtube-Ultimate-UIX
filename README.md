# YouTube analytics and transcript exploration

A collection of Streamlit dashboard variants for researching YouTube topics, video statistics, title sentiment, and transcripts. `app.py` also contains an optional Gemini-assisted transcript analysis flow.

## Local setup

```bash
git clone https://github.com/abhigurjar101/Youtube-Ultimate-UIX.git
cd Youtube-Ultimate-UIX
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` locally with `YOUTUBE_API_KEY` and, for optional model analysis, `GOOGLE_API_KEY`. Keep this file out of Git. Launch the primary variant with `streamlit run app.py`.

## Repository map

`app.py`, `app1.py`, `appF.py`, and `appui.py` are alternate dashboard implementations. They are not separate deployed products. The primary app uses YouTube search/statistics, TextBlob title sentiment, transcript retrieval, and optional Google model calls.

## Scope

Earnings estimates depend on a user-selected RPM assumption. Relative scores do not predict guaranteed growth, and AI transcript analysis can be incorrect. API quotas, model availability, transcript access and service charges depend on the providers. Optional model calls send transcript content to the selected service.

Current gaps include API mocks, missing-key handling, empty-result handling, and a dependency compatibility check for the transcript and Google SDKs. No live API or deployment verification is claimed by this documentation update.

[Abhi Kumar Gurjar](https://www.linkedin.com/in/abhigurjar)
