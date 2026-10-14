# Kaggle Active Competitions Intelligence & Discussion Knowledge Base

**Generated**: 2026-10-11 17:25:24 UTC
**Source**: Active competition forums union of `sort_by='top'` and `sort_by='active'`.
**Filter**: Filtered to unexpired monetary competitions per Mandate 8.

---

## Competition: `arc-prize-2026-arc-agi-2`

### `[BUG_ALERT]` [697859] Bitterbot's TOPAS Architecture Submission: 11.67% LB vs ~36% Local (Managing TTT Timeouts) (23 comments, `Signal: 17.56`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/697859

> **Message 1 by User (2026-05-07)** [Votes: 10]:
> We used this submission primarily as a pipeline test for our Kaggle setup using an early, not fully-trained checkpoint. We're currently running the TOPAS architecture. It’s a highly efficient, lightweight setup at only ~100M parameters, and it relies heavily on deep recursion.
> 
> Our current compute footprint - we are training on a single consumer-grade RTX 4090. This checkpoint is 14 days into training. We estimate another ~10 days for the model to properly converge.
> 
> Locally, using the same 14-day checkpoint, we are hitting ~36%. The massive drop on the leaderboard comes down in part to time management constraints within the Kaggle environment.
> 
> Because TOPAS utilizes deep recursion, our TTT becomes computationally heavy. During our initial sandbox tests, we were struggling to stay within the strict time limits and kept timing out. While tinkering to ensure the submission would actually complete, we overcompensated on our time-limit thresholds. This resulted in the model bailing out early to save time, ultimately failing to output a prediction on a large chunk of the puzzles.
> 
> Moving forward as we wait for the model to fully converge over the next week and a half, we need to fine-tune our time-management so we convert [[0]] placeholders into real beam outputs.

> **Message 2 by User (2026-05-16)** [Votes: 3]:
> Notebook submission process is kinda flakey.   During our last submission attempt last night the notebook crash within 250s and I assumed we burnt the attempt for the day.  In the morning we had a new leaderboard score of 19.03%, but from a previous version of the notebook.  Makes no sense.  Now I don't know which variables to adjust for the next run.

> **Message 3 by User (2026-05-07)** [Votes: 4]:
> Squeezing your code to fit Kaggle compute limit is what makes this competition challenging. 
> 
> It is good that your first submission went through, even if the score may disappoint you.

> **Message 4 by User (2026-05-08)** [Votes: 1]:
> Tweaked the config, patiently waited for the daily submission to become available… forgot to turn on the accelerator… promptly crashed… burnt the daily submission…   Ugh


---

### `[BUG_ALERT]` [747515] Update on "Kaggle Error" Submissions & Queue Delays (17 comments, `Signal: 14.22`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/747515

> **Message 1 by User (2026-10-10)** [Votes: 1]:
> The current queue delay is around ~33h, so yes, your submission isn't stuck, its making its way towards the front of a long line of submissions. If its been >33h, its likely running right now and your score will arrive once it finishes, scores have continued to work its just incredibly high demand and finite supply.
> 
> Thanks for your patience everyone, we will continue to do what we can.

> **Message 2 by User (2026-10-08)** [Votes: 18]:
> Hi everyone,
> 
> I wanted to give an update on the long submission wait times and "Kaggle Error" failures many of you have been seeing over the past couple of days.
> 
> What Happened
> Due to very high submission volume using L4s, submission jobs have been facing long queue times before actually getting a machine to run. Submissions that waited >15h to start were being marked as “Kaggle Error” even if they eventually did run.
> 
> What We Fixed
> 
> Extended Queue Timeout: We've drastically extended the queue allowance so submissions will no longer be timed out while waiting to run.  
> Scoring Submissions that had Queue Timeouts: We are actively reprocessing all affected submissions from the past few days. If your notebook ran to completion and produced a valid submission file, it is being scored and published to the leaderboard automatically. You should already see scores showing up on the leaderboard now.  
> Queue Wait Times: to even some of the load on the pool, we are implementing a pending submission limit (separate from the 1/day limit). If your team's previous submission is still scoring, you will need to wait until it finishes to submit again.
> 
> What This Means for You
> 
> No action needed: You do not need to resubmit or contact support to recover an affected run; our batch recovery is processing them directly.  
> Monitor this post for updates
> 
> Thanks for your patience while we sort this out, and sorry for the frustration it caused over the last few days.

> **Message 3 by User (2026-10-08)** [Votes: 1]:
> Thanks for your effort. How are we effectively preventing this from happening again, given that we now have an even bigger load, with everyone rushing to submit more and your batch recovery trying to spam it with the previously error ones? 
> 
> We might need to ask Jensen for more L4s in Kaggle

> **Message 4 by User (2026-10-10)** [Votes: 0]:
> Was the problem solved? I still get long wait times.


---

### `[GENERAL_DISCUSSION]` [685142] Last Years 1st Place Solution (21 comments, `Signal: 13.15`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/685142

> **Message 1 by User (2026-03-27)** [Votes: 25]:
> Has anyone tried submitting last year's winning solution?
> 
> https://www.kaggle.com/competitions/arc-prize-2025/writeups/nvarc
> 
> I suspect it would achieve Public LB 27 and Private LB 24! 
> 
> (edit: last year was 4xL4 and this year is 2xT2, so it cannot achieve these scores)
> 
> ========
> 
> UPDATE: The code has been reconfigured for 2xT4 and published here
> 
> UPDATE 2: This competition has upgraded the GPUs to 4xL4, so we can now submit last years solution

> **Message 2 by User (2026-03-27)** [Votes: 6]:
> That solution uses 4xL4 GPUs. We still don't have access to those.
> 
>   NOTE: We are currently exploring options to provide better compute for this competition.

> **Message 3 by User (2026-03-30)** [Votes: 4]:
> UPDATE: The code has been reconfigured for 2xT4 and published here

> **Message 4 by User (2026-03-30)** [Votes: 4]:
> You won't get these scores with 2xT4. We used 4xL4.


---

### `[BUG_ALERT]` [746520] Kaggle Error? (25 comments, `Signal: 12.88`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/746520

> **Message 1 by User (2026-10-07)** [Votes: 19]:
> Did anyone else get a Kaggle Error on their submission yesterday? Mine ran 15 hours and errored out. I also noticed slow downloads, possibly a docker image?

> **Message 2 by User (2026-10-08)** [Votes: 2]:
> @herbison @macruzbar Please create an offical kaggle topic for the "kaggle error"/queued submission issue in both arc2 and arc3 so all users can get the same information and can follow the way to a solution, thanks!

> **Message 3 by User (2026-10-07)** [Votes: 1]:
> @herbison Hi Dustin, could you please look at this failed submission?
> 
> Submission ref: 56890645
> Submitted: 2026-10-06 20:49 UTC
> Result: "Kaggle Error – A system error. Please try resubmitting…", after about 15 hours
> 
> The submission was about one hour after your message about the dataset outage in Notebooks (https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/743927#3533780). Another user reported the same "A system error" on the same day.
> 
> My questions:
> 
> Was this submission affected by the dataset-mount outage? Or can you see a different cause in the rerun logs?
> When does the 12-hour runtime limit start for a rerun: at queue start, container start, or the first notebook cell? My notebook computes its time budget from the first cell, so a long image pull or dataset mount could push the total over the limit.
> This version used "Latest Container Image". Do you recommend the pinned image for reruns, for faster and more reliable starts?
> 
> Thank you!

> **Message 4 by User (2026-10-08)** [Votes: 0]:
> Please see: https://kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/747515


---

### `[GENERAL_DISCUSSION]` [689054] Upgraded Accelerators (19 comments, `Signal: 10.68`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/689054

> **Message 1 by User (2026-09-29)** [Votes: 2]:
> @addisonhoward @macruzbar It looks like the L4 queue is jammed. Can you do something? See https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/743927

> **Message 2 by User (2026-04-07)** [Votes: 21]:
> Hi everyone, 
> we just upgraded the accelerators for ARC-AGI-2. This competition now has access to Kaggle's pool of powerful new L4x4 machines! These machines offer 96GB of GPU memory enabling submissions with much larger models. 
> 
> Head over to the Overview tab to learn the essentials and see this page for more in-depth information on these machines.
> 
> Good luck!
> 
> María

> **Message 3 by User (2026-05-24)** [Votes: 1]:
> Dear ARC Prize Organizers,
> 
> I hope you are doing well. My team and I have many promising ideas and approaches we would like to explore for the ARC Prize 2026 competition, but we are currently limited by a lack of GPU resources and financial means. I noticed that some sponsors may provide additional compute resources for participants, and I previously sent an email about this opportunity but have not yet received a response. Could you please let me know how we can apply or become eligible for these additional resources? Thank you very much for your time and for organizing this inspiring competition.
> 
> Kind regards,

> **Message 4 by User (2026-10-08)** [Votes: 0]:
> Hi @herbison,
> 
> Could you please check my ARC-AGI-2 submissions?
> Both used the same unchanged notebook and ended with “A system error” after extended waiting. The ordinary GPU smoke completed successfully.
> Could you confirm whether they exceeded the independent queue-time limit? If they were affected by the platform issue, could they be rerun, and could you verify their effect on my submission allowance?
> Please advise whether I should wait for that retry or an official rerun.
> 
> Thank you.


---

### `[GENERAL_DISCUSSION]` [709522] Historical leaderboard with runtime information (6 comments, `Signal: 9.91`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/709522

> **Message 1 by User (2026-08-21)** [Votes: 1]:
> But now its hagging off. I didn't make it to a better score yet.

> **Message 2 by User (2026-08-21)** [Votes: 1]:
> AIMO3, Nemotron, now ARC-AGI 2 and 3. At this point, @huikang is a Critical Competition Infrastructure

> **Message 3 by User (2026-06-19)** [Votes: 32]:
> I made the historical leaderboard for ARC Price 2026 - ARC-AGI-2
> 
> https://arc3.huikang.dev/leaderboard/?comp=arc2
> 
> Here is a screenshot.
> 
> This was done for AIMO3 and it was helpful for many people, since I am doing this for ARC-AGI-3, so I am doing this here as well.

> **Message 4 by User (2026-07-22)** [Votes: 1]:
> Great work! Thank you for this. I just have one suggestion. The horizontal scroll bar is not accessible as it is at the bottom of the table and the table expands as we scroll vertically. Is it possible to modify this? May be move the scroll bar to the top and also freeze the header?


---

### `[GENERAL_DISCUSSION]` [689254] ARC Prize 2026 - ARC-AGI-2 - Let's go! (7 comments, `Signal: 7.72`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/689254

> **Message 1 by User (2026-06-03)** [Votes: 0]:
> @gregkamradt 
> Hey Greg Kamradt!
> We respectfully request that the ARC AGI Team consider increasing the daily submission limit beyond one submission per day, similar to ARC AGI 3. A higher limit would help participants iterate faster, validate improvements, and make more meaningful progress throughout the competition.
> 
> Thank you for your consideration.

> **Message 2 by User (2026-04-08)** [Votes: 9]:
> Hi ARC Prize participants!
> 
> We're excited to have you here with us on Kaggle for ARC Prize 2026: ARC-AGI-2 edition. Our #1 goal is to make sure you have the tools, knowledge, and support you need to start solving ARC-AGI.
> 
> Here is a guide to help you get started and ton of high signal resources and documentation to get you up to speed.
> 
> Plug into the community & get competition updates:
> 
> Subscribe to the newsletter
> Join the Discord server
> Follow ARC Prize Twitter
> Subscribe on YouTube
> 
> Greg Kamradt, President, ARC Prize Foundation

> **Message 3 by User (2026-04-08)** [Votes: 1]:
> I find it incredible that there is neither a reference to our winning solution code nor our article describing it in your resource page at https://arcprize.org/resources
> 
> How can this be possible?

> **Message 4 by User (2026-08-02)** [Votes: 0]:
> Thank you very much for including me in your team. I will learn a lot and help you a lot, God willing.


---

### `[GENERAL_DISCUSSION]` [684441] How to get started + Competition's Official Discord (1 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/684441

> **Message 1 by User (2026-04-26)** [Votes: 5]:
> I don't see an arc agi2 competition channel in kaggle discord. There is any arc agi3 channel.

> **Message 2 by User (2026-03-24)** [Votes: 4]:
> Information for newbies
> New to machine learning and data science? No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!
> 
> New to Kaggle? Take a look at a few videos to learn a bit more about site etiquette, Kaggle lingo, and how to enter a competition using Kaggle Notebooks. Publish and share your models on Kaggle Models!
> 
> Looking for a team? Express your interest in joining a team through our Team Up feature.
> 
> Remember: Kaggle is for everyone. Whether you're teaming up or sharing tips in the competition forum, we expect everyone to follow our Kaggle community guidelines.
> 
> Competition's Official Discord
> In addition to this competition forum, you can continue the discussion in our official Kaggle Discord Server here:
> 
> discord.gg/kaggle
> The Discord is a great place to ask getting started questions, chat about the nuances of this competition, and connect with potential team mates. Learn more about Discord at our announcement here. Here are a few things to keep in mind though:
> 
> 1. Discord Competition Channels are 'Public' - Don't Share Private Information
> 
> Discord channels for specific competitions are considered 'public' spaces where you are allowed to talk about competition details. Please remember that private sharing of competition code or data outside of your team is, as always, not permitted. Code sharing must always be done publicly through the Kaggle forums/notebooks.
> 
> 2. Discord Competition Channels are Not Monitored by Staff - Keep Important Information on the Kaggle Forums
> 
> Kaggle Staff and Hosts running competitions will not monitor Discord or be available to answer questions in Discord. This is intended to be a more casual space to discuss competitions and help each other. Please keep important questions, insights, writeups, and other valuable conversation on the Kaggle forums. 
> 
> Happy modeling!


---

## Competition: `arc-prize-2026-arc-agi-3`

### `[BUG_ALERT]` [705405] Correcting an Error in Competition Submission Limits (12 comments, `Signal: 12.62`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/705405

> **Message 1 by User (2026-06-09)** [Votes: 3]:
> Hi everyone,
> 
> We want to sincerely apologize for a recent oversight regarding the daily submission limits for this competition, and share how we are addressing it.
> 
> What happened:
> Our intended setting for this competition had been one submission per day. However, on May 27, a miscommunication over a mismatch between our settings and the written rules caused us to mistakenly change the competition settings to allow 5 submissions per day.
> 
> The Impact:
> During this 13-day window, the system allowed up to 5 submissions per day. Understandably, several teams utilized these available submissions to test and improve their models. We want to be entirely clear that we do not view this as cheating or breaking the rules; teams were simply operating within the limits our system presented to them.
> 
> Going forward:
> To get back to the intended course, we are taking the following steps:
> 
> Restoring the Cap: Yesterday, June 8, we restored the submission limit back to one submission per day.
> Invalidating Surplus Submissions: We are working now to invalidate any additional submissions teams made after their first successful submission for each day during that period. Because there are still 5 months remaining in the competition, this brief window of elevated submission allowance does not confer a material unfair advantage to teams, and resetting the counts now ensures all teams compete on equal footing for the remainder of the competition.
> 
> We understand that errors such as this are frustrating and disruptive. We very much appreciate your patience and continued participation in the Kaggle community.
> 
> Sincerely, 
> 
> María and the Kaggle team.

> **Message 2 by User (2026-06-11)** [Votes: 2]:
> [Request] Is it possible to make submissions with a score of 0 not count toward the submission limit? Internal errors provide no logs at all, so it is difficult to debug or understand what went wrong.

> **Message 3 by User (2026-06-10)** [Votes: 0]:
> This is completely unfair. Everyone had access to the 5 submissions per day and could use them; there was no injustice! You just made me lose 100 places… 
> 
> I don't understand!
> 
> Some candidates obtained scores by directly using the .py code from the games. This was addressed by implementing obfuscation, but their scores were not invalidated.
> 
> I don't understand how, on the one hand, submissions obtained dishonestly are still valid, and on the other hand, you arbitrarily decide to delete valid submissions, since everyone could make the 5 submissions per day.
> 
> The error lies with the platform, not with dishonest use by the candidates.
> 
> This is arbitrary, unfair, and I'm not sure it's valid from a legal standpoint.
> 
> The fairest course of action would be to publicly state that this is a Kaggle bug, not to cancel submissions made during the period of authorization of 5 submissions per day, and to continue with one submission per day.
> 
> @macruzbar 
> 
> @gregkamradt

> **Message 4 by User (2026-06-23)** [Votes: -1]:
> Hi! I'm trying to reproduce the StochasticGoose ARC-AGI-3 notebook.
> 
> I started from the published notebook and submitted it without intentionally changing the algorithm. However, my submissions are scoring around 0.03–0.11 public score, while I understood the notebook was achieving roughly 0.25.
> 
> Could you clarify:
> 
> Is the published notebook identical to the version that achieved 0.25?
> Were there additional files, weights, patches, or dependencies used that are not included?
> Has the ARC-AGI-3 environment changed since that score was obtained?
> 
> Any guidance would be greatly appreciated. Thanks!


---

### `[METRIC_NUANCE]` [697720] Update on accelerators (6 comments, `Signal: 9.71`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/697720

> **Message 1 by User (2026-07-21)** [Votes: 2]:
> So this benchmark is supposed to be an evaluation of whether frontier models can hit AGI performance, but the only HW available for this task can at best run quantized models with <100B parameters.

> **Message 2 by User (2026-05-07)** [Votes: 10]:
> Hi everyone, 
> a couple of days ago, Kaggle faced a stockout of H100 processors. If we are able to reallocate these processors in the coming months, we will. 
> 
> In the meantime, we have changed to RTX 6000 Pro. Please read the description I updated on the Overview tab. If you have any questions, please let us know. 
> 
> Best, 
> 
> María

> **Message 3 by User (2026-05-07)** [Votes: 2]:
> The machine type indicated in the Overview tab is "g2-standard-48" that has four NVIDIA L4 GPUs. Actually, "g4-standard-48"?

> **Message 4 by User (2026-07-21)** [Votes: 0]:
> Hey María,
> 
> There seems to be an issue with the RTX 600 Pro instances.
> Currently, I do not have access to them, but can select TPU instead.
> 
> Any official update on usable accelerators?
> 
> Thanks!


---

### `[BUG_ALERT]` [697944] Update on Code Requirements (7 comments, `Signal: 8.09`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/697944

> **Message 1 by User (2026-09-08)** [Votes: 2]:
> @macruzbar Dear Hosts,
> Thank you for the public competition.
> However for the past week th queue for the running any notebook using the RTX 6000 is taking painfully long time in queues. Since or is a quit expensive GPU most of us cannot afford to run all experiments on rented RTX 6000. Can we please request to increase the quota of those GPUs.
> Else the only member who have a lot of compute (from big companies or startups or labs) can properly compete, which will reduce the spirit of open competition.

> **Message 2 by User (2026-05-07)** [Votes: 11]:
> Hi all, 
> Given the change in accelerators from H100s to RTX 6000, and because we want to make sure your models still have ample resource headroom to run successfully on the new hardware, we have adjusted the code requirements and extended the maximum notebook runtime. It has increased from 6 hours to 9 hours. I noted this on the Overview tab, in the section Code requirements. 
> 
> Thank you everyone for your patience as we worked through this challenge. 
> 
> Happy modeling, and good luck!
> 
> María

> **Message 3 by User (2026-05-09)** [Votes: 3]:
> Hi, H100 still appears as a choice when I create a new notebook. Is that expected?

> **Message 4 by User (2026-05-08)** [Votes: 2]:
> [hypothetical question] what would happen if i select a notebook which was submitted using H100 for my final submission at the end of the deadline? will it automatically reverted to RTX6000 or will i get scoring error??


---

### `[GENERAL_DISCUSSION]` [695158] Upgraded accelerators (2 comments, `Signal: 7.83`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/695158

> **Message 1 by User (2026-04-28)** [Votes: 21]:
> Hi everyone, 
> we just upgraded the accelerators for ARC-AGI-3. This competition now has access to Kaggle's pool of powerful new H100 accelerators! 
> 
> Head over to the Overview tab to learn the essentials and see this page for more in-depth information on these machines.
> 
> Good luck!
> 
> María

> **Message 2 by User (2026-05-28)** [Votes: 0]:
> This is very nice thanks kaggle team


---

### `[GENERAL_DISCUSSION]` [713634] Clarification on deadline for milestone prizes (5 comments, `Signal: 6.58`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/713634

> **Message 1 by User (2026-06-24)** [Votes: 6]:
> Hi everyone, 
> if you are considering open-sourcing your solution for the Milestone Prizes, please note that the deadline to do so is 11:59pm UTC on the corresponding day. For ARC-AGI-3, there are 2 milestone prizes, the first one is next week on June 30th, and the second one is on September 30th. I have updated the Timeline and the Prizes sections in the Overview tab to reflect this. 
> 
> Good luck!
> 
> María

> **Message 2 by User (2026-06-24)** [Votes: 4]:
> plz update the links. they are invalid

> **Message 3 by User (2026-08-10)** [Votes: 0]:
> The milestone prize structure is interesting — it incentivizes early participation. The Progress Prize consists of guaranteed Final Leaderboard Prizes plus conditional Milestone Prizes. This means even if you don't win the overall competition, being on the leaderboard early can earn you a share of the milestone pool. Worth submitting early and often (1 submission per day limit).

> **Message 4 by User (2026-07-28)** [Votes: 0]:
> Hey, so u have to open source the solution the same day as the deadline; for example 30 of september; or the day after


---

### `[GENERAL_DISCUSSION]` [687384] Welcome to ARC Prize 2026 - ARC-AGI-3 Edition (0 comments, `Signal: 4.16`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/687384

> **Message 1 by User (2026-04-02)** [Votes: 7]:
> Hey team!
> 
> We are super excited you're here with us on Kaggle to learn more and participate in ARC Prize 2026: ARC-AGI-3 edition. Our #1 goal is to make sure you have the tools, knowledge, and support you need to start solving ARC-AGI.
> 
> Here is a guide to help you get started. In addition to the Kaggle templates, track our community leaderboard and documentation to get you up to speed.
> 
> Plug into the community & get competition updates:
> 
> Subscribe to the newsletter
> Join the Discord server
> Follow ARC Prize Twitter
> Subscribe on YouTube
> 
> Have questions? Feel free to start a discussion topic on this competition, reach out to us on Twitter, Discord, or team@arcprize.org.
> 
> Greg Kamradt, President, ARC Prize Foundation


---

### `[SOTA_RECIPE]` [684625] How to get started + Competition's Official Discord (9 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/684625

> **Message 1 by User (2026-07-06)** [Votes: 2]:
> Hello!
> Newbie here…looking forward to learn and implement models

> **Message 2 by User (2026-03-25)** [Votes: 8]:
> Information for newbies
> New to machine learning and data science? No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!
> 
> New to Kaggle? Take a look at a few videos to learn a bit more about site etiquette, Kaggle lingo, and how to enter a competition using Kaggle Notebooks. Publish and share your models on Kaggle Models!
> 
> Looking for a team? Express your interest in joining a team through our Team Up feature.
> 
> Remember: Kaggle is for everyone. Whether you're teaming up or sharing tips in the competition forum, we expect everyone to follow our Kaggle community guidelines.
> 
> Competition's Official Discord
> In addition to this competition forum, you can continue the discussion in our official Kaggle Discord Server here:
> 
> discord.gg/kaggle
> The Discord is a great place to ask getting started questions, chat about the nuances of this competition, and connect with potential team mates. Learn more about Discord at our announcement here. Here are a few things to keep in mind though:
> 
> 1. Discord Competition Channels are 'Public' - Don't Share Private Information
> 
> Discord channels for specific competitions are considered 'public' spaces where you are allowed to talk about competition details. Please remember that private sharing of competition code or data outside of your team is, as always, not permitted. Code sharing must always be done publicly through the Kaggle forums/notebooks.
> 
> 2. Discord Competition Channels are Not Monitored by Staff - Keep Important Information on the Kaggle Forums
> 
> Kaggle Staff and Hosts running competitions will not monitor Discord or be available to answer questions in Discord. This is intended to be a more casual space to discuss competitions and help each other. Please keep important questions, insights, writeups, and other valuable conversation on the Kaggle forums. 
> 
> Happy modeling!

> **Message 3 by User (2026-04-17)** [Votes: 1]:
> I have noticed inconsistent maximum cap of per-level efficiency score:
> 
> 1.15x mentioned at https://docs.arcprize.org/methodology
> 1.0x  mentioned at https://arxiv.org/pdf/2603.24621
> 1.0x  mentioned under "Scoring Method" at https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data
> 
> @gregkamradt  Could you please clarify if it is 1.15 (as per methodology) or 1.0 (as per arXiv paper)

> **Message 4 by User (2026-08-10)** [Votes: 0]:
> For anyone just getting started: the key difference from ARC-AGI-2 is that AGI-3 tasks involve fluid intelligence — they require reasoning across multiple steps. My baseline approach: use the training data to identify common transformation patterns (tiling, symmetry, color mapping) and try to match each test input to the most similar training example. The identity transform (copying input as output) is a reasonable fallback.


---

## Competition: `arc-prize-2026-paper-track`

### `[RULES_COMPLIANCE]` [710600] Regressive Plasticity Schedule: A Two-Stage Post-Training Schedule for ARC Program Synthesis (0 comments, `Signal: 7.39`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/710600

> **Message 1 by User (2026-06-20)** [Votes: 1]:
> Paper: https://github.com/iamjasonfeng/RPS-Paper
> 
> This paper has been submitted to ARC Prize 2026 Paper Track and ARC AGI Community Leaderboard.
> 
> Abstract
> 
> This paper presents Regressive Plasticity Schedule (RPS), a two-stage post-training schedule inspired by developmental plasticity. RPS combines two familiar ideas, curriculum learning and learning-rate reduction, in a specific way: the model is first trained on easier data at a higher learning rate, then trained on harder data at a substantially lower learning rate. This differs from ordinary learning-rate decay because the main intervention is not merely reducing the optimizer step size over time within one training stage; instead, RPS couples a discrete stage-level learning-rate drop to a curriculum boundary between easier and harder data. The broader motivation for RPS is to improve general reasoning: program synthesis is an important testbed here, but the more important question is whether staged plasticity can help models preserve foundational reasoning behaviors while adapting to harder domains. I tested RPS on Qwen3-8B using Alibaba Model Studio managed DPO fine-tuning with LoRA. The control condition, Equal Plasticity Schedule (EPS), used the same model, same two-stage data structure, same within-stage cosine scheduler, and same Stage 1 checkpoint, but did not reduce the Stage 2 learning rate. On ARC-AGI-1 public evaluation, RPS improved exact test-output accuracy from 10/419 to 17/419, which provides evidence of improved ARC-style general reasoning because these tasks require inferring and applying latent transformation rules from few examples. On ARC-AGI-2 public evaluation, neither RPS nor EPS solved any test outputs, but RPS substantially improved program-synthesis reliability: 234/240 attempted programs executed without error for RPS, compared with 188/240 for EPS. The result does not show that RPS solves ARC-AGI-2, but it suggests that a curriculum-coupled plasticity reduction can improve ARC-style reasoning behavior and make a model more stable at producing usable reasoning artifacts. If this pattern generalizes beyond ARC, RPS could have large potential as a simple post-training schedule for improving broader reasoning behavior.


---

### `[GENERAL_DISCUSSION]` [689255] ARC Prize 2026 - Paper Track (3 comments, `Signal: 4.85`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/689255

> **Message 1 by User (2026-04-08)** [Votes: 3]:
> Hi Authors!
> 
> We're excited to have you here with us on Kaggle for ARC Prize 2026: Paper Track. This has been one of the most rewarding tracks in previous competitions
> 
> Check out the paper winners from previous years: 2025, 2024
> 
> Plug into the community & get competition updates:
> 
> Subscribe to the newsletter
> Join the Discord server
> Follow ARC Prize Twitter
> Subscribe on YouTube
> 
> Greg Kamradt, President, ARC Prize Foundation

> **Message 2 by User (2026-08-15)** [Votes: 0]:
> HII i am new here


---

### `[METRIC_NUANCE]` [717842] Falsification Engine SEN-EF (0 comments, `Signal: 3.39`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/717842

> **Message 1 by User (2026-07-02)** [Votes: 1]:
> Markdown
> 
> Prêmio ARC 2026 — Análise Técnica: Motor de Falsificação SEN-EF
> 1. Filosofia Central: A Arquitetura Popperiana
> Esta arquitetura rejeita abordagens indutivas ao Corpus de Abstração e Raciocínio (ARC). Em vez de assumir que uma IA pode "aprender" um padrão por meio de mera repetição ou otimização estatística bruta, esse sistema opera estritamente como um Motor de Refutação fundamentado na Epistemologia de Karl Popper (Teoria dos Três Mundos).
> 
> Mundo 1 (Realidade Empírica / Dados Brutos): As matrizes da grade de entrada (0-9). Obtido por meio de dados brutos de sensores e observação estrutural.
> Mundo 2 (Processamento Conceitual): A geração de conjecturas ousadas e hipóteses algorítmicas via o framework SEN-EF (Narrative Engineering System — Fiction Engineering).
> Mundo 3 (Validação Axiomática): O filtro formal e rigoroso do escudo REN-EF, onde a eliminação de erros opera sob máxima fricção lógica.
> 
> 2. Metodologia: Eliminação de Atrito Estrutural e Erro
> Diferentemente das arquiteturas neurais padrão que minimizam uma função de perda contínua, o Falsification Engine SEN-EF aplica um filtro binário absoluto a cada candidato a programa gerado.
> 
> Fase de Conjectura (SEN-EF): O sistema gera hipóteses explícitas e simbólicas de transformação (regras para cores, geometria, simetria e escala).
> Fase de Refutação (REN-EF): Cada hipótese é testada agressivamente contra os pares de treinamento de uma tarefa ARC. Se uma conjectura falhar em um único pixel, ela é instantaneamente refutada e eliminada.
> Corroboração: Apenas hipóteses que sobrevivem à falsificação absoluta são avançadas para a grade final de avaliação.
> 
> 3. Implementação Técnica e Reprodutibilidade
> A execução desse pipeline de lógica simbólica é otimizada para velocidade, clareza e resiliência estrutural. O ambiente completo de processamento determinístico rodou perfeitamente na plataforma, gerando saídas limpas sob restrições computacionais rigorosas.
> 
> Status da Execução: Execução concluída com sucesso em 28,0 segundos.
> Auditabilidade: Totalmente em conformidade com os princípios de verificação distribuída (Consistência, Coerência, Rastreabilidade, Explicabilidade e Auditabilidade).
> 
> 4. Verificação e Link do Caderno
> O repositório completo, os logs de verificação e o ambiente de execução da fonte para esse modelo são totalmente públicos e acessíveis para revisão por pares.
> 
> Repositório Público de Modelos/Cadernos: https://www.kaggle.com/models/itaframyahoocom/falsificacao-motor-sen-cf
> 
> Autor: Estrutura Ita Fram
> 
> Framework: Infraestrutura Central SEN-EF / REN-EF<img src="https://www.googleapis.com/download/storage/v1/b/kaggle-forum-message-attachments/o/inbox%2F35414425%2F1e858bf0c18acb846f5435cfef0ef910%2F764a85e9-3c7d-4e3a-869a-b1833afb4649.png?generation=1783004216450693&alt=media" alt="! (opens in a new tab)">" />


---

### `[GENERAL_DISCUSSION]` [696513] Bibliography? 1500-word limit? (1 comments, `Signal: 2.43`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/696513

> **Message 1 by User (2026-08-15)** [Votes: 1]:
> Same question as @benedictehelfer , and one more on top of it: does the 1,500-word limit also apply if
> you upload a PDF through the Public Project Link instead of writing it in the Kaggle
> Writeup editor? The Submission Requirements page mentions the PDF option but doesn't say
> whether the word limit carries over to it.
> 
> Asking because 1,500 words across all six required sections works out to about 250 words
> each, which is a very different paper than if the PDF route is unlimited. Would rather
> know before writing it than after.

> **Message 2 by User (2026-05-02)** [Votes: 1]:
> Can a bibliography be included? If so, does the bibliography fit within the 1500-word limit?


---

### `[RULES_COMPLIANCE]` [694752] Paper Track: one unified writeup for ARC-AGI-2 and ARC-AGI-3? (1 comments, `Signal: 2.43`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/694752

> **Message 1 by User (2026-04-27)** [Votes: 1]:
> A unified paper is allowed - it will be judged according to the rubric as normal. However, if you think your paper could more clearly communicate it's finding and impact using just one ARC-AGI version that is fine too.
> 
> Yes, please use 1 notebook as your primary one when submitting the paper but also link to any other assets you'd like to as well

> **Message 2 by User (2026-04-26)** [Votes: 1]:
> Hello, I am planning to participate in both ARC-AGI-2 and ARC-AGI-3.
> 
> For the Paper Track, if I make one submission to ARC-AGI-2 and one submission to ARC-AGI-3, should I submit:
> 
> one unified Paper Track writeup covering the shared conceptual/methodological approach behind both submissions, or
> two separate Paper Track writeups, one linked to the ARC-AGI-2 submission and one linked to the ARC-AGI-3 submission?
> 
> Also, if a unified writeup is allowed, should one submission ID/notebook still be selected as the primary linked submission for eligibility purposes?


---

### `[GENERAL_DISCUSSION]` [692867] How to start with? (2 comments, `Signal: 1.65`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/692867

> **Message 1 by User (2026-04-19)** [Votes: 1]:
> Here are more competition resources: https://arcprize.org/competitions/2026
> 
> This is the paper track which builds off the submissions in the ARC Prize 2026: ARC-AGI-3 and ARC-AGI-2 competitions

> **Message 2 by User (2026-04-18)** [Votes: 0]:
> This is my first time to this competition of ARC, Can anyone tell how to start with?


---

### `[GENERAL_DISCUSSION]` [698299] can I just link my codes through GitHub? (2 comments, `Signal: 1.65`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/698299

> **Message 1 by User (2026-05-09)** [Votes: 0]:
> I honestly do not know how to make use of the notebook on Kaggle, however I have multiple pdf files of my work and progress already uploaded to my project that explains my theory, methodology, and tests. I also simply linked my GitHub repository to my project, is that allowed? I'd rather not waste my time trying to understand how to use something new when I can just use what I am already using if it works.

> **Message 2 by User (2026-05-09)** [Votes: 0]:
> Too many notebooks of same project is bad on kaggle. Use claude to merge all of them with proper markdowns and tell to create a one notebook for uploading on kaggle. Then download and upload it on kaggle. Hope this helps !


---

### `[GENERAL_DISCUSSION]` [735361] Does editing a Writeup reset its submission time for the tie-break? (0 comments, `Signal: 1.39`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/735361

> **Message 1 by User (2026-08-15)** [Votes: 1]:
> The Evaluation page says that in the event of a tie, the paper that was entered first to
> the competition wins. We're also allowed multiple submissions per day.
> 
> So can a Writeup be edited or resubmitted after you've submitted it, and if it can, does
> that reset the timestamp used for the tie-break? Or does the original submission time
> still stand?
> 
> It makes a fairly big difference for planning. Either you submit a complete version early
> and keep improving it, or you hold one final version back until the end. Those are
> opposite strategies and right now there's no way to tell which one is correct.
> 
> Unrelated but while I'm here: the Timeline page lists the paper deadline as November 9,
> but arcprize.org says "November 8, 2026 - Papers due". Which one is binding?


---

### `[GENERAL_DISCUSSION]` [684624] How to get started + Competition's Official Discord (0 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/684624

> **Message 1 by User (2026-03-25)** [Votes: 2]:
> Information for newbies
> New to machine learning and data science? No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!
> 
> New to Kaggle? Take a look at a few videos to learn a bit more about site etiquette, Kaggle lingo, and how to enter a competition using Kaggle Notebooks. Publish and share your models on Kaggle Models!
> 
> Looking for a team? Express your interest in joining a team through our Team Up feature.
> 
> Remember: Kaggle is for everyone. Whether you're teaming up or sharing tips in the competition forum, we expect everyone to follow our Kaggle community guidelines.
> 
> Competition's Official Discord
> In addition to this competition forum, you can continue the discussion in our official Kaggle Discord Server here:
> 
> discord.gg/kaggle
> The Discord is a great place to ask getting started questions, chat about the nuances of this competition, and connect with potential team mates. Learn more about Discord at our announcement here. Here are a few things to keep in mind though:
> 
> 1. Discord Competition Channels are 'Public' - Don't Share Private Information
> 
> Discord channels for specific competitions are considered 'public' spaces where you are allowed to talk about competition details. Please remember that private sharing of competition code or data outside of your team is, as always, not permitted. Code sharing must always be done publicly through the Kaggle forums/notebooks.
> 
> 2. Discord Competition Channels are Not Monitored by Staff - Keep Important Information on the Kaggle Forums
> 
> Kaggle Staff and Hosts running competitions will not monitor Discord or be available to answer questions in Discord. This is intended to be a more casual space to discuss competitions and help each other. Please keep important questions, insights, writeups, and other valuable conversation on the Kaggle forums. 
> 
> Happy modeling!


---

### `[GENERAL_DISCUSSION]` [694095] what is the ARC Prize project (1 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/arc-prize-2026-paper-track/discussion/694095

> **Message 1 by User (2026-04-23)** [Votes: 1]:
> Check out more information here
> 
> https://arcprize.org/
> 
> and here https://arcprize.org/competitions/2026

> **Message 2 by User (2026-04-23)** [Votes: 0]:
> I'm a beginner not Understand this work what is working and solving this is but what is I'm working for this competition


---

## Competition: `rsna-knee-abnormality-detection`

### `[BUG_ALERT]` [746792] Reaching 0.949 with one CoAtNet: labels, native crops, and anatomical mirroring (48 comments, `Signal: 32.83`)
**URL**: https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/746792

> **Message 1 by User (2026-10-07)** [Votes: 32]:
> Our best single-model submission scores 0.949 public AUC. We are sharing the accuracy recipe, our smaller 0.945 model for the efficiency track, and several changes that did not help.
> 
> The accuracy result uses one CoAtNet checkpoint trained at 384 pixels. At inference we take a native 320-pixel center crop and average probabilities from the original view and an anatomical left/right mirror. It is one learned model evaluated twice. The checkpoint itself averages three selected epochs from one training run, called SWA in our code.
> 
> The score history
> These are ordinary, full twelve-finding public leaderboard scores. Rows describe successive pipeline configurations; their differences are not all isolated causal effects.
> 
> Configuration
> Public AUC
> Change
> 
> Our all-data CoAtNet, 80 slices and 78 windows
> 0.939
> Starting point
> 
> 96 slices, native 384-pixel cache, 94 windows
> 0.940
> +0.001
> 
> Blend + JEV labels
> 0.942
> +0.002
> 
> Smaller 224-pixel crop model with epoch weight averaging
> 0.940
> −0.002
> 
> Add external OAI knee examples with masked labels
> 0.945
> +0.005
> 
> 384-pixel, full-field external-data recipe
> 0.948
> +0.003
> 
> Same weights, native 320-pixel inference crop
> 0.948
> 0.000
> 
> Same weights and crop, anatomical mirror probability averaging
> 0.949
> +0.001
> 
> The first density change also changed cached resolution and window count. Adding external examples increased training rows and optimizer updates, and the serving precision path changed. The 224-to-384 step also changed training crop geometry and the pretrained architecture variant. Those rows should be read as recipe comparisons rather than additive gains from individual factors.
> 
> Training and labels
> The model is a timm CoAtNet backbone with finding-specific multiple-instance attention pooling. We trained on 4,349 report-labeled competition studies; the 58 expert-labeled studies were excluded from training but reused for selection. The weak targets combine our report-derived soft labels with the public label sources credited below. In the external-data recipe, 2,399 OAI knees brought the training set to 6,748 rows. PF OA, Lateral OA and Synovitis received external supervision; unavailable finding cells were masked rather than treated as negatives. Positive class weights remained based on RSNA labels.
> 
> Both released candidates use seed 42, 16 epochs, backbone learning rate 4.01e−5, head learning rate 0.00195 and weight decay 0.0588. Training used 12 windows per study, batch size 1 and gradient accumulation over 16 studies; gold evaluation used 24 windows. The smaller model averages epochs 15, 13 and 12; the accuracy model averages epochs 14, 11 and 12. These selected averages are called SWA in our code. Adding external examples increased the scheduled optimizer updates from 4,336 to 6,736, so that comparison is not compute-matched.
> 
> The final inference recipe
> Each study has 96 preprocessed slices across five sagittal, coronal, and axial series slots. We evaluate 94 three-slice windows, process them in chunks of 16, and use finding-specific attention over the complete window bag.
> 
> For the accuracy model, native 384×384 windows are cropped to pixels [32:352, 32:352]. No resize is applied. Sagittal left/right mirroring reverses the three slice channels; coronal and axial mirroring flips image width. We use the center slice to determine the window plane and apply the transform before normalization. We average the two sigmoid probability vectors equally. The existing final per-finding percentile ranking preserves their ordering.
> 
> The smaller model uses a 307-pixel center crop resized to 224 pixels, the same 94-window policy, FP16 autocast, and one view. It scores 0.945. Recorded submit-to-score turnaround was about 7.2 minutes for that entry and 26.1 minutes for the mirrored accuracy entry. These include queueing and orchestration; they are not official inference runtimes or efficiency ranks.
> 
> What did not help
> 
> Tested change
> Public AUC, reference → result
> 
> Older model: 94 windows reduced to 24
> 0.940 → 0.934
> 
> Older model: width-flip TTA across every imaging plane
> 0.940 → 0.939
> 
> Current weights: native crop reduced from 320 to 304 pixels
> 0.948 → 0.947
> 
> Current weights: native crop reduced from 320 to 288 pixels
> 0.948 → 0.946
> 
> Epoch 14 instead of averaged weights, same 320-pixel inference
> 0.948 → 0.947
> 
> Fresh training with corrected batch-normalization checkpoint replay
> 0.948 → 0.944
> 
> Fresh native 320-pixel crop training, anatomical mirror inference
> 0.949 → 0.946
> 
> The all-plane width flip is different from anatomical mirroring, and it was tested on an older checkpoint. Its failure does not establish a controlled comparison between the mirror implementations. The new crop-trained model also failed to replace the incumbent despite encouraging gold diagnostics.
> 
> Our 58 labeled studies were reused for checkpoint selection and development. They are useful diagnostics, not independent cross-validation. For example, epoch 14 improved gold AUC while losing on the public board. Rounded public-score differences, especially +0.001, do not establish statistical significance or a private-test gain.
> 
> Credits and release references
> Thanks to dreaddevelopment for the public Raptor CoAtNet/MIL recipe and baseline weights. That public checkpoint scored 0.924 in our baseline read; it is context, rather than a controlled starting point for the table. Our selected checkpoints were retrained. The public weak-label contributions include stevenleehans, pilkwang, and riadmohamed42's JEV labels and verification. We thank RSNA and the competition data contributors.
> 
> Reproducibility notebooks: accuracy, 0.949 and efficiency, 0.945. The selected learned weights are a separate minimal dependency. Both notebooks preserve the exact scored scientific inference source and checkpoint hashes, include hardware/environment requirements, and are saved statically without running inference. No OAI images, identifiers, records, raw reports, subject-level labels or predictions are distributed.
> 
> Both models used the same 2,399 baseline OAI knees; the unsuccessful 12-month arm is excluded from these release models. The public Study describes aggregate methods/results while its exact-input linkage manifest remains restricted to qualified researchers.
> 
> Data and/or research tools used in the preparation of this manuscript were obtained and analyzed from the controlled access datasets distributed from the Osteoarthritis Initiative (OAI), a data repository housed within the NIMH Data Archive (NDA). OAI is a collaborative informatics system created by the National Institute of Mental Health and the National Institute of Arthritis, Musculoskeletal and Skin Diseases (NIAMS) to provide a worldwide resource to quicken the pace of biomarker identification, scientific investigation and OA drug development. Dataset identifier(s): 10.15154/0hcg-f676.
> 
> Shared NDA Study · DOI: 10.15154/0hcg-f676. Official acknowledgement source: NDA manuscript preparation.
> 
> What worked for your models, and what looked promising locally but failed on the leaderboard? Please share useful negative results as well as improvements—especially experiences with weak labels, crop geometry, and plane-aware augmentation.

> **Message 2 by User (2026-10-09)** [Votes: 2]:
> Thanks for the detailed write-up and for releasing the weights and notebooks. The anatomical mirroring explanation and the “what did not help” table were especially useful.

> **Message 3 by User (2026-10-07)** [Votes: 6]:
> Be careful - OAI may not be an allowed external data source. I’d read the host comments about dataset accessibility and then OAI’s own rules before risking using it in model training.

> **Message 4 by User (2026-10-08)** [Votes: 1]:
> Haven't seen such detailed and useful work in a long time.


---

### `[METRIC_NUANCE]` [743416] Please clarify which external knee MRI datasets are allowed (35 comments, `Signal: 20.42`)
**URL**: https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/743416

> **Message 1 by User (2026-10-08)** [Votes: 12]:
> Hope this reply from NDA regarding intended accessibility of OAI dataset helps

> **Message 2 by User (2026-10-08)** [Votes: 4]:
> @javaduke95 Following your Aug 27 guidance (straightforward registration or click-through data-use agreements are generally acceptable; institution-specific approvals are not), could you give a yes/no on two specific points before final selections on Oct 22?
> 
> OAI through the NIMH Data Archive (login.gov account + click-through data-use terms): is it allowed as external training data? Some participants report that NIH country restrictions block access from their location (e.g. China), which seems relevant to "reasonably accessible to all".
> Publicly released checkpoints trained partly on OAI (for example the checkpoint behind the public 0.949 notebook, shared under Apache 2.0): may other teams use them in their submissions?
> 
> Many teams are now building on public notebooks that use such a checkpoint, so a clear answer would keep the leaderboard fair for everyone. Thank you!

> **Message 3 by User (2026-10-07)** [Votes: 8]:
> I would like to follow up on this question, as the status of several commonly used knee MRI datasets is still unclear.
> 
> Resource
> Host status
> Access / licensing issue
> 
> KneeCoT
> Prohibited (host ruling)
> Download is technically easy, but the dataset card requires a formal ethical-use agreement with the affiliated hospital
> 
> Stanford MRNet
> Unclear
> Stanford AIMI / Redivis access; subject to research-use terms and dataset-specific access requirements
> 
> Stanford SKM-TEA
> Unclear
> Stanford AIMI / Redivis access; registration and dataset-specific access requirements
> 
> NYU fastMRI / fastMRI+
> Unclear
> Application required, including institutional affiliation and proposed use; Data Sharing Agreement
> 
> OAI
> Unclear
> NDA registration / controlled-access process; not simply an unrestricted public download
> 
> KneeMRI
> Unclear
> Public download, but CC BY-NC-ND 4.0; unclear whether training/releasing model weights is compatible with the NoDerivatives clause
> 
> KneeXNet-2.5D
> Unclear
> Publicly released OAI-derived annotations/models; repository says research/educational use, but no explicit repository license identified
> 
> Given that KneeCoT is prohibited because of its institutional agreement requirement, could the hosts clarify whether datasets requiring comparable or more substantial access procedures are also prohibited?
> 
> At minimum, could the KneeCoT prohibition be pinned? Although the dataset card explicitly requires a formal ethical-use agreement with the affiliated hospital, the files themselves are relatively easy to access, and this requirement may easily be overlooked in practice. Given the dataset’s large scale and its inclusion of knee MRI examinations, diagnostic reports, labels, VQA data, and reasoning annotations that closely overlap with this competition’s tasks, its use could potentially lead to substantial score gains. A pinned notice would help prevent inadvertent use and ensure that all teams are operating under the same rules.
> 
> @javaduke95

> **Message 4 by User (2026-10-08)** [Votes: 0]:
> I find the calls for a strict external-data ban in the name of “fairness” pretty LAUGHABLE 😀. How exactly is this supposed to be enforced, and what level playing field are we pretending exists?
> 
> We can use LLMs from Google, OpenAI, or Anthropic to extract labels from radiology reports or help annotate knee MRIs. We don’t know their complete pretraining and post-training datasets. I’m not claiming they were trained on any particular knee MRI dataset, but if these teachers are allowed, how do we establish that their labels contain no benefit from external data? Where exactly is the boundary?
> 
> In my experience, datasets such as fastMRI, fastMRI+, OAI, and MRNet are readily accessible because:
> 
> You don't need an academic institution email
> You don't have to sign any agreement and wait for human approval
> 
> How would organizers verify that a winning model never used them? Rerunning an inference notebook verifies its predictions, not its training history. Independently reproducing the full training pipeline requires substantial time and compute that most participants cannot spare.
> 
> And if the argument is equal opportunity, what about participants working with two T4 GPUs and Kaggle’s limited weekly quota while others train on clusters of H200s/ B200s/ B300s ? An external-data ban leaves that disparity intact. If equal resources are the principle, apply it to compute too.

> **Message 5 by User (2026-09-26)** [Votes: 91]:
> Thank you to the hosts for organizing this challenge and for taking the time to answer questions throughout the competition. I appreciate that assessing third-party datasets individually is difficult, especially when their access requirements and licenses differ.
> 
> Questions about external knee MRI data are spread across several threads. Without a clear answer for commonly used datasets, teams may train under different assumptions about what is permitted, which makes it difficult to ensure a level playing field.
> 
> I have read the original question, the registration-gated dataset question, and the institutional-agreement follow-up. There are also separate questions about pretrained weights and research-use agreements.
> 
> The host has explicitly ruled that KneeCoT is not allowed because its formal institutional agreement may create unequal access. The host has also explained that non-commercial terms alone do not exclude a dataset, while straightforward registration and substantial institutional approval may be treated differently. It remains unclear to me how these principles apply to the following resources:
> 
> Resource
> Relevant access or licensing issue
> 
> Stanford MRNet
> Research-use agreement
> 
> Stanford SKM-TEA
> Registration and data-use terms
> 
> NYU fastMRI and fastMRI+
> Data-sharing agreement for images; separately released annotations
> 
> Osteoarthritis Initiative (OAI)
> Data Use Certification 
> 
> KneeMRI
> CC BY-NC-ND 4.0
> 
> KneeXNet-2.5D
> Public OAI-derived annotated images and pretrained weights; no explicit repository license that I could identify
> 
> Could the hosts give a yes or no for each resource under this competition's external-data rules? If the answer differs between training on the images and fine-tuning publicly released weights, please state that separately. It would also help to know whether using each resource is compatible with the winner's requirement to release the final model. I understand that teams remain responsible for complying with the original providers' terms.
> 
> Because the same question keeps appearing in different threads, could the hosts pin the answer in the Discussion so all teams can find and follow the same guidance?
> 
> @javaduke95


---

### `[SOTA_RECIPE]` [735304] Best single-model score (132 comments, `Signal: 20.15`)
**URL**: https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/735304

> **Message 1 by User (2026-10-10)** [Votes: 6]:
> LB0.945 no fold
> 
> only LLM labels. (no pseudo)

> **Message 2 by User (2026-10-10)** [Votes: 1]:
> single fold Dinov2 (ViT) : 94.3. Best ensemble 95.1

> **Message 3 by User (2026-10-09)** [Votes: 9]:
> My public scores:
> 
> ConvNeXt-T (2.5D), single model: 0.953
> DINOv2 ViT-S (2.5D), single model: 0.951
> Ensemble of the two: 0.955
> 
> Both single models are trained with pseudo labels, so they are not pure report-label single models. No external data used yet, though.

> **Message 4 by User (2026-10-09)** [Votes: 7]:
> model is not the key. it is your labels.

> **Message 5 by User (2026-08-14)** [Votes: 81]:
> What is the best score you’ve achieved with a single model?
> 
> I’m trying to train a strong single model first before moving on to ensembling, and I’m curious how far a single model can go.
> 
> I’ve noticed that most of the public solutions use ensembles of 20+ models and achieve around 0.91. For those scoring around 0.92–0.94 on the leaderboard, are you also using ensembles, or is it possible to reach that range with a single model?
> 
> For reference, my current best score is 0.887 with DINOv2.


---

### `[METRIC_NUANCE]` [733343] Knee Abnormality Detection AI Challenge Overview (15 comments, `Signal: 19.35`)
**URL**: https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/733343

> **Message 1 by User (2026-08-06)** [Votes: 98]:
> Courtesy of Dr. Jacob Kazam
> 
> Overview of the Clinical Problem
> The 2026 RSNA Knee Abnormality Detection AI Challenge asks participants to build machine learning models that detect a defined set of clinically important abnormalities on knee MRI examinations. It is the first RSNA AI Challenge to pair every imaging study with the text of its original radiology report, and to do so across a large, multilingual, international dataset. Models may learn from both the images and the report text, reflecting how knee MRI is actually interpreted and communicated in clinical practice.
> 
> The knee is one of the most frequently injured and most frequently imaged joints in the body. Knee disorders are a major and growing cause of pain and disability worldwide, affecting athletes, manual workers, and older adults alike. The knee is the most common site of osteoarthritis, which affects nearly a quarter of adults aged 40 and older, an estimated 654 million people worldwide. Acute injuries are also common: knee injuries account for an estimated 15 to 40 percent of all sports-related injuries.
> 
> Several structures are commonly involved. Anterior cruciate ligament (ACL) tears are among the most frequent sports injuries, often occurring during sudden pivots or changes of direction and leading to immediate instability. Medial collateral ligament (MCL) injuries typically result from outward (valgus) stress on the knee and frequently accompany other structural damage. Meniscal tears, which may be traumatic or degenerative, disrupt the joint’s shock absorption and mechanics, producing pain, locking, and functional limitation. Cartilage loss, joint effusion, synovitis, bone contusions, fractures, and Baker (popliteal) cysts are additional findings that cause symptoms and influence management.
> 
> MRI is central to evaluating the knee because it depicts all of these structures, including ligaments, menisci, articular cartilage, and bone, without ionizing radiation, providing a comprehensive whole-joint assessment that other modalities cannot match. However, MRI interpretation varies across readers and practice settings, and access to subspecialty-trained musculoskeletal (MSK) radiologists is limited in many parts of the world. Reliable, consistent automated detection of knee abnormalities could help extend expert-level interpretation, reduce variability, and support more timely care.
> 
> The goal of this competition is to develop machine learning models that detect twelve clinically important knee abnormalities, learning from a large international dataset of knee MRI examinations paired with their original, multilingual radiology reports.
> 
> Anatomical Overview
> The knee is a synovial hinge joint formed by three bones: the femur (thigh bone) above, the tibia (shin bone) below, and the patella (kneecap) in front. The ends of these bones are covered by articular cartilage, a smooth layer that allows near-frictionless motion and distributes load. The joint is enclosed by a capsule lined with synovium, which produces lubricating fluid; an abnormal excess of this fluid is termed a joint effusion, and inflammation of the synovium is termed synovitis.
> 
> Knee anatomy: anterior view (top) and lateral view (bottom), showing the femur, tibia, patella, cruciate ligaments, and meniscus. Illustrations by BruceBlaus, CC BY 3.0, via Wikimedia Commons.
> 
> For the purposes of this challenge, the knee is considered in three compartments. The medial compartment lies between the medial femoral condyle and the medial tibial plateau, on the inner side of the knee. The lateral compartment lies between the lateral femoral condyle and the lateral tibial plateau, on the outer side. The patellofemoral compartment lies between the patella and the femoral trochlea, the groove on the front of the femur. Osteoarthritis, or cartilage loss, is assessed separately in each of these three compartments.
> 
> Four ligaments stabilize the knee. The anterior cruciate ligament (ACL) and posterior cruciate ligament (PCL) lie within the joint, in the intercondylar notch, and control front-to-back stability and rotation. The medial collateral ligament (MCL) and lateral collateral ligament (LCL) run along the inner and outer sides of the knee and resist side-to-side stress. This challenge focuses on tears of the ACL and the MCL.
> 
> Between the femur and tibia sit two menisci, the medial meniscus and the lateral meniscus, C-shaped wedges of fibrocartilage that cushion the joint, absorb shock, and improve the fit between the rounded femur and the relatively flat tibia. Tears of the medial and lateral meniscus are evaluated separately.
> 
> Other relevant structures include the bone marrow within the femur, tibia, and patella, where a bruise from impact is called a bone contusion (or bone marrow edema) and a break in the bone is a fracture; and the soft tissues behind the knee, where a fluid-filled outpouching of the joint lining is called a Baker, or popliteal, cyst.
> 
> Imaging Overview
> Several modalities can image the knee. Radiographs (X-rays) show bones and joint-space narrowing but cannot directly visualize ligaments, menisci, or cartilage. Ultrasound and CT have specific roles but offer limited soft-tissue contrast for the internal structures of the joint. Magnetic resonance imaging (MRI) is the reference standard for evaluating internal derangement of the knee because it provides excellent soft-tissue contrast, depicts ligaments, menisci, cartilage, and bone marrow simultaneously, and does not use ionizing radiation.
> 
> A knee MRI examination is not a single image but a set of series, each acquired with a particular pulse sequence and in a particular imaging plane. The three standard planes are axial (cross-sectional, viewed as if looking up through the leg), coronal (a front-facing, side-to-side view), and sagittal (a side-profile, front-to-back view). Different structures are best seen in different planes; for example, the cruciate ligaments and menisci are well evaluated on sagittal and coronal images, and the patellofemoral cartilage on axial images.
> 
> Sequences differ in how they weight tissue signal. Fluid-sensitive sequences, such as proton-density or T2-weighted images, often with fat suppression, make edema, effusion, and tears appear bright and are central to detecting most abnormalities; a meniscal tear, for instance, appears as abnormally increased signal that reaches the surface of the meniscus on more than one image. Other sequences emphasize anatomy or cartilage detail. Interpreting a study therefore requires integrating information across multiple series, planes, and slices for the same knee, an inherently three-dimensional task.
> 
> Sagittal proton-density, fat-suppressed (fluid-sensitive) MRI of the knee, the type of sequence on which most abnormalities are detected. Image by Ptrump16, CC BY-SA 4.0, via Wikimedia Commons.
> 
> For the purpose of the 2026 Knee Abnormality Challenge, a “fluid sensitive” sequence refers to one in which edema, hemorrhage, and other types of fluid appear bright and fat is suppressed in some way.
> 
> Because findings can be subtle and the criteria for what counts as clinically significant are nuanced, interpretation varies between readers. This variability, combined with limited access to subspecialty MSK radiologists, motivates the development of consistent automated tools.
> 
> Label Description
> Models are evaluated on twelve binary labels, each indicating the presence or absence of a specific finding in the imaged knee. The labels, and the criteria used by the annotating radiologists, are summarized below. In each case, ambiguous or borderline findings (“on the fence”) were graded as negative to favor specificity.
> 
> ACL tear: A high-grade partial or full-thickness tear of the anterior cruciate ligament, meaning complete discontinuity of the ligament, or more than 50 percent of fibers disrupted, with or without secondary signs such as characteristic pivot-shift bone contusions. Mild signal change, degeneration, or thickening without discontinuity is graded negative.
> 
> MCL tear: A high-grade partial or complete acute tear of the medial collateral ligament, with disrupted fibers and edema within and adjacent to the ligament. Low-grade sprains and chronic or remote stress changes are graded negative.
> 
> Medial meniscus tear: Abnormal signal that definitely contacts the meniscal surface on at least two images, or a morphologic abnormality such as a truncated, diminutive, or displaced fragment, involving the medial meniscus. Intrasubstance degeneration that does not reach the surface is negative.
> 
> Lateral meniscus tear: The same criteria applied to the lateral meniscus.
> 
> Medial compartment osteoarthritis: A moderate or large area (roughly 1 cm or greater) of high-grade cartilage loss, defined as greater than 50 percent of cartilage thickness, in the medial compartment, with or without underlying subchondral marrow changes.
> 
> Lateral compartment osteoarthritis: The same criteria applied to the lateral compartment.
> 
> Patellofemoral compartment osteoarthritis: The same criteria applied to the patellofemoral compartment.
> 
> Joint effusion: A moderate or large amount of fluid distending the joint.
> 
> Synovitis: Inflammation and thickening of the synovial lining of the joint.
> 
> Baker (popliteal) cyst: A moderate or large fluid collection in the characteristic location behind the knee.
> 
> Contusion: A bone contusion, seen as bone marrow edema-like signal from impact, without a discrete fracture line.
> 
> Acute fracture: An acute cortical break or fracture line.
> 
> Each study in the annotated reference set was independently labeled by two subspecialty-trained MSK radiologists, with disagreements adjudicated by a third radiologist to produce a single consensus ground truth. Labels are assigned at the level of the whole examination, for a single knee.
> 
> Examples
> The following annotated examples, drawn from the challenge’s image annotation guidelines, illustrate representative positive and negative cases for several of the labels. In each figure, yellow arrows and arrowheads mark the findings described in the caption.

> **Message 2 by User (2026-08-10)** [Votes: 7]:
> For the train.csv. It contains only 58 flagged labels. Rest are NaN.
> Those flags do not reflect what is the report. 
> Does the reports are the GT?

> **Message 3 by User (2026-08-10)** [Votes: 4]:
> Thanks for the overview! For anyone getting started, the key insight is that this is a multi-label classification problem — each study can have multiple abnormalities present simultaneously. The 12 abnormality categories each need their own probability prediction.

> **Message 4 by User (2026-10-07)** [Votes: 0]:
> Hi study organizers: can you comment on how to deal with bilateral knee mri's in which both left and right side are within the same studyid? If there is only one label per studyid then how should this be resolved? Just report every positive in either knee? For example if left knee ACL is torn but right knee ACL is normal then how should it be labeled if both studies are within same studyid?


---

### `[METRIC_NUANCE]` [733965] Use of Commercially Hosted LLMs (13 comments, `Signal: 14.31`)
**URL**: https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/733965

> **Message 1 by User (2026-09-23)** [Votes: -1]:
> Thanks for the clarification! Just one quick question: if LLM-generated labels/embeddings from the reports are allowed, would it also be okay to use an external LLM to extract structured features like findings, laterality, or severity and combine those with MRI features?
> 
> And would this be allowed at inference time only if those same features can be generated from the information available at inference?

> **Message 2 by User (2026-08-09)** [Votes: 23]:
> Use of commercially hosted LLMs and other external inference services is permitted, provided that the service and method of use otherwise comply with the Competition Rules, including requirements that external data, models, software, and associated tools be reasonably accessible to all participants and of minimal cost. 
> 
> In other words, for purposes of this competition, submitting Competition Data, including report text, to an external LLM or API for inference or other computational processing (for example, extracting labels from reports) will not, by itself, be considered prohibited PRIVATE SHARING of Competition Data outside the Team.
> 
> Please refer to the RSNA Knee Abnormality Detection Competition Rules.  This is in accordance to Section 2.6.b, EXTERNAL DATA AND TOOLS.
> 
> The PRIVATE SHARING restriction is intended to prohibit sharing Competition Data, code, or competition-specific work product with other participants, teams, or third parties for collaboration or competitive use outside the registered Team.
> 
> Participants remain responsible for ensuring that any external service complies with all applicable Competition Rules and the service's terms of use, including the requirements for reasonable accessibility and minimal cost.
> 
> The Competition Host reserves the right to determine whether a particular service, model, or configuration is reasonably accessible, is prohibitively costly, or otherwise creates an unfair competitive advantage.

> **Message 3 by User (2026-08-21)** [Votes: 1]:
> Ok, by the sentence: "(for example, extracting labels from reports) will not, by itself, be considered prohibited PRIVATE SHARING of Competition Data outside the Team." i can conclude that i can use LLM API (i.e. openAI) to read the reports, which are actually in diifferent languages, to generate the labels, so i don't have to struggle?
> I know that the answer may be abvious but i just want to make 100% sure i can save me so much trouble and focus on model not in getting the target labels without been kicked out from the competence.
> Thanks!

> **Message 4 by User (2026-08-14)** [Votes: 3]:
> To make the dataset question above concrete: the Osteoarthritis Initiative (OAI) is free of charge and open to any researcher after a click-through data use agreement, but the agreement limits use to non-commercial research. The same access pattern covers MRNet, fastMRI+ and SKM-TEA, so a ruling on the category would settle it for essentially every public knee-MRI resource. Given the prize money, could the host confirm whether external datasets under research-only agreements are permitted, and if so whether the winners' open-source obligation is affected? Teams need this before committing pretraining work ahead of the entry deadline. Thank you.


---

### `[GENERAL_DISCUSSION]` [733375] Welcome to Knee Abnormality Detection Challenge! (1 comments, `Signal: 2.82`)
**URL**: https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/733375

> **Message 1 by User (2026-08-06)** [Votes: 17]:
> The knee is the largest joint in the human body, and MRI is central to diagnosing major sports injuries, trauma, and degenerative disease, but interpretation is demanding and access to subspecialty musculoskeletal expertise is uneven. 
> 
> This challenge invites the RSNA and Kaggle community to build models that detect 12 clinically important knee abnormalities, spanning ligament and meniscal tears, osteoarthritis, effusion, synovitis, fracture, and more.
> 
> This is also RSNA’s first AI Challenge to pair MRI examinations with original multilingual radiology reports. We hope that combination encourages creative, rigorous work that reflects the **real **clinical task: connecting images, language, and meaningful patient care.
> 
> And don't forget the efficiency prizes!   "Real world" here also means striking a balance between label-level accuracy and efficient use of resources.
> 
> A challenge dataset can make a large collaborative effort look deceptively simple. We are deeply grateful to the contributing institutions, radiologists, data and privacy teams, RSNA colleagues, and Kaggle team who made this possible.  
> 
> Above all, we owe it to you… every participant who will bring curiosity, technical skill, and healthy skepticism to the work. Whether this is your first Kaggle competition or your hundredth, we hope you will share reproducible ideas, learn from one another, and help move imaging AI forward thoughtfully. 
> 
> Good luck, and welcome.
> 
> Learn more about the challenge and RSNA’s AI Challenge program.

> **Message 2 by User (2026-08-21)** [Votes: 0]:
> It was great to read about it but i difinetly dont have any idea how to start with 500 gb dataset and 300 gb ssd drive). I would be glad if you can remove me from competition lists and thank you for great opportunity to read about ml medical research since it was just was partly covered by med engineering course in my university…


---

### `[GENERAL_DISCUSSION]` [730709] How to get started + Competition's Official Discord (2 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/730709

> **Message 1 by User (2026-07-30)** [Votes: 10]:
> Information for newbies
> New to machine learning and data science? No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!
> 
> New to Kaggle? Take a look at a few videos to learn a bit more about site etiquette, Kaggle lingo, and how to enter a competition using Kaggle Notebooks. Publish and share your models on Kaggle Models!
> 
> Looking for a team? Express your interest in joining a team through our Team Up feature.
> 
> Remember: Kaggle is for everyone. Whether you're teaming up or sharing tips in the competition forum, we expect everyone to follow our Kaggle community guidelines.
> 
> Competition's Official Discord
> In addition to this competition forum, you can continue the discussion in our official Kaggle Discord Server here:
> 
> discord.gg/kaggle
> The Discord is a great place to ask getting started questions, chat about the nuances of this competition, and connect with potential team mates. Learn more about Discord at our announcement here. Here are a few things to keep in mind though:
> 
> 1. Discord Competition Channels are 'Public' - Don't Share Private Information
> 
> Discord channels for specific competitions are considered 'public' spaces where you are allowed to talk about competition details. Please remember that private sharing of competition code or data outside of your team is, as always, not permitted. Code sharing must always be done publicly through the Kaggle forums/notebooks.
> 
> 2. Discord Competition Channels are Not Monitored by Staff - Keep Important Information on the Kaggle Forums
> 
> Kaggle Staff and Hosts running competitions will not monitor Discord or be available to answer questions in Discord. This is intended to be a more casual space to discuss competitions and help each other. Please keep important questions, insights, writeups, and other valuable conversation on the Kaggle forums. 
> 
> Happy modeling!

> **Message 2 by User (2026-08-06)** [Votes: 0]:
> Thank you for the helpful introduction and resources! I'm excited to join this competition and learn from the community. The multimodal nature of this challenge looks both interesting and challenging. Looking forward to experimenting with different approaches, following the discussions, and improving my skills throughout the competition. Best of luck to everyone participating!

> **Message 3 by User (2026-10-01)** [Votes: 0]:
> Thanks @macruzbar!!!!


---

## Competition: `enveda-CASMI26-molecule-id-mass-spectra`

### `[BUG_ALERT]` [741359] Welcome to CASMI 2026! (10 comments, `Signal: 20.19`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/741359

> **Message 1 by User (2026-09-14)** [Votes: 26]:
> Welcome to CASMI 2026! Identifying molecules from their mass spectra is one of the most important challenges in life sciences, but the number of machine learning scientists who have worked on mass spectra is very small relative to the size and importance of the scientific problem. This creates a great opportunity to have a large impact in a short amount of time. Hence this competition!  
> 
> The kinds of methods that have been developed in recent years against standing benchmarks like MassSpecGym span a wide variety of approaches that resemble those used across technology and life sciences. We are very excited to see the approaches this community comes up with to tackle this problem. We are especially excited to be providing spectra for many molecules whose structures have not been previously described. 
> 
> A note on external data and licensing
> 
> We want everyone to have a fair and enjoyable competition, so a quick reminder on the use of external data and models.
> 
> Per the competition rules, the winning solution cannot include any licenses that would otherwise prohibit commercial use or redistribution. When you submit a winning solution, you grant us, the Competition Sponsor, a license to that solution and represent that you have the unrestricted right to grant it. Any external data, models, or tools you rely on must be compatible with that license.
> 
> We're aware that datasets exist which carry licenses that fall into this category, i.e. terms that restrict commercial use or redistribution. These should be avoided. Solutions built on data or tools that cannot be commercially licensed will not be eligible to win, and we reserve the right to disqualify any submission that does not comply or can’t be reproduced with allowed data and tools.
> 
> As always, any external data used must be publicly available and equally accessible to all participants.
> 
> Special thanks to the Kaggle team Ashley, Walter, and Addison for all their support!
> 
> Happy modeling!

> **Message 2 by User (2026-10-09)** [Votes: 0]:
> please who can help me with the reson why code has been saying submission error for like 4 submissions now?

> **Message 3 by User (2026-10-03)** [Votes: 0]:
> Looking to form or join a team for CASMI 2026 - need two more people.
> 
> Where I'm at: I've completed a thorough EDA pass on the training data molecule-level train/validation splitting (to avoid spectra from the same structure leaking across both sets), rebalancing the heavy spectra-per-molecule skew, checking precursor mass and adduct coverage against the test set's documented ranges, and isolating a systematic adduct-mislabeling bug that was corrupting ~40k rows (traced to an adduct-standardization error, fixed rather than discarded). Background: final-year Biochemistry student, currently a Machine Learning Engineering intern, comfortable in Python and ML fundamentals, with real domain chemistry knowledge to bring to structure elucidation. Worth noting this is my first Kaggle competition specifically, though not my first serious ML project.
> 
> What I need: two teammates who'll engage seriously and contribute real work I'm not filtering by experience level, just looking for genuine commitment. Complementary skills that would help a lot: cheminformatics/RDKit experience, deep learning or generative modeling (spectrum-to-structure especially), or bandwidth to help split up retrieval-baseline and modeling work.
> 
> Comment or DM if you're interested, or if you've got a team with a spot open.
> 
> — Dara

> **Message 4 by User (2026-10-02)** [Votes: 0]:
> What if I learn every concept from Gemini?? Means of python , data science and every skill needed?? Is it that reliable or I should use some different app?? Please guide me.


---

### `[METRIC_NUANCE]` [741404] A complete statistical tour of the data (EDA notebook) (3 comments, `Signal: 16.74`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/741404

> **Message 1 by User (2026-09-15)** [Votes: 27]:
> I went through this dataset column by column and wrote the whole thing up in a public notebook. Sharing it here because three of the findings change how you should set up your validation, and it seems better if we all start from the same picture of the data.
> 
> https://www.kaggle.com/code/josefreitasalvesneto/casmi-2026-a-complete-statistical-tour
> 
> A few things you may want to know before you write any preprocessing code:
> 
> The public leaderboard is measuring the wrong thing. The data page says the test file is "comprised of examples from the training dataset" — it turns out to be enveda-180 rows, and the ones I checked are byte-for-byte identical to training spectra. That library is drug-like screening chemistry, not the natural products the prize is decided on. I would not read anything into a public score.
> Test spectra only look 10x richer than training spectra. Median 230 raw peaks vs 27 — but 82% of the test peaks are below 1% relative intensity, and at a 1% floor the two land at 18 and 14. The apparent train/test shift is mostly noise floor.
> A plain library search already scores MRR@25 = 0.907 on natural products that have reference spectra. Novelty Class 1 is close to solved without any learning, which means the entire score differential is in Classes 2 and 3.
> The notebook also covers the 11 source libraries and how little they overlap, chemical space, adducts, collision energy, neutral losses, and where the labels wobble. Every number is computed in the notebook, so you can check any of it yourself.
> 
> Corrections very welcome — if something looks wrong, tell me and I will fix it. Good luck, everyone.

> **Message 2 by User (2026-09-15)** [Votes: 7]:
> Thanks for making this notebook, and welcome to CASMI 2026!
> 
> Just to clarify something about the public leaderboard and test.parquet: the public leaderboard score is calculated not on the contents of the test.parquet downloadable dummy file (which as you say just contains a sample of Enveda-180 spectra and is there to demonstrate the size and scope and structure of the test data), but rather on the public split of the Hidden test set provided to your submission notebook.

> **Message 3 by User (2026-09-15)** [Votes: 3]:
> Thank you for sharing this detailed analysis. @josefreitasalvesneto I’m still a beginner and learning step by step, but I’m very interested in the chemistry + data science side of this competition.
> I’m currently trying to organize the main areas that could be useful for this type of problem, including:
> 
> Cheminformatics
> Molecular structures, SMILES, fingerprints, molecular descriptors, similarity search.
> Python: RDKit
> QSAR / QSPR
> Predicting molecular or chemical properties using machine learning.
> Python: RDKit + Scikit-learn
> Molecular Property Prediction
> Predicting properties such as activity, toxicity, solubility, and other molecular characteristics.
> Python: RDKit + Scikit-learn / PyTorch
> Molecular Representation Learning
> Learning useful representations from SMILES, fingerprints, molecular graphs, and molecular features.
> Python: RDKit + PyTorch / TensorFlow
> Graph Neural Networks for Chemistry
> Representing atoms as nodes and chemical bonds as edges.
> Python: PyTorch Geometric / DGL + RDKit
> AI for Drug Discovery
> Virtual screening, molecular activity prediction, hit discovery, and lead optimization.
> Python: RDKit + DeepChem
> Molecular Generation / Generative Chemistry
> Using generative models to create or modify molecules with desired properties.
> Python: RDKit + PyTorch + Transformers / diffusion models
> Chemical Reaction Prediction
> Reaction prediction, reaction classification, retrosynthesis, and reaction-condition prediction.
> Python: RDKit + reaction datasets + Transformer models
> Molecular Optimization
> Optimizing molecules toward specific chemical or biological objectives.
> Python: RDKit + Bayesian Optimization / evolutionary optimization
> Virtual Screening
> Searching large chemical libraries and ranking compounds that may match a target.
> Python: RDKit + similarity search + Mranking
> Computational Chemistry + Machine Learning
> Combining computational chemistry, molecular simulations, and ML.
> Python: RDKit + DeepChem + scientific Python tools
> Chemometrics
> Applying statistics and machine learning to chemical and experimental data.
> Python: NumPy + Pandas + Scikit-learn + SciPy
> Spectroscopy + Machine Learning
> Working with NMR, IR, Raman, and mass-spectrometry data.
> Python: NumPy + SciPy + Scikit-learn + PyTorch
> Materials Informatics
> Using data science and ML to discover and predict properties of materials and compounds.
> Python: pymatgen + Matminer + Scikit-learn / PyTorch
> I’m also trying to collect books, research papers, courses, official documentation, GitHub repositories, Python libraries, datasets, and practical notebooks for each section, so I can understand both the theory and the implementation.
> Your analysis of the validation setup, source-library overlap, noise floor, adducts, collision energy, and especially the Class 1 vs. Classes 2–3 difference is very helpful. I’ll definitely go through the notebook carefully before making assumptions about preprocessing or validation.
> I’m still learning, so I may not understand everything correctly yet, but I’d really appreciate any corrections or recommendations from people with more experience in computational chemistry and mass spectrometry.
> Thank you again for sharing your work and helping everyone start from a better understanding of the data. 🙏
> Good luck with the competition!


---

### `[GENERAL_DISCUSSION]` [743974] All you need is a good ranker (3 comments, `Signal: 14.35`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/743974

> **Message 1 by User (2026-09-28)** [Votes: 22]:
> When I started this competition, I thought the hardest issue would be finding the right molecule. Turns out, the bottleneck is the ranker. (of course, excluding Regime C)
> 
> For instance, my CV scores MRR @ 25 : 0.584 in Regime B and 0.846 in Regime A
> 
> Among them, number of molecules not in my top 25 are very low:- (below are CV MRR scores)
> 
> On an unrelated note, it's so sad to see instances where the true structure isnt part of my guesses, but the guesses my pipeline makes is so close
> 
> Also, feel free to use my ranker if it helps anyone : https://claude.ai/artifact/VAQDJb8q7hLFyhv66hWMNL
> (It is still at Phase-0 and very unstable, so if anyone is using it, please share some feedback)
> 
> It is very useful to visualize and see where you went wrong and its very fun to visualize these molecules

> **Message 2 by User (2026-09-28)** [Votes: 1]:
> Your dashboard is amazing! Simple but informative, did you use AI to make it? Could you open source the UI or prompt?

> **Message 3 by User (2026-10-01)** [Votes: 0]:
> please what is the path to Concatenate key spectral metadata as tabular features: precursor_mz, ionization_mode, adduct (one-hot encoded), collision_energy_ev, and instrument_type.


---

### `[METRIC_NUANCE]` [741666] My Learning Roadmap for the Enveda CASMI 2026 Kaggle Competition (0 comments, `Signal: 14.27`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/741666

> **Message 1 by User (2026-09-16)** [Votes: 22]:
> I’m still a beginner and learning step by step, and I’m not participating in this competition at the moment. However, I found the chemistry + data science side of this problem very interesting, so I decided to organize the topics and resources that I think could be useful for understanding this type of challenge.
> 
> I may misunderstand some parts, so corrections and recommendations from people working in computational chemistry, metabolomics, mass spectrometry, and machine learning are very welcome.
> 
> My goal here is not to present a solution, but to build a learning roadmap.
> 
> 1️⃣ Cheminformatics
> 
> Understanding molecules computationally:
> 
> SMILES
> Molecular structures
> Molecular fingerprints
> Molecular descriptors
> Molecular similarity
> 
> 🐍 Main tool: RDKit
> 
> 📚 Resources:
> 
> RDKit Documentation: https://www.rdkit.org/docs/
> RDKit Book: https://www.rdkit.org/docs/RDKit_Book.html
> RDKit Python Getting Started: https://www.rdkit.org/docs/GettingStartedInPython.html
> 
> RDKit provides functionality for fingerprints, molecular similarity, descriptors, chemical features, and many other cheminformatics tasks.
> 
> 2️⃣ QSAR / QSPR & Molecular Property Prediction
> 
> Using molecular representations and machine learning to predict chemical properties.
> 
> Useful topics:
> 
> Molecular descriptors
> Fingerprints
> Regression / classification
> Molecular property prediction
> Dataset splitting
> Cross-validation
> 
> 🐍 Tools:
> RDKit + Scikit-learn + DeepChem
> 
> 📚 Resource:
> 
> DeepChem Tutorials: https://deepchem.io/tutorials/
> DeepChem Book: https://deepchem.io/
> 
> DeepChem includes tutorials covering molecular fingerprints, molecular featurization, graph convolutions, dataset splitting, and molecular machine learning.
> 
> 📄 Research:
> 
> Analyzing Learned Molecular Representations for Property Prediction: https://arxiv.org/abs/1904.01561
> 
> 3️⃣ Molecular Representation Learning
> 
> A molecule can be represented in many ways:
> 
> SMILES → sequence
> Fingerprint → vector
> Molecule → graph
> Chemical descriptors → numerical features
> 
> The interesting question is: which representation captures the information needed by the model?
> 
> 📚 Useful resources:
> 
> DeepChem Molecular ML tutorials: https://deepchem.io/tutorials/
> RDKit Book: https://www.rdkit.org/docs/RDKit_Book.html
> 
> 📄 Research:
> 
> Analyzing Learned Molecular Representations for Property Prediction: https://arxiv.org/abs/1904.01561
> 
> 4️⃣ Graph Neural Networks for Chemistry
> 
> Representing:
> 
> Atoms → Nodes
> Bonds → Edges
> 
> Then using message passing to learn molecular representations.
> 
> 🐍 Tools:
> 
> PyTorch Geometric: https://pytorch-geometric.readthedocs.io/
> DGL: https://www.dgl.ai/
> RDKit: https://www.rdkit.org/
> 
> 📄 Research:
> 
> Graph Neural Networks for Molecules: https://arxiv.org/abs/2209.05582
> Geometric Deep Learning: https://arxiv.org/abs/2104.13478
> 
> PyTorch Geometric provides a framework for GNNs and geometric deep learning, while research on molecular GNNs covers property prediction, molecular optimization, generation, and related tasks.
> 
> 5️⃣ Mass Spectrometry / MS/MS ⭐
> 
> For this competition, this is one of the areas I would study most carefully.
> 
> Important concepts include:
> 
> MS1 / MS2
> Precursor ions
> Fragment ions
> m/z
> Peak intensity
> Adducts
> Ionization modes
> Collision energy
> Mass tolerance
> Spectral similarity
> Spectral libraries
> 
> 🐍 Python tools:
> 
> matchms
> https://matchms.readthedocs.io/
> 
> GitHub:
> https://github.com/matchms/matchms
> 
> matchms is designed for importing, processing, cleaning, and comparing tandem mass spectra.
> 
> 6️⃣ Spectral Similarity & Spectral Embeddings
> 
> Instead of treating a spectrum as just a list of peaks, machine learning can learn relationships between fragments.
> 
> One interesting approach is Spec2Vec, inspired by Word2Vec.
> 
> GitHub:
> https://github.com/iomega/spec2vec
> 
> Tutorial / practical notebooks:
> https://github.com/iomega/spec2vec_gnps_data_analysis
> 
> The repository includes practical notebooks for processing MS/MS data, calculating spectral similarities, and building molecular networks.
> 
> 📄 Research:
> Spec2Vec: Improved mass spectral similarity scoring through learning of structural relationships
> 
> https://doi.org/10.1371/journal.pcbi.1008724
> 
> 7️⃣ Molecular Identification From MS/MS
> 
> This is especially relevant to the competition.
> 
> The general problem can be viewed as:
> 
> Mass spectrum → possible molecular candidates → rank candidates
> 
> Important concepts:
> 
> Molecular formula prediction
> Structure identification
> Candidate generation
> Candidate ranking
> Spectral matching
> Fragmentation patterns
> 
> One important ecosystem to study is SIRIUS + CSI:FingerID.
> 
> GitHub:
> https://github.com/sirius-ms/sirius
> 
> SIRIUS documentation:
> https://v6.docs.sirius-ms.io/
> 
> SIRIUS can use isotope and fragmentation information for molecular-formula identification and integrate tools such as CSI:FingerID for structure identification.
> 
> 8️⃣ Spectral Libraries & External Chemical Data
> 
> Potentially useful sources for understanding and experimenting with MS/MS data include:
> 
> 🧪 GNPS
> https://gnpsdocs.readthedocs.io/
> 
> GNPS provides spectral-library search, molecular networking, public MS/MS datasets, and tools for MS/MS identification and analysis.
> 
> 🧪 MassBank of North America (MoNA)
> https://mona.fiehnlab.ucdavis.edu/
> 
> MoNA provides downloadable mass-spectral collections, including experimental and LC-MS/MS spectra.
> 
> 🧪 NIST Chemistry WebBook
> https://webbook.nist.gov/chemistry/
> 
> NIST provides mass spectra for more than 33,000 compounds along with other chemical and physical data.
> 
> 9️⃣ Machine Learning for MS/MS
> 
> This is where chemistry and ML become particularly interesting.
> 
> Possible approaches include:
> 
> Classical spectral similarity
> Fingerprint-based retrieval
> Neural networks
> Contrastive learning
> Spectral embeddings
> Transformer-based models
> Candidate retrieval + reranking
> 
> One interesting open-source example is MIST, which works with MS/MS spectra and molecular candidates.
> 
> GitHub:
> https://github.com/samgoldman97/mist
> 
> The repository includes examples for candidate ranking and embedding mass spectra into a continuous representation space.
> 
> 🔟 Molecular Networking
> 
> Another useful concept is molecular networking.
> 
> Instead of analyzing every spectrum independently:
> 
> Spectrum → Spectrum similarity → Network → Molecular families
> 
> GNPS documentation:
> https://gnpsdocs.readthedocs.io/en/latest/networking/
> 
> This represents spectra as nodes and spectral similarities as connections, allowing related molecules to form molecular families.
> 
> 1️⃣1️⃣ Computational Chemistry + Machine Learning
> 
> For deeper study:
> 
> Molecular simulation
> Quantum chemistry
> Molecular descriptors
> 3D molecular representations
> ML approximation of expensive calculations
> 
> 📄 Useful research:
> 
> Molecular Property Prediction: A Multilevel Quantum Interactions Modeling Perspective
> https://arxiv.org/abs/1906.11081
> 
> This is probably a deeper direction rather than the first thing I would study for understanding the competition.
> 
> 1️⃣2️⃣ Chemometrics
> 
> The statistical side of chemical data:
> 
> PCA
> PLS
> Feature selection
> Dimensionality reduction
> Regression
> Classification
> Experimental variation
> 
> 🐍 Tools:
> 
> NumPy + Pandas + SciPy + Scikit-learn
> 
> This area is useful because chemical datasets are not only an ML problem; understanding measurement variability and experimental structure is also important.
> 
> 1️⃣3️⃣ Spectroscopy + Machine Learning
> 
> A broader area worth exploring:
> 
> Mass spectrometry
> NMR
> IR
> Raman
> UV/Vis
> 
> The ML pipeline can often look like:
> 
> Raw/processed spectrum → preprocessing → representation → model → identification/prediction
> 
> For this competition, however, I would focus primarily on MS/MS rather than trying to study every spectroscopy field at once.
> 
> 📚 A few resources I would prioritize
> 
> If I had to organize the learning path, I would start with:
> 
> RDKit
> https://www.rdkit.org/docs/
> 
> DeepChem
> https://deepchem.io/
> 
> matchms
> https://matchms.readthedocs.io/
> 
> GNPS
> https://gnpsdocs.readthedocs.io/
> 
> Spec2Vec
> https://github.com/iomega/spec2vec
> 
> SIRIUS
> https://github.com/sirius-ms/sirius
> 
> MoNA
> https://mona.fiehnlab.ucdavis.edu/
> 
> NIST Chemistry WebBook
> https://webbook.nist.gov/chemistry/
> 
> MIST
> https://github.com/samgoldman97/mist
> 
> DeepChem Book
> https://deepchem.io/
> 
> 🧠 What I am trying to understand
> 
> After reading more about this competition, I think the interesting part is not simply:
> 
> «"Train a neural network on spectra."»
> 
> There are several layers:
> 
> Chemical structure
> ↓
> Ionization / adduct
> ↓
> Precursor ion
> ↓
> Fragmentation
> ↓
> MS/MS spectrum
> ↓
> Spectral representation
> ↓
> Candidate retrieval
> ↓
> Candidate ranking
> ↓
> Molecular identification
> 
> And this makes the problem interesting from both the chemistry and machine learning perspectives.
> 
> I also want to understand the validation strategy carefully before making assumptions about preprocessing or modeling. Things such as source-library overlap, adducts, collision energy, noise, and differences between chemical classes can potentially affect how well a model generalizes.
> 
> I’m still learning, so I may have some things wrong. If you have experience with mass spectrometry, metabolomics, cheminformatics, computational chemistry, or ML for chemistry, I would really appreciate corrections, resources, or recommendations.
> 
> I’m sharing this mainly as a learning roadmap, not as a competition solution.
> 
> Thank you for reading, and good luck to everyone participating in the competition!


---

### `[RULES_COMPLIANCE]` [744470] Chasing medals with price ineligible sources (15 comments, `Signal: 13.83`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/744470

> **Message 1 by User (2026-10-09)** [Votes: 3]:
> You do not need NIST or any additional data for a better score.

> **Message 2 by User (2026-09-29)** [Votes: 16]:
> Well, pretty much this. Is using NIST dataset, gated weights etc. is going to be enforced somehow on gold medals? My Claude agent insist we need the NIST based model for better score 🤣 Since I don't care about the money, I might as well go and do it if I can (?) Who knows maybe this is what top teams do already 😁😅

> **Message 3 by User (2026-10-02)** [Votes: 1]:
> Another Kaggle competition called "Detect illegal use of forbidden training data (e.g., inducing poison data in hidden test data)". I think some papers claim to "detect" training data, maybe it is possible

> **Message 4 by User (2026-09-29)** [Votes: 6]:
> I’m sorry, the NIST dataset is not permitted for solutions, any solution using or trained on NIST will be disqualified.  It is not freely available and its  license has restrictions on redistribution of itself or derivatives, including model weights.


---

### `[DATA_LEAK_SHIFT]` [745715] Visible test.parquet molecule_ids appear to leak class-1 answers (11 comments, `Signal: 12.0`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745715

> **Message 1 by User (2026-10-07)** [Votes: 4]:
> There is no overlap in IDs between train and test, or between dummy test and rerun test. It's a relatively low-observation test set, so participants should be careful that they don't interpret noise with causation.

> **Message 2 by User (2026-10-03)** [Votes: 22]:
> A public notebook (imranarif536/casmi26-v44-pairtail-locked-top1, V3, 0.417) hard-codes the 400 visible molecule_id → SMILES pairs (the structures of the train spectra copied into the dummy test file) and forces them to rank 1 for every row, unguarded; its previous version scored 0.402. That is only possible if (a) the hidden rerun reuses the visible molecule_ids and (b) for a substantial share of ids the dummy row's structure equals the hidden truth. Forks are spreading (two dozen teams at 0.416–0.418). Could you confirm whether molecule_ids are shared between the visible file and the hidden set, and shuffle/remap them before the final rerun? We are not using this and would prefer a level field.

> **Message 3 by User (2026-10-06)** [Votes: 2]:
> +1 from our team. We don't use the visible molecule_id to structure pairs in any form, neither in submissions nor for diagnostics, and we'd welcome a remap or shuffle of the molecule_ids before the final rerun (ideally with the visible placeholder built from structures outside the hidden set), so the final leaderboard reflects identification from the spectra alone. Thanks for raising this.

> **Message 4 by User (2026-10-03)** [Votes: 3]:
> Can the admin confirm if the shuffle/remap will be done? Above is accurate according to my test.


---

### `[RULES_COMPLIANCE]` [745072] Prize eligibility: code and weights shared in public Kaggle datasets with an "Other (non-commercial)" licence (16 comments, `Signal: 10.14`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/745072

> **Message 1 by User (2026-10-06)** [Votes: 1]:
> Looks like the organizers aren’t going to do anything about it.

> **Message 2 by User (2026-10-04)** [Votes: 1]:
> Adding to the questions above: several of these datasets (for example ahmedberatozer/casmi26-v4b-models, casmi26-v2-pool and casmi26-fpnet-full1) contain code together with models and tables derived from train.parquet, which you have confirmed can be open-sourced (threads 742265 and 743236).
> 
> If an author publicly relicenses such a dataset under MIT, Apache-2.0 or CC0, can it then be used in a prize-eligible solution?
> For assets that keep a non-commercial licence: does using them only forfeit prize eligibility, or can it also affect leaderboard placement and medals?
> 
> Thank you!

> **Message 3 by User (2026-10-02)** [Votes: 6]:
> Hi David and the Enveda team,
> 
> Many public notebooks in this competition run inference code and model weights stored in public Kaggle datasets. Examples are ahmedberatozer/casmi26-v4b-models, 
>   -fpnet-full1, -v2-pool, -v3-models, -iceberg and -glacier. Their licence field is "Other". The v4b-models description says the assets are for use "under the 
>   (respective) source licenses (non-commercial, with attribution)", because they are derived from the competition training data (CC BY-NC) and COCONUT (CC BY 4.0). The 
>   training scripts for the weights are not published.
> 
> We have two questions about prize-eligible solutions:
> 
> Does Foundational Rule 6.b (Public Code Sharing) also cover code that was shared publicly for this competition inside Kaggle datasets? That rule says shared code is 
> deemed licensed under an OSI-approved licence that does not limit commercial use. If it does, a winning solution could include that code and deliver it under the MIT 
> winner licence.
> 
> Under rule 2.5.3, can a winning solution use those published pretrained weights as they are? We would deliver our own training and inference code plus references to 
> the public datasets, even though the code used to train the weights is not public.
> 
> A short answer would help the many teams building on the public notebooks. Thank you!

> **Message 4 by User (2026-10-02)** [Votes: 1]:
> Hi David, a follow-up on the question above. Several public notebooks use ahmedberatozer/casmi26-v4b-models, -v3-models, -fpnet-full1 and -v2-pool. As far as we can tell they contain models and candidate pools trained or built only on train.parquet and COCONUT (CC BY 4.0), but their description says "non-commercial, with attribution", which seems inherited from the competition data's CC BY-NC licence. Given your earlier answer that models trained on train.parquet are fine for solutions, could you confirm these datasets are acceptable in a prize-eligible solution? Thanks.


---

### `[BUG_ALERT]` [740671] How to get started + Competition's Official Discord (18 comments, `Signal: 3.64`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/740671

> **Message 1 by User (2026-09-10)** [Votes: 4]:
> Welcome! 
> 
> Information for newbies
> New to machine learning and data science? No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!
> 
> New to Kaggle? Take a look at a few videos to learn a bit more about site etiquette, Kaggle lingo, and how to enter a competition using Kaggle Notebooks. Publish and share your models on Kaggle Models!
> 
> Participants under 18 years old: If you are under 18 years old and want to participate in this competition, you need to submit a couple of forms:
> 
> Form #1: Parent/Guardian consent for minor's use of kaggle.com. You only have to fill this out once, and it is valid for any competitions on Kaggle. If you already filled this out in the past, you can move on to the next form. 
> Form #2: Parent/Guardian consent for minor's participation in Kaggle competition. You have to fill out form #2 for this and any future competitions you want to join. 
> Kids under 13 years of age are not allowed to participate on Kaggle. If you have any questions, please leave a comment and we'll follow up with you!
> 
> Looking for a team? Express your interest in joining a team through our Team Up feature.
> 
> Remember: Kaggle is for everyone. Whether you're teaming up or sharing tips in the competition forum, we expect everyone to follow our Kaggle community guidelines.
> 
> Competition's Official Discord
> In addition to this competition forum, you can continue the discussion in our official Kaggle Discord Server here:
> 
> discord.gg/kaggle
> The Discord is a great place to ask getting started questions, chat about the nuances of this competition, and connect with potential team mates. Learn more about Discord at our announcement here. Here are a few things to keep in mind though:
> 
> 1. Discord Competition Channels are 'Public' - Don't Share Private Information
> 
> Discord channels for specific competitions are considered 'public' spaces where you are allowed to talk about competition details. Please remember that private sharing of competition code or data outside of your team is, as always, not permitted. Code sharing must always be done publicly through the Kaggle forums/notebooks.
> 
> 2. Discord Competition Channels are Not Monitored by Staff - Keep Important Information on the Kaggle Forums
> 
> Kaggle Staff and Hosts running competitions will not monitor Discord or be available to answer questions in Discord. This is intended to be a more casual space to discuss competitions and help each other. Please keep important questions, insights, writeups, and other valuable conversation on the Kaggle forums. 
> 
> Happy modeling!

> **Message 2 by User (2026-10-09)** [Votes: 0]:
> please who can help me with the reson why code has been saying submission error for like 4 submissions now? Thank you very much

> **Message 3 by User (2026-10-03)** [Votes: 0]:
> Looking to form or join a team for CASMI 2026 - need two more people.
> 
> Where I'm at: I've completed a thorough EDA pass on the training data molecule-level train/validation splitting (to avoid spectra from the same structure leaking across both sets), rebalancing the heavy spectra-per-molecule skew, checking precursor mass and adduct coverage against the test set's documented ranges, and isolating a systematic adduct-mislabeling bug that was corrupting ~40k rows (traced to an adduct-standardization error, fixed rather than discarded). Background: final-year Biochemistry student, currently a Machine Learning Engineering intern, comfortable in Python and ML fundamentals, with real domain chemistry knowledge to bring to structure elucidation. Worth noting this is my first Kaggle competition specifically, though not my first serious ML project.
> 
> What I need: two teammates who'll engage seriously and contribute real work I'm not filtering by experience level, just looking for genuine commitment. Complementary skills that would help a lot: cheminformatics/RDKit experience, deep learning or generative modeling (spectrum-to-structure especially), or bandwidth to help split up retrieval-baseline and modeling work.
> 
> Comment or DM if you're interested, or if you've got a team with a spot open.
> 
> — Amirah

> **Message 4 by User (2026-10-01)** [Votes: 0]:
> please what is the route to Concatenate key spectral metadata as tabular features: precursor_mz, ionization_mode, adduct (one-hot encoded), collision_energy_ev, and instrument_type.


---

### `[GENERAL_DISCUSSION]` [742186] Looking for teammates/ Chemistry & ML Background. I am a graduate of Pure and Industrial Chemistry that has 5 months of ML experience. I seek people who are very good at feature engineering, data analysis and chemistry. (22 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/742186

> **Message 1 by User (2026-09-24)** [Votes: 1]:
> I work in bio/protein ML and would like to collab: https://www.linkedin.com/in/zachary-cohen-220a96343/

> **Message 2 by User (2026-09-20)** [Votes: 1]:
> Please who has a good idea of what the competition entails?

> **Message 3 by User (2026-09-22)** [Votes: 0]:
> I'm doing my Bsc Mining Engineering and have done some Machine learning projects from Thrive Africa. you can see one of them in the link https://github.com/kwabenantiamoahlarbi-art/smart-crop-advisor. I'd like to join your group.

> **Message 4 by User (2026-09-22)** [Votes: 0]:
> I would like to join your team. I’m David, bsc in soil and environmental management, Msc in Computer Engineering, Msc in Soil science. I’m a research Data scientist. Currently working on a lot of ML model. Hit me up if needed.


---

## Competition: `nfl-big-data-bowl-2027`

### `[METRIC_NUANCE]` [747086] Clarification on private cloud and AI-assisted data processing (2 comments, `Signal: 5.65`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/747086

> **Message 1 by User (2026-10-08)** [Votes: 0]:
> A private cloud workspace and an AI coding assistant are both fine. External tools and models, LLMs included, are allowed under General Rules §2.6, as long as they're reasonably accessible and low cost.

> **Message 2 by User (2026-10-08)** [Votes: 0]:
> I’ve joined personally and want to use a private cloud workspace with an AI coding assistant. What conditions apply to raw-data processing, retention, model training and provider access under §2.4? If the raw data stays in Kaggle, may an external assistant receive samples or analytical outputs, or should it only help with code?


---

### `[METRIC_NUANCE]` [747584] Dataset Row Count Discrepancies Between Data Description and Downloaded CSV Files (2 comments, `Signal: 5.03`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/747584

> **Message 1 by User (2026-10-09)** [Votes: 1]:
> Hello NFL Big Data Bowl 2027 organizers,
> 
> I noticed some discrepancies between the row counts listed in the competition's Data page and the actual CSV files provided in the downloadable dataset.
> 
> Here is a comparison:
> 
> File
> Rows Listed on Data Page
> Actual CSV Rows
> 
> player_play.csv
> 316,338
> 314,197
> 
> game_tracking_2023.csv
> 1,421,805
> 3,665,443
> 
> game_tracking_2024.csv
> 3,042,118
> 7,827,944
> 
> game_tracking_2025.csv
> 4,339,021
> 11,160,903
> 
> To verify these differences, I:
> 
> Downloaded the competition dataset twice from Kaggle.
> Confirmed that both downloaded ZIP archives are identical using SHA256.
> Confirmed that all nine CSV files in my working directory match the downloaded archives byte-for-byte.
> Independently counted CSV records using both Pandas and Python's standard-library csv.reader, excluding header rows.
> 
> Both counting methods produced the same results, and the discrepancies remained.
> 
> Interestingly, the file sizes of the three game_tracking CSV files appear consistent with those listed on the Data page, despite the substantial differences in row counts.
> 
> Could you please clarify:
> 
> Are the row counts on the Data page based on a different dataset version or filtering convention?
> Are the CSV files currently available for download the intended files for this competition?
> Should participants use the actual CSV records as provided, or is there an additional preprocessing or filtering step expected before analysis?
> 
> I want to ensure that my analysis is based on the correct dataset and follows the intended data definitions.
> 
> Thank you very much for your time and clarification!

> **Message 2 by User (2026-10-09)** [Votes: 0]:
> Hello organizers, I independently reproduced the exact CSV row counts reported above. I also checked bidirectional linkage between the three game_tracking files and player_play.csv using the composite key (game_id, play_id, nfl_id), after collapsing tracking frames to unique player-play keys.
> 
> Tracking keys without a matching player_play record: 2023: 449; 2024: 857; 2025: 1,191; total: 2,497. Conversely, player_play records without tracking: 293, 661 and 796 respectively; total: 1,750.
> 
> The 2,497 unmatched tracking keys are concentrated in roster positions WR (1,760), TE (721) and FB (16). They include 2,233 REG, 79 POST and 185 PRE keys. For 2,288 of them, player_play contains another player on the same game/play; for 209, the entire game/play pair is absent. No null or duplicate tracking composite keys, orphan player IDs or orphan game IDs were found.
> 
> Could you please clarify whether these are intended player-level or play-level exclusions, and whether a corrected player_play.csv or source-version/filtering notice is available? In particular, should analyses using receiver context retain these as missing, or is there an official eligibility/filter rule? We have preserved the exceptions and have not imputed missing context. Thank you.


---

### `[METRIC_NUANCE]` [746678] Pass-rush opportunities and missing metric values (3 comments, `Signal: 4.08`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/746678

> **Message 1 by User (2026-10-07)** [Votes: 1]:
> Hello,
> 
> Thanks for the question. I agree it can be confusing.
> 
> When quick pressure or time to pressure is NA and blitz is TRUE, that means there was no pressure.
> 
> When quick pressure is false, that means a pressure occurred but it cannot be described as "quick".
> 
> player_get_off is NA if the player never crosses the line of scrimmage (although this is very rare).
> 
> Does that answer your questions?

> **Message 2 by User (2026-10-07)** [Votes: 0]:
> For player_play, which fields identify every pass-rush opportunity, including ordinary non-blitz rushes that produce no pressure? The dictionary defines blitzing for blitz participation and quick_pressure = 1.0 for pressure within 2.50 seconds, but does not specify whether quick_pressure = 0 means an observed non-event or what null means. On an eligible rush, can null distinguish a non-rush from an unobserved outcome? Also, is player_get_off recorded for every eligible rusher, and how are rushers who never cross the line of scrimmage represented? Clarifying these definitions would help avoid conditioning the denominator on successful or observed outcomes. Thank you.


---

### `[GENERAL_DISCUSSION]` [746521] What about NFL Big Data Bowl 2027 - Prediction (1 comments, `Signal: 3.24`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/746521

> **Message 1 by User (2026-10-07)** [Votes: 2]:
> There are no plans to launch a prediction competition this year.

> **Message 2 by User (2026-10-07)** [Votes: 2]:
> @tombliss, Is there any possibility that a prediction competition will be launched this year?


---

### `[METRIC_NUANCE]` [746995] Ask for joining a Team (5 comments, `Signal: 2.88`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/746995

> **Message 1 by User (2026-10-08)** [Votes: 2]:
> Hi, anyone who need a data science for your team, inviting me please.
> 
> Background: I got bechelor degree of computer science, and master of operating system structure and master of AI in University of Auckland. 
> 
> Experience: Worked at Softbank Robotics for 7 years, and Currently being a Business Analytics Consultant. 
> 
> Thanks

> **Message 2 by User (2026-10-09)** [Votes: 0]:
> Hi everyone! 😊 I'm looking for a team to join for this competition. I'm interested in data analytics and machine learning, and I'm excited to learn, contribute, and work with others on this challenge. I'm still growing my skills, so if your team is open to collaborating and learning together, I'd love to connect! 🏈📊

> **Message 3 by User (2026-10-09)** [Votes: 0]:
> What about the four of us?  I love football and analytics but have only recently take a liking to it and have a very basic understanding.  Would love to do the best I can and learn more with some experienced people

> **Message 4 by User (2026-10-08)** [Votes: 0]:
> Recent CS grad, worked as software developer for 8 months, did ML specialization of Andrew Ng, if suitable you can mail me at mustafaraza6372@gmail.com


---

### `[DATA_LEAK_SHIFT]` [747108] combine_tracking.csv: nfl_id on BALL frames — are we reading this correctly? (plus two small notes) (2 comments, `Signal: 1.65`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/747108

> **Message 1 by User (2026-10-08)** [Votes: 1]:
> Hello,
> 
> Thanks for the question on the combine tracking data -- the data dictionary was incorrect so we updated it. When the entity type is ball, the nfl_id represent the corresponding player in given event_id.
> 
> With respect to players without an in-game record, the 13 players who do not have in-game record did not ever make it to the field. You could use this information to as part of your analysis (i.e. perhaps their combine performance led to them never receiving the opportunity) or focus on those who do have on field plays.
> 
> Following up on the question about NA values, those are plays where a penalty occurs to kill the play before it starts. Unfortunately, we do not have a value for lined_up_position for those plays.

> **Message 2 by User (2026-10-09)** [Votes: 0]:
> Thank you for the clarification. One additional completeness check may help participants defining the sample as the 497 players with in-game records.
> 
> Our audit of the supplied files, collapsing game tracking to unique (game_id, play_id, nfl_id) keys before joining, found 2,497 tracking player-play keys without a matching player_play record (2023: 449; 2024: 857; 2025: 1,191). Conversely, 1,750 player_play records have no matching tracking key. The unmatched tracking keys are concentrated in WR (1,760), TE (721) and FB (16); 2,233 are regular-season keys. These counts describe linkage exceptions, not duplicate tracking frames or additional players.
> 
> A practical safeguard is to audit both sides of the join, retain unmatched keys in an exception table, and report coverage for the actual analytical cohort before filtering to complete cases. Restricting to players with at least one in-game record does not, by itself, establish complete player-play context. We are preserving the missing context rather than imputing it while awaiting the organizers' explanation.
> 
> The detailed findings and question are already posted in the row-count discussion: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/747584
> 
> This is a linkage safeguard, not a correction to the source data or a claim that the exclusions are erroneous.

> **Message 3 by User (2026-10-08)** [Votes: 0]:
> Hi organizers,
> 
> The Data tab describes nfl_id in combine_tracking.csv as "int64 / null" with the note "Null for
> BALL tracking frames." When we read the competition data as distributed, we get something we do
> not fully understand, and we would like to confirm the intended semantics before we lock our
> feature pipeline.
> 
> What we observe (verified twice: once in a Kaggle notebook with pandas, and once with a plain
> Python stdlib CSV parser over the downloaded files):
> 
> Across all 463,189 rows of combine_tracking.csv, nfl_id is never null — for PLAYER rows and
> for BALL rows alike (0 null rows in the whole file).
> Of the 6,310 drill attempts, 551 contain BALL frames, and those frames appear only in
> SKILL_DRILLS_WR and SKILL_DRILLS_TE.
> In all 551 of those events, the BALL frames carry exactly one nfl_id, and it is identical to
> the nfl_id on the PLAYER frames of the same event.
> That leaves 54 players with any ball tracking at all (37 WR, 16 TE, 1 FB), so we are treating
> ball tracking as a secondary/appendix analysis rather than the core of our submission.
> 
> Our questions:
>   (a) Is the intended reading that a BALL row is attributed to the athlete performing that drill?
>   (b) Is ball tracking expected to remain limited to these 54 players, or is broader ball
>       coverage available somewhere we have not looked?
> 
> Two smaller notes, in case they are useful to other participants:
> 
> player_play.csv contains 314,197 rows in the distributed files, and covers 497 of the 510
>  players and 1,001 of the 1,002 games (the file catalog describes 316,338 rows). We are
>  defining our sample as the 497 players with in-game records and will state this explicitly
>  in the writeup — is that the intended interpretation?
> lined_up_position uses the literal string "NA" for "not applicable" (1,383 rows), which most
>  pandas pipelines silently convert to a missing value. Just flagging it.
> 
> Thank you!


---

### `[GENERAL_DISCUSSION]` [748114] Reference Point for player_get_off (1 comments, `Signal: 1.04`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/748114

> **Message 1 by User (2026-10-11)** [Votes: 0]:
> It is based off the ball location at snap. This information is not provided in the competition.

> **Message 2 by User (2026-10-10)** [Votes: 0]:
> What reference point does player_get_off use for the line of scrimmage, and is the ball’s position available anywhere in the tracking?


---

### `[RULES_COMPLIANCE]` [746316] How to Get Started + Competition's Official Discord (5 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/746316

> **Message 1 by User (2026-10-08)** [Votes: 2]:
> Hi, I need help. I gave Kaggle access to Discord. After authorisation, it gave me an error message: "Invalid field 'iss'"

> **Message 2 by User (2026-10-06)** [Votes: 9]:
> Information for First Timers
> New to machine learning and data science? No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!
> 
> New to Kaggle? Take a look at a few videos to learn a bit more about site etiquette, Kaggle lingo, and how to enter a competition using Kaggle Notebooks. Publish and share your models on Kaggle Models!
> 
> Looking for a Team? Express your interest in joining a team through our Team Up feature.
> 
> Remember: Kaggle is for everyone. Whether you're teaming up or sharing tips in the competition forum, we expect everyone to follow our Kaggle community guidelines.
> 
> Competition's Official Discord
> In addition to this competition forum, you can continue the discussion in our official Kaggle Discord Server here:
> 
> discord.gg/kaggle
> The Discord is a great place to ask getting started questions, chat about the nuances of this competition, and connect with potential team mates. Learn more about Discord at our announcement here. Here are a few things to keep in mind though:
> 
> 1. Discord Competition Channels are 'Public' - Don't Share Private Information
> 
> Discord channels for specific competitions are considered 'public' spaces where you are allowed to talk about competition details. Please remember that private sharing of competition code or data outside of your team is, as always, not permitted. Code sharing must always be done publicly through the Kaggle forums/notebooks.
> 
> 2. Discord Competition Channels are Not Monitored by Staff - Keep Important Information on the Kaggle Forums
> 
> Kaggle Staff and Hosts running competitions will not monitor Discord or be available to answer questions in Discord. This is intended to be a more casual space to discuss competitions and help each other. Please keep important questions, insights, writeups, and other valuable conversation on the Kaggle forums. 
> 
> Happy modeling!

> **Message 3 by User (2026-10-09)** [Votes: 0]:
> A small pandas example can keep the two linkage levels separate. Combine athletes link to players on nfl_id; game tracking links to player_play on (game_id, play_id, nfl_id). BALL rows carry the associated athlete's nfl_id, as Tom clarified in discussion/747108, so filter entity_type == "PLAYER" before calculating athlete movement.
> 
> import pandas as pd
> 
> def linkage_checks(combine_tracking, players, game_tracking, player_play):
>     athlete_ids = (
>         combine_tracking.loc[combine_tracking["entity_type"].eq("PLAYER"), ["nfl_id"]]
>         .drop_duplicates()
>     )
>     athlete_link = athlete_ids.merge(
>         players, on="nfl_id", how="left", validate="one_to_one", indicator=True
>     )
>     keys = ["game_id", "play_id", "nfl_id"]
>     if game_tracking[keys].isna().any().any():
>         raise ValueError("Null game-tracking join key: review before merging")
>     if player_play[keys].isna().any().any():
>         raise ValueError("Null player_play join key: review before merging")
>     if player_play.duplicated(keys).any():
>         raise ValueError("Duplicate player_play key: review before merging")
>     tracking_keys = game_tracking[keys].drop_duplicates()
>     play_link = tracking_keys.merge(
>         player_play[keys], on=keys, how="outer",
>         validate="one_to_one", indicator=True
>     )
>     return athlete_link, play_link
> 
> # Load identifiers with consistent dtypes across files.
> # _merge: both = linked; left_only = tracking without context;
> # right_only = context without tracking.
> 
> Keep unmatched records visible rather than silently dropping them or filling missing context with zero. Our independent join audit is posted in discussion/747584. Tom's clarification in discussion/747108 also distinguishes the 13 prospects who never reached the field from missing player-play context for an observed tracking record. Those represent different research questions.
> 
> The helper above was checked with synthetic matched/unmatched records, repeated tracking frames, BALL frames and invalid keys; this is a linkage illustration, not a new audit of the competition files.

> **Message 4 by User (2026-10-08)** [Votes: 0]:
> Hello,
> 
> I would like to confirm my eligibility for the NFL Big Data Bowl 2027 University Track.
> 
> I am 23 years old and currently enrolled as an engineering student at City University in Lebanon.
> 
> I am completing a five-year engineering program, which follows the Lebanese higher education system. I am currently in my final semester and expect to graduate in June 2027.
> 
> I would like to participate individually in the University Track.
> 
> Could you please confirm:
> 
> Am I eligible to participate in the University Track as a student enrolled at a university in Lebanon?
> Does my five-year engineering program meet the undergraduate or graduate student requirement?
> Am I eligible to receive cash prizes if selected as a finalist or winner?
> Would I need to provide proof of university enrollment?
> 
> Thank you for your time and clarification.
> 
> Best regards.


---

### `[SOTA_RECIPE]` [748104] Beyond 40-Yards: 10Hz Acceleration & Longevity (0 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/discussion/748104

> **Message 1 by User (2026-10-10)** [Votes: 0]:
> I just published my Notebook for the NFL Big Data Bowl 2027: Beyond 40-Yards: 10Hz Acceleration & Longevity.
> 
> Key Takeaways:
> 
> Simpson's Paradox: Proved that combine tracking data must be segmented by position to reveal true signals.
> 
> Kinematic Signals vs. Chronometers: Peak acceleration in drill-specific tracking data (like pass-rush drops and lateral wave drills) is a much stronger predictor of NFL career longevity (total_snaps) than traditional 40-yard dash times.
> 
> Model: Improved baseline validation RMSE from 799.55 to 649.94 using LightGBM with native NaN handling for drill-specific features.
> 
> Check it out and let me know your thoughts! Upvotes and feedback are greatly appreciated! 🏈


---

## Competition: `gemma-4-developer-agent`

### `[METRIC_NUANCE]` [742807] Clarification on distillation from external LLMs (11 comments, `Signal: 17.43`)
**URL**: https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/742807

> **Message 1 by User (2026-09-29)** [Votes: 6]:
> Hello and thank you for your question and your patience. As long as you are using those models in accordance with their model license terms, and the output you're using to submit to that competition doesn't 'conflict with the license requirement of the rules of this competition, you may use them.

> **Message 2 by User (2026-09-23)** [Votes: 46]:
> Hi organizers,
> 
> My understanding is that using external LLM APIs to generate synthetic training data has generally been allowed in recent Kaggle competitions. Given Section 2.6, I would expect this to be permitted here as well, subject to the competition’s external data and model requirements.
> 
> Could you clarify whether participants may use proprietary models, such as OpenAI Astra or Claude Opus 5.5, to generate code patches and agent trajectories for training Gemma specifically for this competition?
> 
> Regarding provider restrictions on developing competing models, my current understanding is that training a model solely for this competition may be permissible, while deploying or using the resulting model outside the competition could raise separate concerns. I recognize that participants remain responsible for complying with their providers’ terms.
> 
> With that distinction in mind, could you clarify:
> 
> Does the competition allow this form of distillation from proprietary API models? Are there any restrictions on which teacher models may be used?
> Are there different requirements for proprietary API teachers versus open-weight teachers?
> How would a model intended solely for competition use fit with the winner licensing and release requirements under Sections 2.5 and 2.8? In particular, would winners need to release the trained weights or adapters for unrestricted use outside the competition?
> 
> Examples of acceptable teacher models would be very helpful.
> 
> Thank you!

> **Message 3 by User (2026-09-24)** [Votes: 6]:
> Hi @cnumber,
> 
> We are confering and will have an answer for you soon.

> **Message 4 by User (2026-09-25)** [Votes: 1]:
> I'm looking at using distillation methods for open source models as well. I'm not against open sourcing my training data results from the distillation process as I have a tool that does this for Gemma 4 already developed. I'm curious what they decide on here!
> 
> Edit: Here is my KD tool which I'll be updating for this competition Ghostwriter


---

### `[BUG_ALERT]` [747519] Update on "Kaggle Error" Submissions & Queue Delays (53 comments, `Signal: 16.65`)
**URL**: https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/747519

> **Message 1 by User (2026-10-11)** [Votes: -1]:
> Unfortunately, this issue has also prevented me from submitting another notebook the following day, causing me to lose valuable competition time and submission opportunities.

> **Message 2 by User (2026-10-11)** [Votes: -1]:
> Hi Team! My previous submission has been running for more than 24 hours, which is preventing me from making any new submissions. Could you please look into this and help resolve it?

> **Message 3 by User (2026-10-11)** [Votes: -2]:
> Hi team!
> I’ve run into a technical hiccup. My notebook has been running for over 12+ hrs, and it’s blocking my submission, and since I already have an updated version ready, I can’t submit it until this is resolved. Could you please help?
> Thanks so much.

> **Message 4 by User (2026-10-10)** [Votes: 4]:
> The current queue delay is around ~33h, so yes, your submission isn't stuck, its making its way towards the front of a long line of submissions. If its been >33h, its likely running right now and your score will arrive once it finishes, scores have continued to work its just incredibly high demand and finite supply.
> 
> Thanks for your patience everyone, we will continue to do what we can.

> **Message 5 by User (2026-10-08)** [Votes: 27]:
> Hi everyone,
> 
> I wanted to give an update on the long submission wait times and "Kaggle Error" failures many of you have been seeing over the past couple of days.
> 
> What Happened
> Due to very high submission volume using L4s, submission jobs have been facing long queue times before actually getting a machine to run. Submissions that waited >15h to start were being marked as “Kaggle Error” even if they eventually did run.
> 
> What We Fixed
> 
> Extended Queue Timeout: We've drastically extended the queue allowance so submissions will no longer be timed out while waiting to run.  
> Scoring Submissions that had Queue Timeouts: We are actively reprocessing all affected submissions from the past few days. If your notebook ran to completion and produced a valid submission file, it is being scored and published to the leaderboard automatically. You should already see scores showing up on the leaderboard now.  
> Queue Wait Times: to even some of the load on the pool, we are implementing a pending submission limit (separate from the 1/day limit). If your team's previous submission is still scoring, you will need to wait until it finishes to submit again.
> 
> What This Means for You
> 
> No action needed: You do not need to resubmit or contact support to recover an affected run; our batch recovery is processing them directly.  
> Monitor this post for updates
> 
> Thanks for your patience while we sort this out, and sorry for the frustration it caused over the last few days.


---

### `[GENERAL_DISCUSSION]` [748287] New Gemma 4 Models Available: 12B, E4B, and E2B (12 comments, `Signal: 13.39`)
**URL**: https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/748287

> **Message 1 by User (2026-10-11)** [Votes: 15]:
> Hi everyone,
> 
> We've added support for several smaller Gemma 4 variants. You can now use any of the following models for your agents:
> 
> gemma-4-31b-it-qat-w4a16-ct
> gemma-4-12b-it-qat-w4a16-ct
> gemma-4-e4b-it-qat-w4a16-ct
> gemma-4-e2b-it-qat-w4a16-ct
> 
> We don't support mixing variants within a submission, however. Every agent and subagent in your submission must use the same variant (though they can attach different LoRA adapters.)
> 
> These smaller models open up some new strategies:
> 
> More test time compute: Inference is faster and memory burden lower so you can execute more and longer reasoning turns and iteration cycles. You could also experiment with using ParallelAgent for concurrent LLM calls (though tool calls are still executed sequentially).
> Faster and more accessible LoRA finetuning: Experiment with different setups more quickly and on more accessible GPUs. We provide L4x4s for use in interactive notebooks, but adapters can now be finetuned on a wider variety of consumer hardware.
> More specialized agents: Smaller models use smaller LoRA adapters, so you can include more of them in your submission.
> 
> We're excited to see what you build!

> **Message 2 by User (2026-10-11)** [Votes: 2]:
> Hi, here is a well-known issue, already fixed on v2.** upstream, but as we are using still v1.36  . Parallel agent is not gonna work : https://github.com/google/adk-python/issues/7324#issuecomment-5868428151

> **Message 3 by User (2026-10-11)** [Votes: 0]:
> thx appreciate the options this opens.

> **Message 4 by User (2026-10-11)** [Votes: 0]:
> @ryanholbrook  One question about timing: is the scorer's vLLM server configured exactly like the Getting Started notebook (tensor_parallel_size=4, max_model_len=32768, gpu_memory_utilization, prefix caching and any max_num_seqs settings), for every variant?


---

### `[BUG_ALERT]` [743683] Rerunning Failed Submissions (93 comments, `Signal: 13.0`)
**URL**: https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743683

> **Message 1 by User (2026-10-11)** [Votes: -1]:
> what to do please? my submission is scoring for 48h? i cant submit until this is resolved

> **Message 2 by User (2026-10-11)** [Votes: -1]:
> Hi. Can you please take a look at my submission. It is running for 2 days already. Thanks

> **Message 3 by User (2026-10-11)** [Votes: -1]:
> Hi, my S4 submission has remained at “Notebook Running” for approximately two days. It was submitted on October 9 and uses the single-agent shell repair loop. The submission details still show no score or more specific execution status.
> 
> Could you please confirm whether this is waiting for L4x4 resources, actively executing, or stalled during evaluation? If it is stuck because of the current queueing issue, is a rerun possible?
> 
> I have not submitted a duplicate. Thank you.

> **Message 4 by User (2026-10-10)** [Votes: -1]:
> My submission is running for 14hours +

> **Message 5 by User (2026-09-26)** [Votes: 21]:
> Hi everyone,
> 
> Some submissions since yesterday were failing with "Your notebook has requested more CPU, GPU or TPU resources than are available." I believe I've resolved the issue, though please let me know if you're still having issues. I will rerun the affected submissions on Monday so that you won't be losing a submission.


---

### `[GENERAL_DISCUSSION]` [743007] Welcome to the Gemma 4 Developer Agent Competition (9 comments, `Signal: 8.42`)
**URL**: https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743007

> **Message 1 by User (2026-09-24)** [Votes: 11]:
> Hello Kagglers,
> 
> Today’s most capable software engineering agents rely on massive, closed-source models running in the cloud, leaving advanced autonomous development tools out of reach for many developers.
> 
> With Gemma 4, we want to change that.
> 
> Our challenge to you is to push the boundaries of open-source models and post-train Gemma 4 into an autonomous coding agent capable of navigating real-world repositories and reliably resolving software engineering tasks on consumer-grade hardware. To help you get started, we’ve provided a starter submission, development tasks, and a corresponding dataset of structured code graphs with pre-computed embeddings for repository-level retrieval.
> 
> Whether you explore parameter-efficient fine-tuning, novel reinforcement learning approaches, or graph-based code reasoning, we want to see how far you can take local, open models. 
> 
> We can't wait to see the agents you build and the solutions you invent!
> 
> Google Research and The Gemma Team

> **Message 2 by User (2026-09-28)** [Votes: 1]:
> L4 ×4 session is queued for very long time.

> **Message 3 by User (2026-10-06)** [Votes: 0]:
> Excited to participate in this challenge! We've been experimenting with an AST-based semantic skeletonization pipeline to overcome the 32k context bottleneck on massive SWE-bench repositories
> (compressing structural token footprints by ~95% while preserving full class hierarchies and function
> signatures).
> Combining this with a 3-agent hierarchical triad (Scout, Synthesizer, Sandbox Verifier) running across 4x NVIDIA L4 GPUs via vLLM has shown great promise for surgical unified diff patches. Looking forward to
> learning from the community's approaches! Best of luck to everyone.

> **Message 4 by User (2026-10-05)** [Votes: 0]:
> here i have a doubt that can we make agents work in parallel to solve tasks so we can increase time for solving each task and eval_config.yaml has no concurrency key so we can implement it as we what or you will decide it


---

### `[RULES_COMPLIANCE]` [745998] Note on Code Graphs for Async Functions (0 comments, `Signal: 4.16`)
**URL**: https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/745998

> **Message 1 by User (2026-10-05)** [Votes: 7]:
> There have been a number of discussion posts pointing out that async def functions are not included in the code graph tools. This is true and is an issue for some of the public tasks in fastapi and httpx. 
> 
> However, it is not an issue for any of the private repo tasks. 
> 
> None of the private repo tasks touch any functions defined with async def. Additionally, async def functions are rare within the private repos as a whole, at most 1.8% of functions. 
> 
> As a result, we will not be doing an update to the private tasks' code graphs.


---

### `[GENERAL_DISCUSSION]` [742815] How to get started + Competition's Official Discord (2 comments, `Signal: 0.0`)
**URL**: https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/742815

> **Message 1 by User (2026-10-04)** [Votes: 1]:
> Please review this discussion https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/745775

> **Message 2 by User (2026-09-23)** [Votes: 6]:
> Information for newbies
> Welcome! 
> New to machine learning and data science? No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!
> 
> New to Kaggle? Take a look at a few videos to learn a bit more about site etiquette, Kaggle lingo, and how to enter a competition using Kaggle Notebooks. Publish and share your models on Kaggle Models!
> 
> Participants under 18 years old: If you are under 18 years old and want to participate in this competition, you need to submit a couple of forms:
> 
> Form #1: Parent/Guardian consent for minor's use of kaggle.com. You only have to fill this out once, and it is valid for any competitions on Kaggle. If you already filled this out in the past, you can move on to the next form. 
> Form #2: Parent/Guardian consent for minor's participation in Kaggle competition. You have to fill out form #2 for this and any future competitions you want to join. 
> Kids under 13 years of age are not allowed to participate on Kaggle. If you have any questions, please leave a comment and we'll follow up with you!
> 
> Looking for a team? Express your interest in joining a team through our Team Up feature.
> 
> Remember: Kaggle is for everyone. Whether you're teaming up or sharing tips in the competition forum, we expect everyone to follow our Kaggle community guidelines.
> 
> Competition's Official Discord
> In addition to this competition forum, you can continue the discussion in our official Kaggle Discord Server here:
> 
> discord.gg/kaggle
> The Discord is a great place to ask getting started questions, chat about the nuances of this competition, and connect with potential team mates. Learn more about Discord at our announcement here. Here are a few things to keep in mind though:
> 
> 1. Discord Competition Channels are 'Public' - Don't Share Private Information
> 
> Discord channels for specific competitions are considered 'public' spaces where you are allowed to talk about competition details. Please remember that private sharing of competition code or data outside of your team is, as always, not permitted. Code sharing must always be done publicly through the Kaggle forums/notebooks.
> 
> 2. Discord Competition Channels are Not Monitored by Staff - Keep Important Information on the Kaggle Forums
> 
> Kaggle Staff and Hosts running competitions will not monitor Discord or be available to answer questions in Discord. This is intended to be a more casual space to discuss competitions and help each other. Please keep important questions, insights, writeups, and other valuable conversation on the Kaggle forums. 
> 
> Happy modeling!

> **Message 3 by User (2026-09-28)** [Votes: 0]:
> I get invalid invite error in discord, is it a problem in my side or others have the same problem as well?


---
