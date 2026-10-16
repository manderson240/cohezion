# Kaggle Active Competitions Discussion Intelligence Synthesis
**Generated**: 2026-10-16 22:36:04 UTC
**Principle**: Quality Over Quantity — Deep Domain Invariant Extraction

---

## 🏆 RSNA Knee Abnormality Detection (`rsna-knee-abnormality-detection`)
**Domain**: Medical Imaging / 3D MRI / Radiomics
**Topics Mined**: 10 highest-impact discussions

### [#748181] Kaggle could we please start doing something about the public notebooks? 
*Votes: 122 | Comments: 62 | Date: 2026-10-11*

**Key Findings & Context:**
> Yet again, we have another competition where low-effort public ensembles are being released with less than two weeks remaining, potentially allowing participants to secure medals through copy-paste submissions rather than their own work or understanding.

I fully expect this to continue as the deadline approaches and based on the past year or more, I expect that Kaggle will do absolutely nothing to address it.

Personally, I expect to be fine. My concern is for the participants who may end up hundreds of places below where they otherwise would have finished, despite putting in significantly more work and developing their own solutions. I am equally concerned about those who have shared genuinely valuable notebooks and helped others learn, only to see that work receive little recognition because the current code-tier structure disproportionately rewards marginal leaderboard improvements, often effectively meaningless (or outright duplicates), driven by a random seed rather than a meaningful contribution.

What I find most frustrating is not simply that this problem persists, but that it continues despite repeated forum discussions and substantial community support highlighting the issue. **Why have we received so little meaningful explanation from Kaggle about why this remains unresolved, what trade-offs are preventing a solution, or whether there is any concrete plan to address it?**

No system will be perfect, and I recognize that solutions involve trade-offs. But leaving participants without meaningful explanation while the same concerns recur competition after competition is difficult to justify.

Kaggle should be a place where competitive performance, original work, and meaningful contributions are rewarded. Right now, the incentives are increasingly misaligned with those goals, and I would genuinely like to understand why.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+10): people posting high public notebook at the final leg of competition is ALWAYS the worst, it kills the soul of the competition :'(  with this speed i think soon we will see .960 notebook :p...
- **Community Member** (+6): With the advancement of coding agents, the current rules are no longer as appropriate as they used to be....
- **Community Member** (+8): With almost 100% code being generated with coding agents lately, are notebook medals still relevant [@cody11null](/cody11null)? I think Kaggle could simply scrap off datasets and kernels tiers and resort to competitions only, like older times. If anyone wishes to share code, he/ ...
- **Community Member** (+15): I think a better approach would be to freeze all notebook achievements as of a certain date. All achievements earned before that cutoff would be retained—medals, titles, the fancy GM profile frames—but no new notebook achievements would be added after that date. This change shoul...
- **Community Member** (+2): I saw a suggestion to add downvotes to notebooks -- but if that happens, bots will just end up downvoting every notebook LOL....

### [#735304] Best single-model score
*Votes: 82 | Comments: 141 | Date: 2026-08-14*

**Key Findings & Context:**
> What is the best score you’ve achieved with a single model?

I’m trying to train a strong single model first before moving on to ensembling, and I’m curious how far a single model can go.

I’ve noticed that most of the public solutions use ensembles of 20+ models and achieve around 0.91. For those scoring around 0.92–0.94 on the leaderboard, are you also using ensembles, or is it possible to reach that range with a single model?

For reference, my current best score is 0.887 with DINOv2.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+10): In my option - 9 days into a competition is a very silly time to be wasting efforts refining ensemble models....
- **Community Member** (+7): A single model actually works much better than you'd expect....
- **Community Member** (+5): Single model 0.915, DinoV2 based.   Highly doubt the top results are ensembles, look at the [efficiency lb](https://www.kaggle.com/code/ryanholbrook/rsna-knee-abnormalities-efficiency-lb), you can see many high scoring submissions also have decent run times, i.e. they're not runn...
- **Community Member** (+0): Single model 0.92 is impressive. Would you mind sharing the input geometry you landed on — resolution, physical crop in mm, and slices per series?  We're at 0.826 with 192px / 9 slices / 4 sequence slots and trying to work out whether our ceiling is the input pipeline or the mode...
- **Community Member** (+2): Sharing is quite revealing on my methods. What I can strongly suggest - look at the images your model sees. Does it look detailed enough? Do you think 192px is sufficient to see mm level details?   I find playing with the pipeline is crucial.  If I can it see the details, how cou...

### [#743416] Please clarify which external knee MRI datasets are allowed
*Votes: 97 | Comments: 41 | Date: 2026-09-26*

**Key Findings & Context:**
> Thank you to the hosts for organizing this challenge and for taking the time to answer questions throughout the competition. I appreciate that assessing third-party datasets individually is difficult, especially when their access requirements and licenses differ.

Questions about external knee MRI data are spread across several threads. Without a clear answer for commonly used datasets, teams may train under different assumptions about what is permitted, which makes it difficult to ensure a level playing field.

I have read the [original question](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/733652), the [registration-gated dataset question](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/735497), and the [institutional-agreement follow-up](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/737950). There are also separate questions about [pretrained weights](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/735121) and [research-use agreements](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/738111).

The host has [explicitly ruled that KneeCoT is not allowed](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/734109) because its formal institutional agreement may create unequal access. The host has also [explained](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/discussion/733965) that non-commercial terms alone do not exclude a dataset, while straightforward registration and substantial institutional approval may be treated differently. It remains unclear to me how these principles apply to the following resources:

Resource

Relevant access or licensing issue

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+7): This is quite pressing and could really throw off the leaderboard. I could be wrong, but it's only the winning solutions (top 10) that would be audited thoroughly enough that training on external data sources that are not allowed would even get "caught" and disqualified. Basicall...
- **Community Member** (+5): I couldn't agree more. I worry that detailed review may naturally focus on prize-eligible teams, while the effects of unclear external-data rules could extend across the entire leaderboard.  What particularly concerns me is that relevant external knee MRI data could allow even a ...
- **Community Member** (+2): This is really important. I have a similar question for the hosts. Can we use publicly released pretrained models (MIT license and all) that were trained on OAI-derived data?...
- **Community Member** (+3): 4 days and still no answer. is that a yes?...
- **Community Member** (+2): MRNet’s user agreement says we’re not allowed to modify, reverse engineer, decompile, or create derivative works from the dataset, so that might be an issue too....

### [#733343] Knee Abnormality Detection AI Challenge Overview
*Votes: 101 | Comments: 17 | Date: 2026-08-06*

**Key Findings & Context:**
> **Courtesy of Dr. Jacob Kazam**

### Overview of the Clinical Problem

The 2026 RSNA Knee Abnormality Detection AI Challenge asks participants to build machine learning models that detect a defined set of clinically important abnormalities on knee MRI examinations. It is the first RSNA AI Challenge to pair every imaging study with the text of its original radiology report, and to do so across a large, multilingual, international dataset. Models may learn from both the images and the report text, reflecting how knee MRI is actually interpreted and communicated in clinical practice.

The knee is one of the most frequently injured and most frequently imaged joints in the body. Knee disorders are a major and growing cause of pain and disability worldwide, affecting athletes, manual workers, and older adults alike. The knee is the most common site of osteoarthritis, which affects nearly a quarter of adults aged 40 and older, an estimated 654 million people worldwide. Acute injuries are also common: knee injuries account for an estimated 15 to 40 percent of all sports-related injuries.

Several structures are commonly involved. Anterior cruciate ligament (ACL) tears are among the most frequent sports injuries, often occurring during sudden pivots or changes of direction and leading to immediate instability. Medial collateral ligament (MCL) injuries typically result from outward (valgus) stress on the knee and frequently accompany other structural damage. Meniscal tears, which may be traumatic or degenerative, disrupt the joint’s shock absorption and mechanics, producing pain, locking, and functional limitation. Cartilage loss, joint effusion, synovitis, bone contusions, fractures, and Baker (popliteal) cysts are additional findings that cause symptoms and influence management.

MRI is central to evaluating the knee because it depicts all of these structures, including ligaments, menisci, articular cartilage, and bone, without ionizing radiation, providing a comprehensive whole-joint assessment that other modalities cannot match. However, MRI interpretation varies across readers and practice settings, and access to subspecialty-trained musculoskeletal (MSK) radiologists is limited in many parts of the world. Reliable, consistent automated detection of knee abnormalities could help extend expert-level interpretation, reduce variability, and support more timely care.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+7): For the train.csv. It contains only 58 flagged labels. Rest are NaN. Those flags do not reflect what is the report.  Does the reports are the GT?...
- **Community Member** (+4): Thanks for the overview! For anyone getting started, the key insight is that this is a multi-label classification problem — each study can have multiple abnormalities present simultaneously. The 12 abnormality categories each need their own probability prediction....
- **Community Member** (+0): Great overview. The combination of multi-label MRI classification, multilingual reports, and clinically adjudicated labels makes this a particularly interesting multimodal challenge. Has anyone found the report text to add a clear advantage over image-only models?...
- **Community Member** (+0): Hi [@javaduke95](https://www.kaggle.com/javaduke95) - thank you offering such clear explanation to competitors. can i clarify the below in the label description section: should "the same criteria applied" read medial meniscus rather than lateral meniscus?    Medial meniscus tear:...
- **Community Member** (+0): Hi study organizers: can you comment on how to deal with bilateral knee mri's in which both left and right side are within the same studyid? If there is only one label per studyid then how should this be resolved? Just report every positive in either knee? For example if left kne...

### [#746792] Reaching 0.949 with one CoAtNet: labels, native crops, and anatomical mirroring
*Votes: 41 | Comments: 56 | Date: 2026-10-07*

**Key Findings & Context:**
> Our best single-model submission scores **0.949 public AUC**. We are sharing the accuracy recipe, our smaller 0.945 model for the efficiency track, and several changes that did not help.

The accuracy result uses one CoAtNet checkpoint trained at 384 pixels. At inference we take a native 320-pixel center crop and average probabilities from the original view and an anatomical left/right mirror. It is one learned model evaluated twice. The checkpoint itself averages three selected epochs from one training run, called SWA in our code.

### The score history

These are ordinary, full twelve-finding public leaderboard scores. Rows describe successive pipeline configurations; their differences are not all isolated causal effects.

Configuration

Public AUC

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+6): Be careful - OAI may not be an allowed external data source. I’d read the host comments about dataset accessibility and then OAI’s own rules before risking using it in model training....
- **Community Member** (+2): I checked OAI's rules, as long as I publish what's been done it's fine. Regarding the host, well they see this post now so we might get the direct answer from them....
- **Community Member** (+0): How did you get access to OAI? It seems to be gated on a Login.gov account, for which one needs a US passport and a social security number. I am in the US so I do not know what this looks like for someone in another country, but could be problematic from the [hosts statement abou...
- **Community Member** (+1): It doesn't require what you've stated to sign up. From OAI'S side, I didn't have any issues, and actually included what I've done as a case study on their portal, which is something they welcome. If interested check out the links at the very end of this post....
- **Community Member** (+4): You don't need any of that. Creating the login.gov account (for the purpose of getting access to this data) just requires your email id. And regarding use of the dataset, I reached out to the team at UMass and here is their response-...

### [#733932] "Not addressed" is a label too — what we learned reading 4,407 knee reports with an LLM
*Votes: 62 | Comments: 11 | Date: 2026-08-09*

**Key Findings & Context:**
> **TL;DR** — Only 58 of 4,407 training studies have real labels, so everyone manufactures

targets from the radiology report. An LLM does this measurably better than a regex

(**0.8780 vs 0.8136** against the 58 gold studies). But the more useful finding is about

the gaps: **25.4% of all label cells are "the report does not address this"**, and what

that silence means is different for every finding. Getting that wrong costs more than the

labeller's accuracy does.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+0): Thanks for this article, I set my LLM extraction phase to explicitly ignore any study with no clear diagnosis and set it 0 across all 12 labels, but with this your findings in Effusion and synovitis it just proves I was throwing in lots of false negatives into my work...

### [#745861] Tricks for the competition 
*Votes: 35 | Comments: 50 | Date: 2026-10-04*

**Key Findings & Context:**
> Show chatgpt the medical report and image. Ask him to label the roi.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): This is a good idea. I thought about showing the images and reports to a multi-modal LLM. The challenge is: what images do we show them? Do we give them a few middle images of each view? Do we give them all 100+ images? There are decisions to make here....
- **Community Member** (+2): The same old tricks in the old days of kaggle:  1) for "solo devlopement" : active labelling. Starts ask chatgot to label lots of slices. Then train some models (or grab from public notebooks) and ask chatgpt to verify only smaller number of suspicious slices. Since the views (an...
- **Community Member** (+1): If I understand correctly, there's a particular slice or region you need to look at (and that the radiologists look at) to determine if the abnormality is present or not. So I'd feed those specific ones for the abnormalities the textual LLM is insufficient to determine.  I don't ...
- **Community Member** (+2): Great work! Would you mind sharing a bit more about how you generated the labels with Claude? I’m curious about what you provided as input (e.g. individual slices, selected slices, or the whole MRI series), how you prompted Claude to assign the labels, and whether you did any man...
- **Community Member** (+-1): Can JEV help?  I joined the competition late. I apologize if the information below is repeated (I haven't got time to go through all the posts in the forum yet)   [1] Can Jev Judge Radiology Reports? Evaluating a System One Model for Clinical Factuality  [https://arxiv.org/html/2...

### [#733497] I got a perfect usecase for this competition.
*Votes: 43 | Comments: 20 | Date: 2026-08-07*

**Key Findings & Context:**
> Recently, I had some instability in my left knee, and doctor said that i should do MRI, I did it.

Guess what, I had my ( ACL ) front ligament tear completely, So i am gonna use my MRI in this competition and see if it can predict it accurately.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+6): true zero shot validation...
- **Community Member** (+4): If anyone wants to create this competition into a project and wants to see if they can use it on a real world data, just say it and i will share the photos....
- **Community Member** (+0): We built the competition to demystify radiology AI and make things relevant to real-life.  Love seeing that you find this relevant to yours.  ACL is one of the most important ligaments in the largest joints in the body. I hope the injury wasn't too bad and good luck with recovery...
- **Community Member** (+16): I think under the competition rules, you are technically supposed to make your MRI publicly available to use it in the competition (see "EXTERNAL DATA AND TOOLS"), even though it's probably not impactful. I have a ruptured ACL too, maybe we can make a "Kagglers with injured knees...
- **Community Member** (+5): Haha, Yeah we should make it   Injured knee kagglers assemble!!...

### [#747658] RSNA Knee MRI reports — LLM label-extraction benchmark 
*Votes: 23 | Comments: 21 | Date: 2026-10-09*

**Key Findings & Context:**
> Trying the Kaggle Benchmark format -- work in progress --

[https://www.kaggle.com/benchmarks/kirderf/rsna-knee-llm-label-extraction-benchmark](https://www.kaggle.com/benchmarks/kirderf/rsna-knee-llm-label-extraction-benchmark)

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): i have a wild experiment:  1) lets define llm label and GT label (the golden 58)  2) my multi mri image predictor trains very fast in hr.  3) llm label is close to GT label. e.g. hamming distance per class is less than 3. some class are more likely to be wrong. some class has onl...
- **Community Member** (+3): note that the GT labels may be created by radiologist/doctors without looking at the report. Hence, the report and label are independent, and a discrepancy exists. That explains the upper limit of 0.90 in teh results....
- **Community Member** (+2): check one of the 58 gold label stduy id:  1.2.826.0.1.3680043.8.498.12606657226568558340797193167488111973    label is "Effusion": 1,    quote from medical report "No knee effusion is present."...
- **Community Member** (+0): Yes working with image vs report is the objective, one of the experiments lately:  Read every report several independent times. Fuse the readers into one probability per cell. Combine the per-reader probabilities into a single fused probability per (study, finding) cell — use a w...
- **Community Member** (+1): for your reference, complete reproducible results for Claude4.5 (auc 0.891895) is found at: [https://github.com/NTejas-1/RSNA-Knee-Abnormality-Detection](https://github.com/NTejas-1/RSNA-Knee-Abnormality-Detection). It has prompt, labels, etc.  Full credits go to the author [@NTe...

### [#733965] Use of Commercially Hosted LLMs
*Votes: 26 | Comments: 14 | Date: 2026-08-09*

**Key Findings & Context:**
> Use of commercially hosted LLMs and other external inference services is permitted, provided that the service and method of use otherwise comply with the Competition Rules, including requirements that external data, models, software, and associated tools be reasonably accessible to all participants and of minimal cost.

In other words, for purposes of this competition, submitting Competition Data, including report text, to an external LLM or API for inference or other computational processing (for example, extracting labels from reports) will not, by itself, be considered prohibited **PRIVATE SHARING** of Competition Data outside the Team.

Please refer to the [RSNA Knee Abnormality Detection Competition Rules](https://www.kaggle.com/competitions/rsna-knee-abnormality-detection/rules).  This is in accordance to Section 2.6.b, **EXTERNAL DATA AND TOOLS**.

The **PRIVATE SHARING** restriction is intended to prohibit sharing Competition Data, code, or competition-specific work product with other participants, teams, or third parties for collaboration or competitive use outside the registered Team.

Participants remain responsible for ensuring that any external service complies with all applicable Competition Rules and the service's terms of use, including the requirements for reasonable accessibility and minimal cost.

The Competition Host reserves the right to determine whether a particular service, model, or configuration is reasonably accessible, is prohibitively costly, or otherwise creates an unfair competitive advantage.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+4): "Participants remain responsible for ensuring that any external service complies with all applicable Competition Rules and the service's terms of use, including the requirements for reasonable accessibility and minimal cost.  The Competition Host reserves the right to determine w...
- **Community Member** (+0): That's a great suggestion - contact the source and ask if they are ok with you using the data in a kaggle competition.  Not sure if they would reply, but also past experience suggest kaggle reluctant to reply to this type of question during the competition....
- **Community Member** (+1): The rules about commercially hosted LLMs are important here. Since knee MRI interpretation requires domain expertise, it's tempting to use an LLM to help with reasoning. But the competition rules likely restrict this to ensure the solutions are based on the image data, not extern...
- **Community Member** (+3): To make the dataset question above concrete: the Osteoarthritis Initiative (OAI) is free of charge and open to any researcher after a click-through data use agreement, but the agreement limits use to non-commercial research. The same access pattern covers MRNet, fastMRI+ and SKM-...
- **Community Member** (+8): From the competition’s perspective, use of these datasets would be considered non-commercial; receipt of competition prize money does not, by itself, make their use a commercial sale or commercial exploitation. These datasets would not be excluded by the competition rules solely ...

---

## 🏆 ARC Prize 2026 - ARC-AGI-2 (`arc-prize-2026-arc-agi-2`)
**Domain**: AGI / Program Synthesis / Discrete Topology
**Topics Mined**: 10 highest-impact discussions

### [#685142] Last Years 1st Place Solution
*Votes: 25 | Comments: 21 | Date: 2026-03-27*

**Key Findings & Context:**
> Has anyone tried submitting last year's winning solution?

[https://www.kaggle.com/competitions/arc-prize-2025/writeups/nvarc](https://www.kaggle.com/competitions/arc-prize-2025/writeups/nvarc)

I suspect it would achieve `Public LB 27` and `Private LB 24`!

(edit: last year was 4xL4 and this year is 2xT2, so it cannot achieve these scores)

========

**UPDATE**: The code has been reconfigured for 2xT4 and published [here](https://www.kaggle.com/code/nihilisticneuralnet/9-58-nvarc-arc-2025-winning-solution-for-t4)

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+6): That solution uses 4xL4 GPUs. We still don't have access to those.    NOTE: We are currently exploring options to provide better compute for this competition....
- **Community Member** (+4): You won't get these scores with 2xT4. We used 4xL4....
- **Community Member** (+4): UPDATE: The code has been reconfigured for 2xT4 and published [here](https://www.kaggle.com/code/nihilisticneuralnet/9-58-nvarc-arc-2025-winning-solution-for-t4)...
- **Community Member** (+2): anyone trying[ topas](https://github.com/Bitterbot-AI/topas_DSLPv1)?...
- **Community Member** (+6): We did not wait 😀  Our notebook from last year runs fine in this year comp, see [https://www.kaggle.com/code/jonathanchan/arc26-2025-winning-solution-v1](https://www.kaggle.com/code/jonathanchan/arc26-2025-winning-solution-v1)...

### [#709522] Historical leaderboard with runtime information
*Votes: 32 | Comments: 6 | Date: 2026-06-19*

**Key Findings & Context:**
> I made the historical leaderboard for ARC Price 2026 - ARC-AGI-2

[https://arc3.huikang.dev/leaderboard/?comp=arc2](https://arc3.huikang.dev/leaderboard/?comp=arc2)

Here is a screenshot.

This was done for [AIMO3](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/discussion/662498) and it was helpful for many people, since I am doing this for [ARC-AGI-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/709355), so I am doing this here as well.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): Great work! Thank you for this. I just have one suggestion. The horizontal scroll bar is not accessible as it is at the bottom of the table and the table expands as we scroll vertically. Is it possible to modify this? May be move the scroll bar to the top and also freeze the head...
- **Community Member** (+2): Well, Kaggle could have made this a feature...

### [#747515] Update on "Kaggle Error" Submissions & Queue Delays
*Votes: 20 | Comments: 27 | Date: 2026-10-08*

**Key Findings & Context:**
> Hi everyone,

I wanted to give an update on the long submission wait times and "Kaggle Error" failures many of you have been seeing over the past couple of days.

### What Happened

Due to very high submission volume using L4s, submission jobs have been facing long queue times before actually getting a machine to run. Submissions that waited >15h to start were being marked as “Kaggle Error” even if they eventually did run.

### What We Fixed

**Extended Queue Timeout:** We've drastically extended the queue allowance so submissions will no longer be timed out while waiting to run.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): Thanks for your effort. How are we effectively preventing this from happening again, given that we now have an even bigger load, with everyone rushing to submit more and your batch recovery trying to spam it with the previously error ones?   We might need to ask Jensen for more L...
- **Community Member** (+2): The new limit effectively prevents each team from having more than one submission pending/running at a time, bounding queue growth.  I didn't rerun submissions, I just re processed scores that were skipped because of long waits.  I already added a lot of capacity to the fleet but...
- **Community Member** (+0): Hi [@herbison](/herbison), I have 2 questions:  If the submission from yesterday's slot hasn't finished yet, and it keeps showing Scoring like this past today's submission deadline, does this mean I'm losing today's slot with this new pending submission limit? How are the Save Ru...
- **Community Member** (+0): I believe if it finishes running on a different day, you'll be able to submit another. Bleeding over to the next day doesn't "take" today's submission away. You likely can "miss" a submission if >24h in the queue passes just by the nature of not having been able to submit for tha...
- **Community Member** (+0): [@herbison](/herbison) Thank you for the update and for working to resolve the submission queue issues.  I understand that the pending submission limit is separate from the 1/day limit and that I must wait for my previous submission to finish scoring before submitting again.  How...

### [#746520] Kaggle Error?
*Votes: 19 | Comments: 25 | Date: 2026-10-07*

**Key Findings & Context:**
> Did anyone else get a Kaggle Error on their submission yesterday? Mine ran 15 hours and errored out. I also noticed slow downloads, possibly a docker image?

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): [@herbison](/herbison) Hi Dustin, could you please look at this failed submission?  Submission ref: 56890645 Submitted: 2026-10-06 20:49 UTC Result: "Kaggle Error – A system error. Please try resubmitting…", after about 15 hours  The submission was about one hour after your messa...
- **Community Member** (+1): Not affected by the dataset mount outage. Instead it was queued too long, I'm working on fixing that, but demand is making it hard. Runtime limits only count running time, not queued time. There is a queue time limit for submissions as well, but its an independent timer. Image ve...
- **Community Member** (+2): -1 submission. possible to give affected users another submission slot? [@herbison](/herbison)...
- **Community Member** (+0): Hi [@herbison](/herbison), could you check whether my two failed submissions were also affected by the queue-time issue? Both returned “Kaggle Error — A system error. Please try resubmitting…”  7 October 2026, 19:22:04 UTC: notebook v6, scriptVersionId 356154398 8 October 2026, 1...
- **Community Member** (+2): [@herbison](/herbison) [@macruzbar](/macruzbar) Please create an offical kaggle topic for the "kaggle error"/queued submission issue in both arc2 and arc3 so all users can get the same information and can follow the way to a solution, thanks!...

### [#689054] Upgraded Accelerators
*Votes: 21 | Comments: 20 | Date: 2026-04-07*

**Key Findings & Context:**
> Hi everyone,

we just upgraded the accelerators for ARC-AGI-2. This competition now has access to Kaggle's pool of powerful new L4x4 machines! These machines offer 96GB of GPU memory enabling submissions with much larger models.

Head over to the [Overview tab](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/overview/upgraded-accelerators) to learn the essentials and see [this page](https://cloud.google.com/compute/docs/gpus#l4-gpus) for more in-depth information on these machines.

Good luck!

María

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+0): Thank you for the update! Just wanted to check on this, I thought I remembered the plan being to use H100s for this competition. I am honestly hoping that we are using the 4xL4 and not the H100 but just wanted to be sure that this was the last gpu change for the competition? Than...
- **Community Member** (+3): Our plan is to implement the H100s for the ARC-AGI-3 competition.  Note, any of our advanced accelerators are heavily supply constrained, and we do our best to maintain as much capacity as we can, but as has been seen across these competitions we can face variable supply constrai...
- **Community Member** (+0): Thank you for the upgraded accelerators.  If possible, could the H100s be made available for ARC-AGI-2 to open up more approaches?  I understand resources are heavily constrained so perhaps for ARC-AGI-2, the H100s can consume GPU quota at 2.5 the rate of the 4xL4?...
- **Community Member** (+1): Dear ARC Prize Organizers,  I hope you are doing well. My team and I have many promising ideas and approaches we would like to explore for the ARC Prize 2026 competition, but we are currently limited by a lack of GPU resources and financial means. I noticed that some sponsors may...
- **Community Member** (+2): [@addisonhoward](/addisonhoward) [@macruzbar](/macruzbar) It looks like the L4 queue is jammed. Can you do something? See [https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/743927](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/discussion/74392...

### [#743927] These 2 days the notebooks have been easily queued for several hours and couldn't be executed immediately
*Votes: 15 | Comments: 22 | Date: 2026-09-27*

**Key Findings & Context:**
> As the title.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): [@macruzbar](/macruzbar) [@gregkamradt](/gregkamradt)  I've been experiencing the same issue with L4×4 notebooks when every commit waited nearly seven hours before starting. These delays make even small debugging runs painfully slow, and it’s becoming really discouraging.   I und...
- **Community Member** (+2): my submisison did not kick off at all....
- **Community Member** (+2): Queued commits since 2 days ago, impossible to debug and submit new ideas. This is very discouraging 😟...
- **Community Member** (+2): Here the Culprit.😁 [https://www.kaggle.com/competitions/gemma-4-developer-agent](https://www.kaggle.com/competitions/gemma-4-developer-agent) Another competition where people use L4 4x....
- **Community Member** (+3): Queue should be cleared, and capacity held across peak today, thanks for your patience!...

### [#747088] Did anyone get a valid sub in last 2 days? [Solved]
*Votes: 18 | Comments: 11 | Date: 2026-10-08*

**Key Findings & Context:**
> Edit. Our failed submissions have been scored.

Our last two submissions got an error after being queued too long. Same code as before, just a new checkpoint.

The competition has become useless.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): same error...
- **Community Member** (+2): Same Kaggle system error as reported in another discussion...
- **Community Member** (+2): Same, just entered competition 2 days ago, first submissions are scoring for 17+ hours, still in progress....
- **Community Member** (+2): I think the long queue could be related to a change in the L4x4 GPU quota computing.  Before when I tested, 15 minutes would equal 1 hour of quota use.  Now it is 1 hour = 1 hour.  So maybe people are using the L4s to test a lot more, which takes the fleet away from submissions?...

### [#724647] Good to see movement on LB
*Votes: 13 | Comments: 17 | Date: 2026-07-12*

**Key Findings & Context:**
> 2nd team has clearly moved beyond what could be done with knob fitting on our last year solution. This is good news for the competition.

Congrats to them.

But let's not make too much progress still 😂

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+5): Congratulations on reaching 67.50!  I've noticed your team has been making very consistent progress week after week. It's really impressive to see how steadily your performance keeps improving. Keep up the great work!...
- **Community Member** (+3): Thanks. We're not done yet hopefully 😁...
- **Community Member** (+0): [@cpmpml](https://www.kaggle.com/cpmpml), big fan here — Thank you and Ivan for releasing the NVARC solution so openly.  I’m considering renting GPUs for a serious solo-gold attempt here, but I’d like to avoid an expensive wrong path. Since the Qwen and TRM checkpoints are alread...
- **Community Member** (+5): Hi Tony,  We won't share more till the deadline....
- **Community Member** (+8): [@tonylica](https://www.kaggle.com/tonylica) [https://huggingface.co/datasets/nvidia/Nemotron-SFT-ARC-AGI-v1](https://huggingface.co/datasets/nvidia/Nemotron-SFT-ARC-AGI-v1)  you can deduce the tools used: arc-python-executor, commit, augmenter  they already trained nemotron-ultr...

### [#697859] Bitterbot's TOPAS Architecture Submission: 11.67% LB vs ~36% Local (Managing TTT Timeouts)
*Votes: 10 | Comments: 23 | Date: 2026-05-07*

**Key Findings & Context:**
> We used this submission primarily as a pipeline test for our Kaggle setup using an early, not fully-trained checkpoint. We're currently running the TOPAS architecture. It’s a highly efficient, lightweight setup at only ~100M parameters, and it relies heavily on deep recursion.

Our current compute footprint - we are training on a single consumer-grade RTX 4090. This checkpoint is 14 days into training. We estimate another ~10 days for the model to properly converge.

Locally, using the same 14-day checkpoint, we are hitting ~36%. The massive drop on the leaderboard comes down in part to time management constraints within the Kaggle environment.

Because TOPAS utilizes deep recursion, our TTT becomes computationally heavy. During our initial sandbox tests, we were struggling to stay within the strict time limits and kept timing out. While tinkering to ensure the submission would actually complete, we overcompensated on our time-limit thresholds. This resulted in the model bailing out early to save time, ultimately failing to output a prediction on a large chunk of the puzzles.

Moving forward as we wait for the model to fully converge over the next week and a half, we need to fine-tune our time-management so we convert [[0]] placeholders into real beam outputs.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+4): Squeezing your code to fit Kaggle compute limit is what makes this competition challenging.   It is good that your first submission went through, even if the score may disappoint you....
- **Community Member** (+0): I am feeling pretty stupid for using static partitioning, I thought I had enough headroom to get away with it.  Instead I watched 12 hours of compute evaporate because one GPU drew the short straw and got a bunch of hard puzzles while the other three finished in under 11 hours an...
- **Community Member** (+3): I always save first, I don't submit directkly. It catches this mistake (and other mistakes). A mistake I keep doing, because accelerator are turned off automatically in this comp....
- **Community Member** (+1): This happens for us too.  Last year our winning solution had 30.5% pass@2, but 40% pass@10 if I remember correctly. On the public evaluation data. This led to 27% public LB (semi private data, i.e. same as arc agi leaderboard), and 24% private LB.  Our scorer algorithm missed 10%...
- **Community Member** (+0): A curious questiom that you donthave to answer of course, your leaderboard score is because you updated the scorer to cover those 10% or a newly Finetuned model? 😁  i tried many different strategies foe the scorer and i coudnt beat that 30. Your answer could help me to not waste ...

### [#694698] 95% on ARC AGI1 evaluation
*Votes: 20 | Comments: 2 | Date: 2026-04-26*

**Key Findings & Context:**
> After last year competition, we ran our code on ARC AGI1 public evaluation data, and we scored above 95%.

The code to reproduce it is in our last year solution github repo: [https://github.com/1ytic/NVARC/tree/main/ARC-AGI1](https://github.com/1ytic/NVARC/tree/main/ARC-AGI1)

The reason for the high score is twofold:

ARC AGI1 puzzles are much easier than ARC AGI2.

Most of ARC AGI1 evaluation is included in ARC AGI2 training data.

The second reason is the most important one. It shows that ARC AGI1 scores need to be taken with a grain of salt, depending on the use of ARC AGI2 data or not. All frontier models use ARC AGI2 training data, hence their scores on ARC AGI1 are meaningless.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+5): We did not submit officially. I expect the semi private score to be much lower though as it would not benefit from the evaluation data leak.  We rather fought on getting  our 29.x score obtained 2 days after competition deadline to appear in the arc agi2 LB, but for some reason I...

---

## 🏆 ARC Prize 2026 - ARC-AGI-3 (Interactive) (`arc-prize-2026-arc-agi-3`)
**Domain**: Interactive AGI / Exploration / Affordance Discovery
**Topics Mined**: 10 highest-impact discussions

### [#717133] Tufa Labs’ Winning Solution for ARC-AGI-3 Milestone 1
*Votes: 73 | Comments: 18 | Date: 2026-07-01*

**Key Findings & Context:**
> Authors (alphabetical order): Harold Bessis, Jeroen Cottaar, Isaiah Pressman, Dries Smit, Michal Tešnar, and Stefano Viel.

This technical write-up describes our winning solution for the first milestone prize in the [ARC-AGI-3 Kaggle competition](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3). We present the Duck, the successor to [Stochastic Goose](https://medium.com/@dries.epos/1st-place-in-the-arc-agi-3-agent-preview-competition-49263f6287db) authored by Dries Smit, which won the ARC-AGI-3 agent preview competition. Our solution consists of an inference harness leveraging [Qwen 3.6 27B FP8](https://huggingface.co/vrfai/Qwen3.6-27B-FP8) as its base model and takes heavy inspiration from the [RGB Agent](https://blog.alexisfox.dev/arcagi3) and [Symbolica](https://www.symbolica.ai/blog/arc-agi-3) solutions. The harness uses a Python tool to interact with a game and continuously evicts past messages from its context to keep playing indefinitely. We make the code freely available on [GitHub](https://github.com/Tufalabs/duck-harness). Disclaimer: the code was developed with the help of coding assistants.

We discuss our solution and compare it to other approaches in our [blog post](https://tufalabs.ai/research/duck-harness), and showcase is in an episode of [Machine Learning Street Talk](https://x.com/MLStreetTalk/status/2072326433922297975?s=20). We discuss the progress on the benchmark in more depth in [another episode of MLST](https://www.youtube.com/watch?v=Vg6FBKTlfOw).

Alongside this write-up, we are publishing [the notebook](https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle-share) corresponding to our best submission score of 1.21% on the Kaggle leaderboard and 1.6% on the public train set, respectively. This submission initially scored 1.30%, but that result was retracted by Kaggle, leaving 1.21% as the official leaderboard score ([result here](https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle)). We observed a large variance in scores for the same submission, our best submission got scores as low as 0.77% on Kaggle and on the public games we observe standard deviations of up to 0.4. Our notebooks represent only the infrastructure and metrics; the agent code is attached as a dataset.

We release this harness with the hope of lowering the barrier to entry and inspire innovation from the community. Next, we will present the harness design, explain how the agent behaves, and show results on the public train set.

📝 The text in this post is fully human written, but figures are produced with coding assistance. Refer to the submissions notebook and the repository as the ground truth.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): Thank a lot! I really enjoy reading you. I learn a lot from you write up. Amazing contribution to humanity....
- **Community Member** (+2): I think this represents the true spirit of a milestone prize. You are all clearly dedicated to advancing these domains and helping others do the same. Thank you!...
- **Community Member** (+2): Just finished reading this and its so cool to see you guys turned the game into code. I didn't think of that! Great write up as always! Thank you for the high effort and quality into this!...
- **Community Member** (+3): Yes, but due to cost we've only done a few games. See here: [https://tufalabs.ai/research/duck-harness](https://tufalabs.ai/research/duck-harness)...
- **Community Member** (+2): Thank you, this information is useful. Judging by the gradient table, this method is practically independent of the level complexity. The model is either able to find a pattern, or it isn't. To verify, you could run this test with another local model, for example, the one recentl...

### [#744792] Comparing the Milestone 2 winning solutions
*Votes: 64 | Comments: 18 | Date: 2026-10-01*

**Key Findings & Context:**
> Congratulations to the [winners](https://x.com/arcprize/status/2105737436450201734) of Milestone Prize 2!

All three run Tufa Labs' Duck harness on the Tufa ARC-AGI Framework (TAAF) and serve Qwen3.8-Flash-Next.

Here is a comparison ~

dfranzen

lordhansolo

sirikilohit

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+3): Congrats to the winners! Very good inference engineering :)...
- **Community Member** (+7): So many token wizardry :D.  A bit unfortunate that we only figured out how important these are late in the game.  Nevertheless, congratulations to the well-deserved winners!...
- **Community Member** (+3): Congrats!!! Since all the public one have quite the same inference improvement, maybe next phase will focus more on harness (or we have new OSS  model release 😂)...
- **Community Member** (+7): The big thing I learned here is how useless the coding agents are for understanding vllm and sglang and I am admittedly not an expert in either. I knew more tokens and more time == more levels solved, but I could not make that happen working from within codex and claude. That's o...
- **Community Member** (+3): I can share my own experience here now that the solution is out.  For a long time I could not figure out how to improve it, because I just keep telling the agents to "try everything you can" to optimize TPS.  I did not thing of potentially just pruning of changing the serving unt...

### [#742801] We will not be open-sourcing for the second milestone prize
*Votes: 41 | Comments: 45 | Date: 2026-09-23*

**Key Findings & Context:**
> **TLDR**: We, Tufa Labs, will not be sharing our solution on September 30 for the second milestone prize, since we worry it may not be possible to beat the best of 4000 copies of that solution. We still plan to release our final solution when the competition ends. We encourage other top teams to share their intentions ahead of the milestone as well.

On June 30, we open-sourced our duck harness, claiming the first ARC-AGI3 milestone prize. Apart from the prize itself, part of our motivation was that we believed this would increase the quality of the competition by providing everyone with a good baseline to build on. This has worked out well, with all high-scoring public notebooks now building on this harness. We were not worried that further improvement wasn't possible; we knew that our harness was just the beginning.

With the second milestone on September 30 coming up, we are faced with a similar choice. This time, however, it is not so obvious that big improvements are still possible in the limited time that remains. We worry that if we (or another top ranked team) share our solution there will be 4000 submissions copying this solution, with the winner simply being the luckiest. Minor improvements would not help you; your score would need to beat the best of 4000, and variance is high. This has happened before, such as in this year's AIMO competition.

So we've come to the conclusion that we will not be participating in the second milestone prize, and so will not open-source our solution. We remain fully committed to sharing our final solution when the competition ends.

We understand that other top teams may choose differently. Either way, we'd like to encourage all top teams to clarify their plans; this also helps lower-ranked teams to know whether to share or not.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+0): Thanks for sharing your intention early!  I also want to ask regarding the [rules](http://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview/prizes)    Notebooks must be made public under an open source license by the corresponding milestone dates to qualify for these ...
- **Community Member** (+1): It moves down the ladder, so if the highest scoring open-sourced notebook is actually in 15th place on the leaderboard, but the teams paced 14th - 1st don't open source, then the 15th place open source solution becomes the "1st" place prize winner for the milestone....
- **Community Member** (+2): You have a commanding lead. My guess is part of that is some fine tuning, but I just got to #38 on harness fixes alone (5.19) so there's still room for many to climb....
- **Community Member** (+2): From Game Theory perspective I don't think it is worth it.  The team basically sacrifices $25k for a better chance of gaining $40k. Tufa still has competition-winning talents and resource levels (which then can further re-invests the $25k on if they feel they are in danger of los...
- **Community Member** (+2): I don't think they are focused on exact prize money, i think it has more to do with risk of being milestone winner but not competition winner because of the noise introduced by 4000 copies....

### [#732854] What are your agents scoring on the 25 public games?
*Votes: 16 | Comments: 61 | Date: 2026-08-04*

**Key Findings & Context:**
> Hi all,

I'm curious how everyone's agents are doing on the 25 public demo games, and I think it would help all of us to have a rough community baseline in one place. Local public-game results aren't a perfect leaderboard proxy, but they're still the fastest signal most of us have while iterating.

If you're willing to share, here's a format that would make comparison easy:

Overall: average score across the 25 games (and how many games you score > 0 on)

Per game: which games you clear, and roughly what score — even a rough "solved / partially solved / zero" breakdown is useful

Setup: base model, harness style (coding agent in a REPL, orchestrator + subagents, RL, hand-written search, etc.)

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): Got 2.8 locally so far...
- **Community Member** (+0): I had an alternative approach based on using Claude Fable to build game-specific solvers that solved 7 of the 25 public games and hit ~38% RHAE overall at 116/183 levels. That really worked, but it's utterly impractical here because it needed Claude access and it took 5 days to s...
- **Community Member** (+1): So yesterday I hit 11.04 on the public games with a win of ft09. Yay me I guess. So I submitted it last night with great hope…  Sadly, 2.71. WTFF? This was based entirely on game-independent harness changes and Qwen 3.8 flash next nvfp4.  The variance on submissions is insane. I ...
- **Community Member** (+0): I've scored as high as 12 on the public games. The best I have seen is 3.2 on the hidden. I am beginning to think the only path forward is a winning recipe for SFT/RL on an existing model. And because I am out of you know whats, most of what I have done is just take the stock duc...
- **Community Member** (+0): I've scored as high as 12 on the public games. The best I have seen is 3.2 on the hidden. I am beginning to think the only path forward is a winning recipe for SFT/RL on an existing model. And because I am out of you know whats, most of what I have done is just take the stock duc...

### [#716696] Code for milestone 1st place open sourced - writeup tomorrow
*Votes: 38 | Comments: 16 | Date: 2026-06-30*

**Key Findings & Context:**
> We've open-sourced our code for the purpose of the milestone. You can find it here: [https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle](https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle)

A more shareable verison (that didn't get the same lucky score) is here, we highly recommend working from this one: [https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle-share](https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle-share)

Tomorrow at 3 PM CEST we'll share a detailed technical writeup and several supporting materials, so stay tuned.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): Awesome congratulations, i am excited on your work I also read some papers from your lab I think some of them might be useful in this competition...
- **Community Member** (+-1): [@gregkamradt](https://www.kaggle.com/gregkamradt) Will this competition end here, or will it continue?  The highest score was supposed to be 1, but the top participant has already exceeded that value. Could you please explain how the competition will proceed from this point onwa...
- **Community Member** (+2): The high score is 100, not 1....
- **Community Member** (+4): No, it's very unstable, ranging from 0.7 to 1.3....
- **Community Member** (+0): congrats guys! Out of my 19 submissions 3 of my failed attempts were maybe 85-90% on the same path but only 25-30% ready for a submission… I ended up going a different route… boy do I wish I had stuck to that idea… anyways, can't wait to read the technical writeup!...

### [#686416] Simplified submission framework
*Votes: 42 | Comments: 3 | Date: 2026-03-31*

**Key Findings & Context:**
> The official notebooks show how to submit your agents to run on ARC-AGI3, but they're pretty complicated. Also, they do nothing if you're not actually submitting - they don't actually run on the 25 training games then.

We've made this notebook that shows a more straightforward way to interact with the ARC-AGI3 environments. It will run on the 25 training games when not submitting (including diagonstics), and on the 110 test games when submitting.

Good luck!

[https://www.kaggle.com/code/jeroencottaar/simplified-submission-approach/](https://www.kaggle.com/code/jeroencottaar/simplified-submission-approach/)

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+3): Thank you for this contribution...
- **Community Member** (+0): Hey, any idea why this scores 0.00 while the official random example scores 0.something? I tried increasing the max iterations to 100k and making it parallel w/ 20 threads, still 0.00. On the test set it scores something (solving some first levels, and even 2nd levels on 2 proble...
- **Community Member** (+0): I figured it out, posting here for posterity. My first attempt at parallelising the code was calling env.make() in each process, you can't do that as it will open a scorecard for each process, and end up with a 0 code. I followed the code in the agent repo and called make() on th...

### [#742148] Long Queue for RTX Pro 6000 (8 hours) partially due to abusive used for non ARC-AGI-3 tasks, Proposal to mitigate
*Votes: 22 | Comments: 24 | Date: 2026-09-20*

**Key Findings & Context:**
> The Long Queue for RTX Pro 6000 usage has been getting serious day by day especially between 2 am UTC to 9 am UTC. Beside legitimate usage, the problem is partly made serious by abusive used of RTX Pro 6000 GPU for non ARC AGI-3 tasks.

I propose 2 methods below to mitigate the problems: [@herbison](/herbison)

Decrease the number of allowed concurrent GPU usage for RTX Pro 6000 from 2 to 1 per user. This will limit the abusive usage for Training of non ARC-AGI-3 tasks while free up resources for iteration. (At least 50% can be free up)

Make a clear warning pop-up when user chose RTX Pro 6000 as the GPU, currently there is no warning, some novice user might not read the rules and use it ignorantly for non ARC-AGI-3 tasks.

Other participants can also propose better way to mitigate if you had any ideas.

Some example of abuse:

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+3): ong bro like what the helly is this ts 😭 im crine rn, i have to use my cloud creds or something else as an alternative  KAGGLE OR ARC PLEASE HELP...
- **Community Member** (+5): Long queues mean the rewards keep going to the same group of selected people. Meanwhile, I can’t even test new notebook versions or run new experiments because of the queue....
- **Community Member** (+2): Have noticed the same issue over the last 2 days. :(...
- **Community Member** (+3): Almost 12 HOURS for me :(. This sucks...
- **Community Member** (+1): [@herbison](/herbison) [@macruzbar](/macruzbar) [@gregkamradt](/gregkamradt)  The Kaggle GPU is totally unusable these few days, can you consider temporary stopgap measure by limiting the concurrent GPU save to 1 per person (instead of 2 currently)?  This will immediately release...

### [#691696] It is 0.66%
*Votes: 24 | Comments: 9 | Date: 2026-04-15*

**Key Findings & Context:**
> A colleague of mine ran the top public notebook on 10 public games. Here are the results. Even though the score is low, it is interesting that some levels are solved still.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+4): It is 0.33 %...

### [#687648] ARC3 Offline Agent Evaluation and Recording Viewer
*Votes: 23 | Comments: 10 | Date: 2026-04-03*

**Key Findings & Context:**
> Hi everyone, sharing a reproducible ARC3 notebook for offline agent evaluation and debugging.

Notebook: [ARC3 Offline Agent Evaluation and Recording Viewer](https://www.kaggle.com/code/shiinehata/arc3-agent-evaluation-and-recording-viewer/notebook?scriptVersionId=308657447)

What this notebook adds:

Runs the copied agent offline

Computes per-game action-count and score stats on public games

Visualizes recordings for behavior inspection and debugging

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): Thanks for the question. I was able to run the code from [https://www.kaggle.com/code/itsyoursumit/forge-arc-agi-3-agent](https://www.kaggle.com/code/itsyoursumit/forge-arc-agi-3-agent) by simply replacing my agent write cell with theirs, so compatibility-wise it does run in this...
- **Community Member** (+2): What max action limit resulted in a clean run? (not hitting the storage failure)...

### [#709355] View your run time and the historical leaderboard
*Votes: 23 | Comments: 5 | Date: 2026-06-18*

**Key Findings & Context:**
> I used [Kaggle API](https://github.com/Kaggle/kaggle-api/blob/main/docs/README.md#competitions) and Modal compute for [query](https://modal.com/docs/guide/cron) the API minutely, and to [store](https://modal.com/docs/reference/modal.Dict) and [serve](https://modal.com/docs/reference/modal.fastapi_endpoint) the data.

[https://arc3.huikang.dev/leaderboard](https://arc3.huikang.dev/leaderboard)

Here is a screenshot, cropped to a size where I am still visible.

This was done for [AIMO3](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/discussion/662498) and it was helpful for many people, so I am doing this here as well.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): I made my first submission to the competition 3–4 days ago, and one of the first things I looked for was the historical leaderboard (it was very helpful in AIMO3 for understanding trends). When I couldn't find it, I said, "looks like [@huikang](https://www.kaggle.com/huikang) hav...
- **Community Member** (+2): Why does it show a score of 1.30 on June 4th, but the highest score is still 1.21?...

---

## 🏆 Enveda CASMI26 Molecule ID (`enveda-CASMI26-molecule-id-mass-spectra`)
**Domain**: Computational Chemistry / High-Res Mass Spectrometry
**Topics Mined**: 10 highest-impact discussions

### [#741359] Welcome to CASMI 2026!
*Votes: 27 | Comments: 10 | Date: 2026-09-14*

**Key Findings & Context:**
> Welcome to CASMI 2026! Identifying molecules from their mass spectra is one of the most important challenges in life sciences, but the number of machine learning scientists who have worked on mass spectra is very small relative to the size and importance of the scientific problem. This creates a great opportunity to have a large impact in a short amount of time. Hence this competition!

The kinds of methods that have been developed in recent years against standing benchmarks like MassSpecGym span a wide variety of approaches that resemble those used across technology and life sciences. We are very excited to see the approaches this community comes up with to tackle this problem. We are especially excited to be providing spectra for many molecules whose structures have not been previously described.

**A note on external data and licensing**

We want everyone to have a fair and enjoyable competition, so a quick reminder on the use of external data and models.

Per the competition rules, the winning solution cannot include any licenses that would otherwise prohibit commercial use or redistribution. When you submit a winning solution, you grant us, the Competition Sponsor, a license to that solution and represent that you have the unrestricted right to grant it. Any external data, models, or tools you rely on must be compatible with that license.

We're aware that datasets exist which carry licenses that fall into this category, i.e. terms that restrict commercial use or redistribution. These should be avoided. Solutions built on data or tools that cannot be commercially licensed will not be eligible to win, and we reserve the right to disqualify any submission that does not comply or can’t be reproduced with allowed data and tools.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+0): Looking to form or join a team for CASMI 2026 - need two more people.  Where I'm at: I've completed a thorough EDA pass on the training data molecule-level train/validation splitting (to avoid spectra from the same structure leaking across both sets), rebalancing the heavy spectr...
- **Community Member** (+0): Hi Amin,  I saw your team-up post. I work on text-based person search (TBPS) — cross-modal retrieval, embedding learning, and re-ranking, so analysing retrieval baselines is squarely in my area, and it's what you said you're looking for help with.  The part of your post that stuc...

### [#741404] A complete statistical tour of the data (EDA notebook)
*Votes: 29 | Comments: 3 | Date: 2026-09-15*

**Key Findings & Context:**
> I went through this dataset column by column and wrote the whole thing up in a public notebook. Sharing it here because three of the findings change how you should set up your validation, and it seems better if we all start from the same picture of the data.

[https://www.kaggle.com/code/josefreitasalvesneto/casmi-2026-a-complete-statistical-tour](https://www.kaggle.com/code/josefreitasalvesneto/casmi-2026-a-complete-statistical-tour)

A few things you may want to know before you write any preprocessing code:

The public leaderboard is measuring the wrong thing. The data page says the test file is "comprised of examples from the training dataset" — it turns out to be enveda-180 rows, and the ones I checked are byte-for-byte identical to training spectra. That library is drug-like screening chemistry, not the natural products the prize is decided on. I would not read anything into a public score.

Test spectra only look 10x richer than training spectra. Median 230 raw peaks vs 27 — but 82% of the test peaks are below 1% relative intensity, and at a 1% floor the two land at 18 and 14. The apparent train/test shift is mostly noise floor.

A plain library search already scores MRR@25 = 0.907 on natural products that have reference spectra. Novelty Class 1 is close to solved without any learning, which means the entire score differential is in Classes 2 and 3.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+7): Thanks for making this notebook, and welcome to CASMI 2026!  Just to clarify something about the public leaderboard and test.parquet: the public leaderboard score is calculated not on the contents of the test.parquet downloadable dummy file (which as you say just contains a sampl...
- **Community Member** (+3): Thank you for sharing this detailed analysis. [@josefreitasalvesneto](/josefreitasalvesneto) I’m still a beginner and learning step by step, but I’m very interested in the chemistry + data science side of this competition. I’m currently trying to organize the main areas that coul...

### [#745715] Visible test.parquet molecule_ids appear to leak class-1 answers
*Votes: 22 | Comments: 11 | Date: 2026-10-03*

**Key Findings & Context:**
> A public notebook (imranarif536/casmi26-v44-pairtail-locked-top1, V3, 0.417) hard-codes the 400 visible molecule_id → SMILES pairs (the structures of the train spectra copied into the dummy test file) and forces them to rank 1 for every row, unguarded; its previous version scored 0.402. That is only possible if (a) the hidden rerun reuses the visible molecule_ids and (b) for a substantial share of ids the dummy row's structure equals the hidden truth. Forks are spreading (two dozen teams at 0.416–0.418). Could you confirm whether molecule_ids are shared between the visible file and the hidden set, and shuffle/remap them before the final rerun? We are not using this and would prefer a level field.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+3): Can the admin confirm if the shuffle/remap will be done? Above is accurate according to my test....
- **Community Member** (+1): +1 from our team. We do not use the visible molecule_id → structure pairs in any way (ids only join rows in our pipeline), and we would welcome a shuffle/remap of the ids before the final rerun so the final leaderboard reflects spectrum-based identification only. Could the hosts ...
- **Community Member** (+0): +1: please remap the test molecule_ids (or confirm they are not shared) before the final rerun  Thanks [@NicholasOOO](/NicholasOOO) for raising this. Our team doesn't use the visible molecule_id → structure pairs either, and we'd also prefer a level field.  As described above, th...
- **Community Member** (+0): My tests re-confirm this. Can something be done about this?  People who use the visible molecule ID will get a huge advantage, atleast in the open test cases  I'm optimistic that those types of predictions will fail in the hidden test cases, but it's fairly easy to just a run a c...
- **Community Member** (+2): +1 from our team. We don't use the visible molecule_id to structure pairs in any form, neither in submissions nor for diagnostics, and we'd welcome a remap or shuffle of the molecule_ids before the final rerun (ideally with the visible placeholder built from structures outside th...

### [#744470] Chasing medals with price ineligible sources
*Votes: 18 | Comments: 16 | Date: 2026-09-29*

**Key Findings & Context:**
> Well, pretty much this. Is using NIST dataset, gated weights etc. is going to be enforced somehow on gold medals? My Claude agent insist we need the NIST based model for better score 🤣 Since I don't care about the money, I might as well go and do it if I can (?) Who knows maybe this is what top teams do already 😁😅

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+6): I’m sorry, the NIST dataset is not permitted for solutions, any solution using or trained on NIST will be disqualified.  It is not freely available and its  license has restrictions on redistribution of itself or derivatives, including model weights....
- **Community Member** (+3): I understand that prize-eligible teams are required to disclose their methods, which should make it possible to review their data sources. However, is there any way to verify compliance for participants who are not eligible for prizes and are therefore not required to disclose th...
- **Community Member** (+9): How do you exactly plan to enforce this rule? We as participants don't have to disclose our solutions. In this sense, un-enforceable limitation actually put all the undisclosed results in qurstion (=every solution except those that disclose for price- and even 1st place don't hav...
- **Community Member** (+0): So if I understand it correctly (I'm new here), there is a possibility to cheat from inside kaggle's submission framework? How severe is it? If someone is just here for a medal, and they cheat, and they dont want to get caught and earn a medal, they wanna aim for landing outside ...
- **Community Member** (+5): How would the host review solutions? Restricting data usage is very hard....

### [#743974] All you need is a good ranker
*Votes: 23 | Comments: 3 | Date: 2026-09-28*

**Key Findings & Context:**
> When I started this competition, I thought the hardest issue would be finding the right molecule. Turns out, the bottleneck is the ranker. (of course, excluding Regime C)

For instance, my CV scores MRR @ 25 : 0.584 in Regime B and 0.846 in Regime A

Among them, number of molecules not in my top 25 are very low:- (below are CV MRR scores)

On an unrelated note, it's so sad to see instances where the true structure isnt part of my guesses, but the guesses my pipeline makes is so close

Also, feel free to use my ranker if it helps anyone : [https://claude.ai/artifact/VAQDJb8q7hLFyhv66hWMNL](https://claude.ai/artifact/VAQDJb8q7hLFyhv66hWMNL)

(It is still at Phase-0 and very unstable, so if anyone is using it, please share some feedback)

### [#745029] Understanding the actual task 
*Votes: 22 | Comments: 3 | Date: 2026-10-01*

**Key Findings & Context:**
> In the commercial world, this is called “understanding your customer.” ChatGPT is quite good at doing market research.

I looked more closely at the competition description and focused on the phrase “natural product structures” from mass spectra. I then asked ChatGPT to investigate what Enveda is really interested in.

does this look familiar to our 3 class of test set??

Here are some Enveda papers/resources you should not miss:

Butler et al., “MS2Mol: A transformer model for illuminating dark chemical space from mass spectra.”

Their goal is de novo prediction of natural metabolites that are not present in existing databases.

### [#741666] My Learning Roadmap for the Enveda CASMI 2026 Kaggle Competition
*Votes: 23 | Comments: 0 | Date: 2026-09-16*

**Key Findings & Context:**
> I’m still a beginner and learning step by step, and I’m not participating in this competition at the moment. However, I found the chemistry + data science side of this problem very interesting, so I decided to organize the topics and resources that I think could be useful for understanding this type of challenge.

I may misunderstand some parts, so corrections and recommendations from people working in computational chemistry, metabolomics, mass spectrometry, and machine learning are very welcome.

My goal here is not to present a solution, but to build a learning roadmap.

1️⃣ Cheminformatics

Understanding molecules computationally:

SMILES

### [#741745]  [0.339 Top 1 Solution] 4-Channel Mass-Shifted Analog Propagation & Neural Bayes Reranking
*Votes: 19 | Comments: 0 | Date: 2026-09-17*

**Key Findings & Context:**
> ### [0.339 Top 1] 4-Channel Mass-Shifted Analog Propagation & Neural Bayes Reranking

Hi everyone!

I wanted to share a post-mortem of my current approach for CASMI 2026 and some of the ideas that helped me move from:

**0.149 → 0.193 → 0.205 → 0.239→ 0.339**

At the moment, this places **me at Rank 1 on the Public Leaderboard**.

For anyone interested in the full implementation, I also published the main notebook here:

### [#744343] trick: train a smiles to MS/MS predictor too!
*Votes: 17 | Comments: 3 | Date: 2026-09-29*

**Key Findings & Context:**
> Old experienced kaggler will know what this is for! Maybe ChatGPT and Claude know too.

required for competition:

backward : generator(MS/MS, adduct) = smiles (de novo)

useful:

forward:  predictor(smiles, adduct)= MS/MS

(especially open-source predictor)

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): i remember a comment from a past competition that their winners generated 1TB or more training data...
- **Community Member** (+0): Enveda’s GrAFF-MS model Efficiently predicting high resolution mass spectra with graph neural networks [https://proceedings.mlr.press/v202/murphy23a/murphy23a.pdf](https://proceedings.mlr.press/v202/murphy23a/murphy23a.pdf)  note: "We train our model on the NIST-20 tandem MS libr...
- **Community Member** (+0): my orginal idea is some RSI harness  + forward/backward spectrum to molecule modelling. But it seems this idea has been partially explored  [https://github.com/ChrisTho23/dMSdMol](https://github.com/ChrisTho23/dMSdMol)     QOUTE: "Since models for both the forward (e.g., CFM-ID a...

### [#745070] Claude COT gives you a clue on how to get the solution
*Votes: 15 | Comments: 7 | Date: 2026-10-02*

**Key Findings & Context:**
> I am impressed (even chatgpt says it is impressive)

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): i hope to do something like peak --> fragment loss, then fragment --> assemble to molecule; instead of just directly ms/ms --> molecule...
- **Community Member** (+0): Yes, I'm thinking along the same lines. The end-to-end task of predicting SMILES is just too difficult. Instead, based on the fragment losses and the observed m/z values, we can predict the combinations of lost molecular formulas. Moreover, for classic substructures like benzene ...
- **Community Member** (+2): in summary: [(mz,intensity) … ] --> [(mz,intensity, fragment formula) …] --> smiles   hints:  fragment formula must obey mz is mass/charge value...

---

## 🏆 Name That LLM (`name-that-llm`)
**Domain**: NLP / Stylometry / Generative Model Attribution
**Topics Mined**: 10 highest-impact discussions

### [#749447] Will the winner just be whoever can get the most amount of extra training data?
*Votes: 72 | Comments: 18 | Date: 2026-10-14*

**Key Findings & Context:**
> Someone who has 1M training examples per model will find more patterns than someone with 100K training examples per model. Is paying model providers for data generation going to be the key to winning?

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+6): I agree with you.  I think, in a real-world context, there should be some degree of domain gap between the training data and the test data in this competition. Ignoring the cost,  the simplest way to eliminate this gap is to obtain the training data directly via LLMs' API....
- **Community Member** (+5): Could the organizers clarify whether participants are allowed to generate additional training data by calling LLM APIs themselves? The provided training set contains only around 150 unique prompts, which is clearly quite limited.  More specifically, how exactly will the "Reasonab...
- **Community Member** (+3): There is a $100 per month token opportunity on [https://www.kaggle.com/benchmarks](https://www.kaggle.com/benchmarks) for the different APIs...
- **Community Member** (+2): This won't be enough for the data extraction… Also if we were to waste personal money for this, why not Kaggle provide it and ringfence the assignment to external datasets [@jazivxt](/jazivxt)?...
- **Community Member** (+3): You can't prove that some team were using the exact data they say, unless you run their pipeline E2E and obtain v close weights. So idk how this will be invoked correctly...

### [#749629] 18-model wide response additional corpus
*Votes: 16 | Comments: 4 | Date: 2026-10-15*

**Key Findings & Context:**
> I collected an external response corpus for **Name That LLM**, organized as:

`id` · `prompt` · **18 model-name columns**

[**Dataset**](https://www.kaggle.com/datasets/olegzholobov/name-that-llm-response-corpus) · [**Overview notebook**](https://www.kaggle.com/code/olegzholobov/name-that-llm-wide-data-overview) · [**Seaborn NLP explorer**](https://www.kaggle.com/code/olegzholobov/name-that-llm-seaborn-nlp-explorer)

External view

Unique responses

Wide rows

### [#749382] How to get started + Competition's Official Discord
*Votes: 13 | Comments: 3 | Date: 2026-10-14*

**Key Findings & Context:**
> ### Information for newbies

Welcome!

**New to machine learning and data science?** No question is too basic or too simple. Feel free to start your own thread, or use this thread as a place to post any first-timer clarifying questions for the Kaggle community to help you with!

**New to Kaggle?** Take a look at a few videos to learn a bit more about [site etiquette](https://www.youtube.com/watch?v=aIus8si_Et0), [Kaggle lingo](https://www.youtube.com/watch?v=sEJHyuWKd-s), and [how to enter a competition using Kaggle Notebooks](https://www.youtube.com/watch?&v=GJBOMWpLpTQ). Publish and share your [models on Kaggle Models](https://www.kaggle.com/docs/models#publishing-a-model)!

**Participants under 18 years old:** If you are under 18 years old and want to participate in this competition, you need to submit a couple of forms:

Form #1: [Parent/Guardian consent for minor's use of kaggle.com](https://www.kaggle.com/guardian-consent-minor-use). You only have to fill this out once, and it is valid for any competitions on Kaggle. If you already filled this out in the past, you can move on to the next form.

### [#749455]   Reconstructed train prompts for all 150 prompt_ids (dataset + method)
*Votes: 13 | Comments: 0 | Date: 2026-10-15*

**Key Findings & Context:**
> I wanted to know what kind of prompts the host used, so I reconstructed them. Every `prompt_id` in train has one answer from each of the 18 models, so the 17–18 passages for a prompt are 18 different answers to the same hidden question. For each prompt I shuffled its passages, removed the model names, and gave them to Claude Sonnet 5. I asked it for the most likely original instruction plus some tags: topic, domain, task type, audience/style, length behaviour, shared structural features and a self-rated confidence. A second call looked over all 150 reconstructions together and summarised the likely generation protocol, including 20 example prompts in the same style.

The result is one row per `prompt_id`, so you can join it straight onto `train.csv`: [Name That LLM – Reconstructed Train Prompts](https://www.kaggle.com/datasets/pjmathematician/ntl-train-prompts-reconstructed). The script is included, and no passage text or labels are redistributed. These are LLM guesses, not ground truth. Average self-rated confidence is 0.81 (minimum 0.60), and the reconstructions I spot-checked read as very plausible.

**What the prompts look like**

**Pop-science, "explain X vividly":** 85 are explain-a-concept, 45 describe/narrate, 10 argue/opinion, 8 story/fiction, 1 compare.

**Domains:** physics 32, biology 28, philosophy 21, creative prose 16, mathematics 15, history 12, CS 10, psychology 6, economics 5, other 5.

**Topics are specific named things,** not broad subjects. Examples: Jevons paradox, Stern–Gerlach, Hilbert's hotel, slime mold recreating the Tokyo rail network, standing on a neutron star, split-brain confabulation, Dutch Hunger Winter epigenetics.

### [#749914] Could the Organizers Provide More Official Training Data?
*Votes: 6 | Comments: 2 | Date: 2026-10-16*

**Key Findings & Context:**
> Hi [@yanyao23](/yanyao23) [@martynaplomecka](/martynaplomecka) [@ashleyoldacre](/ashleyoldacre) , thanks for organizing this competition!

Any chance we could get more training data? 2,699 samples for 18 models feels like way too little.

With more data, participants could focus more on building better solutions instead of wasting time and money generating tons of data. Otherwise, this might end up being more of a synthetic data competition.

Of course, more data wouldn't make the competition perfectly fair. People with bigger budgets could still generate even more data, but at least it'd make spending money on synthetic data less important and give people with smaller budgets a real shot at winning.

And I imagine generating more samples wouldn't be that hard for the organizers?

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): Is generating your own data via model providers’  api even allowed under competition rules?  Hopefully they can clarify this soon....

### [#749511] Has anyone tried the PersonalLLM dataset for this competition? (namkoong-lab/PersonalLLM)？
*Votes: 6 | Comments: 0 | Date: 2026-10-15*

**Key Findings & Context:**
> Hi all,

Has anyone experimented with the PersonalLLM dataset on Hugging Face for this competition?

[https://huggingface.co/datasets/namkoong-lab/PersonalLLM](https://huggingface.co/datasets/namkoong-lab/PersonalLLM)

Quick summary:

~10k prompts

Each prompt has 8 responses from different models (GPT-4o, Claude 3 Opus/Sonnet, Gemini 1.5 Pro, Llama-3-70B, Mixtral, etc.)

### [#749494] You are absolutely right!
*Votes: 3 | Comments: 0 | Date: 2026-10-15*

**Key Findings & Context:**
> Guess who I am?

### [#749613] Clarification on self-generated data from model APIs
*Votes: 3 | Comments: 0 | Date: 2026-10-15*

**Key Findings & Context:**
> Hi, and thanks for hosting this competition.

I’d like to clarify how Section 6 (External Data and Tools) applies to data generated with the candidate models’ own APIs.

1) If a participant generates additional passages by querying some of the 18 candidate models through their paid APIs, is that allowed under the Reasonableness Standard, or does the data need to be publicly available to all participants?

2) If it is allowed, do we have to publish the generated dataset (e.g. on Kaggle Datasets or in the forum) before a certain date, or is that only required as part of the winners’ obligations in Section 2.8?

3)Is there a cost threshold the host considers “minimal cost” for API usage of this kind?

A clear answer would help everyone plan on equal terms, since several threads are already discussing whether the competition becomes pay-to-win.

### [#749545] Training Data Generation Paid
*Votes: 1 | Comments: 1 | Date: 2026-10-15*

**Key Findings & Context:**
> are we allowed to generate more training data via api calls using a small amount from our own pocket or everything has to be free? what about data generated through codex or claude subscriptions?

### [#749593] Random-split CV underestimates you here: 0.22 vs 0.37 – split by prompt_id
*Votes: 1 | Comments: 0 | Date: 2026-10-15*

**Key Findings & Context:**
> Quick finding that may save you some time.

Every prompt in train is answered exactly once by each of the 18 models (2,699 passages / 150 prompts). That makes a random K-fold misleading – but in the opposite direction from usual.

With a random split, the passage you validate on has its 17 "siblings" (same prompt, other models) in train. Topic words were seen only with other labels, so they push the prediction away from the true model.

Same TF-IDF + stylometry model, balanced accuracy:

StratifiedKFold (random): 0.217

StratifiedGroupKFold by prompt_id: 0.369

---

## 🏆 Gemma-4 Developer Agent (`gemma-4-developer-agent`)
**Domain**: Agentic Coding / AST Code Synthesis / Autonomous Systems
**Topics Mined**: 10 highest-impact discussions

### [#747519] Update on "Kaggle Error" Submissions & Queue Delays
*Votes: 33 | Comments: 82 | Date: 2026-10-08*

**Key Findings & Context:**
> Hi everyone,

I wanted to give an update on the long submission wait times and "Kaggle Error" failures many of you have been seeing over the past couple of days.

### What Happened

Due to very high submission volume using L4s, submission jobs have been facing long queue times before actually getting a machine to run. Submissions that waited >15h to start were being marked as “Kaggle Error” even if they eventually did run.

### What We Fixed

**Extended Queue Timeout:** We've drastically extended the queue allowance so submissions will no longer be timed out while waiting to run.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): I updated the packages in the wheelhouse yesterday to address some of the edge cases around tool calling and thought budgets. I'll make a more detailed post soon....
- **Community Member** (+12): Queue Wait Times: to even some of the load on the pool, we are implementing a pending submission limit (separate from the 1/day limit). If your team's previous submission is still scoring, you will need to wait until it finishes to submit again.  Do we have a guarantee that our s...
- **Community Member** (+2): It's possible, yes, that you will lose a daily submission this way. Unfortunately, even after doubling the number of L4 machines, we were still seeing the queue grow without bounds. Since, at the moment, it doesn't look like we'll be able to increase our supply of GPUs, we have t...
- **Community Member** (+2): Its fine for me 100% within some reasonable bounds. I dont want to end up in the situation, where my final submission will wait a week in a queue and wont even score before the deadline...
- **Community Member** (+1): yeah, this sounds better, i thought of it as limiting participants to max 3 simultaneous competitions (with no restrictions to joining though, only submissions gets capped)  GPU usage will only grow with time, kaggle needs to come up with something sooner than later.   this compe...

### [#743683] Rerunning Failed Submissions
*Votes: 21 | Comments: 98 | Date: 2026-09-26*

**Key Findings & Context:**
> Hi everyone,

Some submissions since yesterday were failing with `"Your notebook has requested more CPU, GPU or TPU resources than are available."` I believe I've resolved the issue, though please let me know if you're still having issues. I will rerun the affected submissions on Monday so that you won't be losing a submission.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): I think this is WAI. Your notebook needs to generate a submission file (`submission.zip`) before that submission can be scored. The workflow seems a little confusing, though. I will give feedback to the team....
- **Community Member** (+2): i think they forgot to mention here but like in arc agi 2, where the same gpus are provided, they too take double the time from your gpu quota...
- **Community Member** (+2): Hi everyone,  I'm going to pause the rescore until we can resolve the queueing for the L4x4 machines. I will get it going as soon as I can....
- **Community Member** (+0): Hi [@ryanholbrook](/ryanholbrook), our two submissions ended in ERROR with "A system error. Please try resubmitting…" — same pattern as reported here: • 56900501 (Oct 7) • 56927955 (Oct 8, v10: bf16+linear-LoRA, 5min/task) Both pass validate_directory locally. Could you include t...
- **Community Member** (+2): will submissions be returned or the deadline extended? my submission is "scoring" for 2 days and i cant submit until it ends....

### [#742807] Clarification on distillation from external LLMs
*Votes: 47 | Comments: 11 | Date: 2026-09-23*

**Key Findings & Context:**
> Hi organizers,

My understanding is that using external LLM APIs to generate synthetic training data has generally been allowed in recent Kaggle competitions. Given Section 2.6, I would expect this to be permitted here as well, subject to the competition’s external data and model requirements.

Could you clarify whether participants may use proprietary models, such as OpenAI Astra or Claude Opus 5.5, to generate code patches and agent trajectories for training Gemma specifically for this competition?

Regarding provider restrictions on developing competing models, my current understanding is that training a model solely for this competition may be permissible, while deploying or using the resulting model outside the competition could raise separate concerns. I recognize that participants remain responsible for complying with their providers’ terms.

With that distinction in mind, could you clarify:

Does the competition allow this form of distillation from proprietary API models? Are there any restrictions on which teacher models may be used?

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+6): Hi [@cnumber](/cnumber),  We are confering and will have an answer for you soon....
- **Community Member** (+3): any updates? :)...
- **Community Member** (+1): I'm looking at using distillation methods for open source models as well. I'm not against open sourcing my training data results from the distillation process as I have a tool that does this for Gemma 4 already developed. I'm curious what they decide on here!  Edit: Here is my KD...
- **Community Member** (+7): Hello and thank you for your question and your patience. As long as you are using those models in accordance with their model license terms, and the output you're using to submit to that competition doesn't 'conflict with the license requirement of the rules of this competition, ...

### [#748287] New Gemma 4 Models Available: 12B, E4B, and E2B
*Votes: 29 | Comments: 29 | Date: 2026-10-11*

**Key Findings & Context:**
> Hi everyone,

We've added support for [several smaller Gemma 4 variants](https://www.kaggle.com/models/google/gemma-4/other/). You can now use any of the following models for your agents:

`gemma-4-31b-it-qat-w4a16-ct`

`gemma-4-12b-it-qat-w4a16-ct`

`gemma-4-e4b-it-qat-w4a16-ct`

`gemma-4-e2b-it-qat-w4a16-ct`

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+0): Thanks for adding the smaller variants! We tried gemma-4-12b-it-qat-w4a16-ct (Other / v2) with the current wheelhouse (vllm 0.19.1, adk-submission 0.2.13, swegemma 0.2.11) and VllmServer (tool_call_parser and reasoning_parser gemma4, TP 4, bf16, max_model_len 32768). The server e...
- **Community Member** (+3): I'll update the Getting Started notebook on Monday to illustrate. The tl;dr is that you need to add:  ``` MODEL_VLLM_EXTRA_ARGS: dict[str, tuple[str, ...]] = {     'gemma-4-12b-it-qat-w4a16-ct': (         '--hf-overrides',         '{"architectures": ["Gemma4ForCausalLM"], "model_...
- **Community Member** (+0): The 12B still fails on wheelhouse v30: `KeyError: 'vision_embedder.patch_dense.weight'` .   `Gemma4ForCausalLM.load_weights` doesn't skip `model.vision_embedder.*`; adding `vision_embedder.` to its skip list fixes it.  MRE: error ([v2](https://www.kaggle.com/code/smartmanoj/gemma...
- **Community Member** (+1): [@ryanholbrook](/ryanholbrook) Thanks for the override. With it, the 12B still fails to start for us on the current wheelhouse (vllm 0.19.1): "Engine core initialization failed" during weight loading.  The cause seems to be the checkpoint itself. `gemma-4-12b-it-qat-w4a16-ct` (a ...
- **Community Member** (+4): Hi, here is a well-known issue, already fixed on v2.** upstream, but as we are using still v1.36  . Parallel agent is not gonna work : [https://github.com/google/adk-python/issues/7324#issuecomment-5868428151](https://github.com/google/adk-python/issues/7324#issuecomment-58684281...

### [#746480] submission is running for 15h. is this due to evaluation ?
*Votes: 21 | Comments: 37 | Date: 2026-10-07*

**Key Findings & Context:**
> since the time limit is 12h why the notebook is running for 15h.

is this normal?

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+3): it finished and now its saying kaggle error....
- **Community Member** (+2): it's the same for me 15h then 'Kaggle error'...
- **Community Member** (+4): same, and it shows 'kaggle error'...
- **Community Member** (+2): me too. 15h, then kaggle error....
- **Community Member** (+2): It happened with me too, the kegel error stuff....

### [#746250] Gemma 4 agent experiments: sampling, thinking, time limits, and tool ablations
*Votes: 30 | Comments: 10 | Date: 2026-10-06*

**Key Findings & Context:**
> I evaluated `gemma-4-31b-it-qat-w4a16-ct` using 32 B40 GPUs by CoreWeave, with one independent inference replica per GPU and tasks sharded across replicas to shorten evaluation turnaround.

All results below use the same 129-task local evaluation set. Resolved percentages are `resolved / 129 × 100`, including errored or incomplete tasks in the denominator. These are single-run observations with known local scoring limitations; small differences need repeat evaluations.

**TL;DR**

**Keep thinking and thought summaries enabled.** Temperatures 0.4 and 1.0 tied; I retained temperature 1.0, top-p 0.95, and a 4,096-token thinking budget. If you are post training, these parameters are good baseline.

**15 minutes was the best local quality-sweep setting, not a Kaggle submission budget.** It resolved 54/129 tasks with fewer task-hours and tokens than the 60-minute run which also resolved the same number of tasks. Shorter limits caused many timeouts but they anyway failed on the longer run. The Kaggle calibration at the end of this post supersedes this as the operational runtime guidance.

**Graph retrieval showed no observed benefit.** Semantic searches returned empty results, and overall quality did not improve.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+0): Thanks a lot for running and sharing this! This saves a lot of time and compute for us. I was running similar experiments but with limited compute and on fewer tasks, so it's amazing to see it scaled up.  You said you have access to compute for some more time. Could you run the t...
- **Community Member** (+1): Yes, I used the Blackwell RTX 6000 pro GPUs. Yes the reported time doesn't map to 4xL4 and for this reason, I am currently running a calibration test. I have been trying to use Kaggle's infra but stuck in queue for the last 2 days.   I just rented 4xL4 on modal for few hours to g...
- **Community Member** (+0): Thanks, looking forward to the calibration numbers.  Just to be clear about the 5.5 minutes: it is not a rule, it is 12 hours divided by about 120 tasks, minus setup. It assumes every task runs into the time cap, which is the safe worst case. In our scored runs, a 4.5-minute cap ...
- **Community Member** (+2): Thanks — the calibration is complete now.  I ran a stratified 12-task panel twice on Modal 4×L4 and once directly on Kaggle 4×L4 (TP=4, sequential agent). Kaggle processed 5.55M reported model tokens in 5,002s of LLM time: **900.8s per million tokens**, or **1,110 total tokens/s*...
- **Community Member** (+0): The E30 repeat going from 55 to 48 resolved tasks caught my attention. Do you have the task-level overlap between those runs? It would be useful to see whether the analyzer consistently fixes a particular kind of failure, even if the total only moves by one task. Thanks for shari...

### [#744807] Submission errors after the Sep 30 wheelhouse update
*Votes: 20 | Comments: 22 | Date: 2026-10-01*

**Key Findings & Context:**
> Hello [@ryanholbrook](/ryanholbrook),

My submission, 56722615, stopped after about 20 minutes with "Your notebook hit an unhandled error while rerunning your code." It's my first upload since the September 30 wheelhouse update. My earlier submissions scored normally, and this one validates and runs fine locally. Any idea what went wrong?

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): Similar issues with submission 56740906. Previous uploads before the wheelhouse update was all working fine...
- **Community Member** (+2): Same error here. Submission 56741570 (Oct 1, 02:33 UTC) failed about 7 minutes after submitting with "Your notebook hit an unhandled error while rerunning your code". The notebook only writes a 4-file submission.zip (agent.yaml, prompts/system.md, configs/sampling.yaml, eval_conf...
- **Community Member** (+2): Same here — submission 56739457 (Oct 1, 00:30 UTC): a prompt-only bundle (no adapters), validated locally against the official harness + wheelhouse on all 129 public tasks. It died with "Notebook Threw Exception". Our previous prompt-only submission (Sep 30, 04:21 UTC) scored nor...
- **Community Member** (+3): Same here: submission 56726945 (2026-10-01 00:06 UTC) ended with "Your notebook hit an unhandled error while rerunning your code" and no score. It validates locally with the Sep 30 wheelhouse.  [@ryanholbrook](/ryanholbrook) could you check what raised, and let us know when it is...
- **Community Member** (+1): Hi, my submission also failed with "Notebook Threw Exception" today (submitted around 04:45 UTC on 1 Oct). The same agent.yaml and prompt scored 0.05 on 30 Sep. Only eval_config.yaml values changed (max_time_minutes 10, max_tool_calls 60).  Two questions:  Is the wheelhouse issue...

### [#747915] Suggestion: Temporarily Pause Gemma 4 for 24 Days to Address the L4x4 Shortage
*Votes: 26 | Comments: 3 | Date: 2026-10-09*

**Key Findings & Context:**
> Background : [https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/747519](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/747519)

Thanks to the Kaggle team for working on this!

Would it make sense to temporarily pause the **Google Gemma 4 Developer Agent Competition** for 24 days, let **ARC-AGI-2** finish, and then resume Gemma 4 with its deadline extended accordingly?

This could allow both competitions to have sufficient L4x4 capacity, rather than having both struggle with extremely long queues and limited or reduced submissions.

I think staggering the two competitions would be a better solution for everyone.

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+2): or atleast make 1 submission per 3 days (as ssuggested by [1](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/747519#3536017) ) till the arc 2 completes...

### [#747168] Stronger models barely beat Gemma 4 31B in this harness — teacher comparison on 124 public tasks
*Votes: 19 | Comments: 3 | Date: 2026-10-08*

**Key Findings & Context:**
> Hi all — sharing an experiment in case it saves someone time/money.

**Question:** is our score limited by the model, or by the harness setup? If a much stronger

coding model (one that gets ~80% on SWE-bench Verified) runs through exactly the same agent

config, how much better does it do?

**Setup** (identical for all models)

Same submission YAML (sample prompt, `get_code_subgraph` removed), same harness (swegemma 0.2.7,

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+1): Thanks for sharing this. I had some results which I was thinking to compile and write up a discussion post but this is solid.   All I wanna add is that this is true. The model capability is restrained by the harness and compute capacity. I ran a similar setup with gpt4.1, gpt5, e...

### [#742882] Is the swegemma harness available for local evaluation?
*Votes: 14 | Comments: 12 | Date: 2026-09-23*

**Key Findings & Context:**
> HARNESS_README.md section 9 shows a local CLI command:

swegemma eval --tasks … --submission-dir starter_kit/sample_submission --sandbox docker

But the dataset has no swegemma, adk-submission, or adk-eval-core package, and no starter_kit folder. It only has docker/, sandbox/setup.py, and wheels/.

Will these packages be released (pip, GitHub, or a Kaggle dataset)?

If not, what is the recommended way to test a submission locally before submitting?

Thanks!

**Notable Follow-up Contributions & Clarifications:**
- **Community Member** (+10): Hi [@shimondanziger](/shimondanziger),  Here is a wheelhouse with the packages: [Gemma 4 Developer Agent Wheelhouse](https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse/data).  I'll post a notebook later today illustrating how to run everything on Kaggle....
- **Community Member** (+0): Hi [@ryanholbrook](/ryanholbrook), thanks for the wheelhouse! Is the "how to run everything on Kaggle" notebook still coming? Specifically:  Test dependencies: the public wheelhouse lacks some packages the task tests import (e.g. typing-inspection, inline-snapshot, dirty-equals, ...
- **Community Member** (+0): [@ryanholbrook](/ryanholbrook)  We're validating the public tasks with `swegemma==0.2.7` using the official Docker verification path and the public competition `wheels/`.  We've hit two environment issues and wanted to confirm whether the private scorer differs:  FastAPI tasks ca...
- **Community Member** (+2): [@ryanholbrook](/ryanholbrook) — follow-up with a completed Kaggle reproduction of the public evaluation environment problems.  Thank you for confirming that the evaluation metric validates a gold-patch submission at 100%. We are trying to reproduce reliable reference-patch valid...
- **Community Member** (+0): This may be a problem with the subprocess sandbox. I don't recall seeing these failures using the Docker sandbox. The private Docker sandbox uses the same base image but installs a different set of dependencies because the test issues come from a different set of repos.  I'll loo...

---
