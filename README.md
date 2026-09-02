# YouTube Strategy & Packaging Intelligence Pro 🚀

[![CI Pipeline](https://github.com/TarunSharma-Coder/YT-Strategy-Pro/actions/workflows/ci.yml/badge.svg)](https://github.com/TarunSharma-Coder/YT-Strategy-Pro/actions/workflows/ci.yml)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=flat&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Bundler-Vite%208-646CFF?style=flat&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

High-performance YouTube intelligence platform designed for creators to discover 10x viral outliers, uncover topic gap heatmaps, score multi-modal thumbnail packaging, and extract audience buying intent from comments.


This tool analyses:

- videos from your selected date range from your channel
- videos from your selected date range from up to 5 competitor channels
- title length
- word count
- has number
- has question
- has year
- views
- video upload date
- video age
- views per day
- keywords used in titles
- hook keywords
- search tags
- month-wise competitor publishing, upload dates, views, keywords, tags, and trend charts for a selected date range
- best 5 title suggestions from your next video description
- duplicate videos removed by `video_id`
- Shorts and long videos separated with a video type filter
- comment intelligence for selected videos
- title + thumbnail packaging analysis for selected videos or your own uploaded thumbnail/title

Important: public YouTube Data API does not provide CTR for competitor videos. If you have CTR from your own YouTube Studio export, you can upload a CSV with either:

- `video_id,ctr`
- `title,ctr`

## How To Use In VS Code

### 1. Open Project Folder

Open VS Code, then open this folder:

```text
C:\Users\LENOVO\Documents\ChatGPT\YouTube Strategy Analyser
```

### 2. Open Terminal

In VS Code, click:

```text
Terminal > New Terminal
```

### 3. Install Dependencies

Run this command in the VS Code terminal:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `.venv` does not exist, create it first:

```powershell
python -m venv .venv
```

Then run the install command again.

### 4. Add YouTube API Key

Create a file named `.env` in this folder.

Add this line:

```env
YOUTUBE_API_KEY=your_real_api_key_here
```

You can also paste the API key directly in the app sidebar.

For the `Title + Thumbnail Analyzer` tab, add your OpenAI API key in the same `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

For the GLM AI report inside `Comment Intelligence`, add your GLM/Z.AI key too:

```env
GLM_API_KEY=your_glm_api_key_here
```

Optional advanced GLM settings:

```env
GLM_MODEL=glm-5.1
GLM_BASE_URL=https://api.z.ai/api/paas/v4/
```

### 5. Run The App

Run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### 6. Open Browser

Open:

```text
http://localhost:8501
```

### If You See WinError 10013

If the app shows a message like `Failed to establish a new connection` or `WinError 10013`, the code is running but Windows/firewall/proxy is blocking Python from connecting to YouTube API.

Try this:

1. Open this URL in Chrome to confirm Google API is reachable:

```text
https://www.googleapis.com
```

2. Allow these apps in Windows Defender Firewall:

```text
python.exe
Code.exe
```

3. In VS Code, close the terminal with `Ctrl + C`, then run again:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

4. If you use VPN, proxy, office/school Wi-Fi, or antivirus web protection, temporarily switch network or allow `www.googleapis.com`.

### If GLM Shows Insufficient Balance

If Comment Intelligence shows:

```text
Insufficient balance or no resource package. Please recharge.
```

Your GLM/Z.AI key reached the API, but that account does not have enough balance or the selected `GLM_MODEL` is not available in your package.

Fix options:

- recharge or activate a GLM/Z.AI resource package
- use a GLM model included in your package by changing `GLM_MODEL` in `.env`
- keep using the normal rule-based Comment Intelligence ideas without GLM

### 7. Fill Inputs

In the sidebar:

1. Paste your YouTube API key.
2. Paste your channel URL.
3. Paste up to 5 competitor channel URLs, one per line.
4. Write your next video description.
5. Optional: upload CTR CSV for your own channel.
6. Select a video analysis date range.
7. Click `Analyse channels`.

Competitor links can be pasted one per line, comma-separated, or space-separated. These formats work:

```text
https://www.youtube.com/@Competitor1
https://www.youtube.com/@Competitor2
@Competitor3
```

```text
https://www.youtube.com/@Competitor1, https://www.youtube.com/@Competitor2 @Competitor3
```

### 8. Read Reports

Use these tabs:

- `Your Channel`: your selected date-range video analysis
- `Competitors`: separate report for each competitor
- `Monthly Competitor Report`: date-range month-wise competitor content, upload dates, views, charts, keywords, and tags
- `Best Titles`: best 5 suggested titles, keywords, tags, and hooks
- `Growth Reasons`: why selected-range videos may have received high views, weekly upload frequency, and topic relevance
- `Content Gap`: last 30 days academic vs non-academic/strategy comparison and content gap sheets
- `Trend Intelligence`: current window vs previous window topic trend detection
- `Comment Intelligence`: selected-video comment classification and time-frame trends
- `GLM AI comment strategy report`: 10 AI video ideas, audience red flags, and downloadable GLM reports inside Comment Intelligence
- `Title + Thumbnail Analyzer`: selected video or uploaded title + thumbnail packaging intelligence
- `What Should We Post Next`: final ranked recommendations using channel, competitor, outlier, trend, gap, search, and comment signals
- `Keyword Reports`: all-channel keyword and hook performance
- `Downloads`: CSV and Markdown report downloads

Use the sidebar `Video analysis date range` to fetch videos uploaded inside your selected dates. For example, select January 1 to December 31, then click `Analyse channels`.

Use `Max videos/channel` if a channel uploads many videos in that range. Higher values fetch more videos but use more YouTube API quota.

Inside each channel report, use the `Video type` button to switch between:

- `All videos`
- `Shorts`
- `Long videos`

The tables include a `video_type` column so you can easily identify which video is a Short and which one is long-form.

The `Monthly Competitor Report` tab helps you:

- use the sidebar selected date range, for example January to December
- choose one or more competitor channels from the analysed competitor dataset
- use the same selected-range YouTube API data fetched by `Analyse channels`
- see month-wise total videos, total views, Shorts count, long-video count, top video, trending title keywords, and trending tags
- see interactive upload-frequency and views trend charts by day or month
- see all videos with exact upload date in the video sheet
- download monthly summary, keyword report, tag report, chart data, and `selected_date_range_competitor_uploaded_videos.csv`

The `Growth Reasons` tab shows:

- possible reasons why the latest 10 videos performed well or weakly
- whether strong keywords look like market demand across channels
- whether hook words, numbers, questions, or format helped performance
- week-wise upload frequency for your channel and competitors
- topic relevance score for your next video description

The `Content Gap` tab shows:

- last 30 days channel-wise content comparison
- how many academic videos each channel uploaded
- how many non-academic / strategy videos each channel uploaded
- which videos got how many total views
- topic keywords competitors covered but your channel did not
- downloadable comparison CSV, video sheet CSV, and opportunity CSV

The `Opportunity Finder` tab lets you type exact keyword/search-intent phrases such as:

```text
MBA entrance strategy
CAT exam preparation
career roadmap after MBA
```

Add one phrase per line or separate phrases with commas. Then click `Find market opportunities`.

The `Trend Intelligence` tab detects:

- custom date range based trends
- rapidly rising topics
- growing topics
- stable or declining topics
- possible saturation
- topic publishing growth
- view velocity growth
- recent outlier videos driving a trend
- top 7 trending keywords per topic
- keyword-wise trending video count, total views, and best video

The `Comment Intelligence` tab helps you:

- select random, latest, or high-view videos from the analysed list
- fetch top-level YouTube comments for selected videos
- classify comments into Question, Content request, Complaint, Confusion, Praise, Purchase intent, Comparison, Exam anxiety, and Feature/course request
- see which comment type is coming more by day, week, month, or hour of day
- filter comments by comment date range
- get 10 upcoming video ideas based on repeated audience questions, confusion, requests, complaints, and purchase intent
- see 5 full YouTube title suggestions for each idea
- see 4-5 long-tail keyword ideas for each content idea
- see demand score, reason, and proof comment for each idea
- download classified comments, comment summary, and comment trend CSV files

The `Title + Thumbnail Analyzer` tab helps you:

- select one existing video from the analysed date-range videos
- upload your own thumbnail and enter your own title before publishing
- view the current thumbnail, title, views, views per day, and video type
- score title clarity, curiosity, specificity, urgency, emotion, and search vs browse orientation
- analyse visible thumbnail text, face presence/count, emotion, readability, visual hierarchy, simplicity, curiosity, and thumbnail style
- analyse title-thumbnail alignment, complementarity, redundancy, curiosity gap, and message clarity
- get a transparent `Packaging Intelligence Score` from 0-100
- get a `YouTube data fit score` and rank band based on analysed channel/competitor keywords, hooks, title length bucket, and similar high-performing videos
- get 3 strengths, up to 3 weaknesses, specific recommendations, one improved title, and one thumbnail text/angle suggestion

Important: this is not CTR or views prediction. It is packaging analysis and YouTube data comparison based on the channels you analysed.

The `What Should We Post Next` tab answers:

- what should we post next
- which topic has the strongest combined signal
- which 5 titles can be used for that topic
- which long-tail keywords should be targeted
- why the topic is recommended
- which proof video supports the recommendation
- optional live YouTube search validation for recent/ongoing YouTube demand
- niche/category filter so unrelated channels or unrelated category videos are not added to recommendations

The `Downloads` tab includes `selected_date_range_all_uploaded_videos.csv` with upload date, channel, title, video type, views, likes, comments, views/day, duration, keywords, tags, video link, thumbnail link, and video ID.

### 9. Stop App

In VS Code terminal press:

```text
Ctrl + C
```
