# **Overview**

Join the **GPU MODE Hackathon**, sponsored by **AMD** (Advanced Micro Devices, Inc.), and push the boundaries of large language model (LLM) inference performance on leading open models—optimized for AMD Instinct™ MI355X GPUs.

This global, two-phase performance optimization challenge invites developers, researchers, and teams to showcase their expertise in GPU kernels and end-to-end inference optimization, competing for $1,100,000 in total cash prizes.

**​Phase 1: Qualifiers**  
*(March 6, 2026, 4PM PST – April 6, 2026, 11:59PM PST)*

Participants will optimize three critical GPU kernels, including MXFP4 MoE, MLA Decode, and MXFP4 GEMM. Teams will be ranked on a public leaderboard based on performance metrics defined in the official rules. The top 10 individuals or teams will advance to the Finals.

**Phase 2: Finals**  
*(April 7, 2026, 9 AM PST – May 15, 2026, 11:59PM PST)*

Finalists will focus on end-to-end inference optimization of selected LLM workloads, including DeepSeek-R1 and Kimi K2.5, with the goal of achieving breakthrough performance on standardized LLM inference benchmarks using AMD Instinct™ MI355X GPUs. 

​The competition will conclude with an awards ceremony on May 18, featuring senior AMD leadership and recognition of the top-performing teams.

**$1.1M Total Cash Prize**

In the qualifiers, the **top 10 individuals or teams** will each win $10K cash prize. Following the qualifiers with **$100,000 cash prize pool**, finalists will compete for the **$1,000,000 total cash prize pool** across two independent tracks, each focused on a specific model and inference stack. Finalists may compete in **one or both tracks**. 

​**Track 1: DeepSeek-R1-0528 FP4 \+ MTP**

Grand Prize: $350,000

​**Track 2\. Kimi K2.5 1T FP4**

Grand Prize: $650,000

​Winners may be invited to attend a special awards ceremony, however, attendance is not required to receive prizes.

All prizes, eligibility requirements, scoring methodology, evaluation criteria, and payment terms are governed by this document of rules, terms, and conditions. Participants are responsible for reviewing this document prior to submission.

**How to Participate**

* ​**Registration:** Register through [Luma](https://luma.com/cqq4mojz) page by Mar 30, 2026, 11:30 PM PST to be eligible to win prizes.  
* ​​**Eligibility**: Open to individuals or teams of up to three (3) members. Additional eligibility criteria apply as per rules, terms, and conditions in this document.  
* **AMD Developer Program:** Join AMD Developer program through [this link](https://www.amd.com/en/developer/ai-dev-program.html).  
* **Reference Kernels for the Qualifiers:** Reference kernels for the Phase 1 qualifiers are available [here](https://github.com/gpu-mode/reference-kernels/tree/main/problems/amd_202602).  
* **Community & Support**: ​​Join the [**GPU MODE Discord**](https://discord.com/invite/gpumode), and visit the [**amd-competition**](https://discord.com/channels/1189498204333543425/1359640791525490768) channel for announcements, technical discussions, Q\&A, and support throughout the competition.  
* **Submission Process**: Qualifier ​submissions must be made using the **Popcorn CLI** in accordance with the technical requirements and submission guidelines. Setup instructions are available here:  
  👉 [https://github.com/gpu-mode/popcorn-cli](https://github.com/gpu-mode/popcorn-cli)

**​Additional Resources**

​For learning resources, check out and subscribe to [GPU MODE YouTube channel](https://www.youtube.com/@GPUMODE/videos), where you can find weekly lectures from top voices in the ML community.

# **Rules** 

**Phase 1 – Qualifiers**

Submissions will be compared against their relative runtime/speed, and scores will be assigned according to the rubric below. The teams or individuals whose kernels deliver the highest performance above the best reference and closest to the published roofline shall win. Finalists will be conclusively determined only after the organizers have successfully reproduced the results independently.

* For each participant submitted kernel in each kernel problem, absolute speed of the kernel is measured. Based on the speed, each team or individual is ranked on the leaderboard.  
* Each team’s or individual’s aggregate score is calculated by applying the below maximum scores to each kernel problem  
  * MXFP4 MoE: 1,500 Points  
  * MLA decode: 1,250 Points  
  * MXFP4 GEMM: 1,000 Points  
* Participant score per kernel problem \= Max Points \* \[1 \- (rank / 20)\]. Rank \= 0,1,2,..18, 19\.  
* The aggregate score for each team or individual is calculated by summing the score for each of the three kernel problems, applying the above methodology.

The scoring metric for the leaderboard is the absolute runtime/speed of the participant’s kernel averaged over a large set of test cases – we will provide shape information for these test cases, but the input data itself will be sampled from a random distribution.

* Only the top 20 fastest kernels for each problem will be considered for aggregate score calculation. If a submission is not in the top 20, it gets zero points.   
* Submissions that do not beat the baseline will get zero points.  
* Geometric mean across all the benchmark cases, rounded to a particular decimal value will be considered for ranking.  
* In case of a tie, the earliest submitted kernel will be considered.    
* Each team will be considered as one participant in calculating aggregate score. If there are multiple entries from the same team, only the top scoring kernel in each problem will be considered for the aggregate score calculation for that team.   
* Top 10 teams or individuals with the highest aggregate score will advance to the Finals.

Problem details and reference implementations will be announced on GPU MODE [website](https://www.gpumode.com/) and [Discord](https://discord.com/invite/gpumode).   
    
Submissions for qualifiers can be made using the Popcorn CLI. Follow the setup and submission instructions here:  
👉 [https://github.com/gpu-mode/popcorn-cli](https://github.com/gpu-mode/popcorn-cli)  
   
**Phase 2 – Finals**

Objective: Optimize complete E2E model performance across two tracks or choose one of the two tracks  
   
**Track 1\. DeepSeek-R1-0528 FP4 \+ MTP**  
Performance will be evaluated as per below configurations:  
\- We provide a single node with 8× MI355, the maximum supported configuration is TP/EP \= 8\. However, developers may choose smaller TP and EP sizes, as long as the model fits, and the following criteria must still be satisfied.  
\- Concurrency: 4, 32, 128   
\- input\_length \= 8k, output Length \= 1k tokens

\- Framework: AMD **ATOM** or **SGLang**  
\- Accuracy Requirement: **GSM8K ≥ 0.93**

### \- Interactivity (= 1000.0 / median\_tpot) vs. total token throughput per GPU

* conc=128: interactivity ≥ 48 token/s/user AND throughput ≥ 6000 token/s/GPU  
* conc=32: interactivity ≥ 50 token/s/user AND throughput ≥ 3900 token/s/GPU  
* conc=4: interactivity ≥ 165 token/s/user AND throughput ≥ 1500 token/s/GPU

### \- E2E Latency (Median) vs. total token throughput per GPU

* conc=128: e2e latency ≤ 22 s AND throughput ≥ 6000 token/s/GPU  
* conc=32: e2e latency ≤ 18 s AND throughput ≥ 3900 token/s/GPU  
* conc=4: e2e latency ≤ 5 s AND throughput ≥ 1500 token/s/GPU

   
**Track 2\. Kimi K2.5 1T FP4**  
Performance will be evaluated as per below configurations:  
\- We provide a single node with 8× MI355, the maximum supported configuration is TP/EP \= 8\. However, developers may choose smaller TP and EP sizes, as long as the model fits, and the following criteria must still be satisfied.   
\- Concurrency: 4, 32, 128   
\- input\_length \= 8k, output Length \= 1k tokens  
\- Framework: AMD **ATOM** or **vLLM**  
\- Accuracy Requirement: **GSM8K ≥ 0.9325**

### \- Interactivity (= 1000.0 / median\_tpot) vs. total token throughput per GPU

* conc=128: interactivity ≥ 35 token/s/user AND throughput ≥ 5300 token/s/GPU  
* conc=32: interactivity ≥ 65 token/s/user AND throughput ≥ 4500 token/s/GPU  
* conc=4: interactivity ≥ 150 token/s/user AND throughput ≥ 1350 token/s/GPU

### \- E2E Latency (Median) vs. total token throughput per GPU

* conc=128: e2e latency ≤ 24.5 s AND throughput ≥ 5300 token/s/GPU  
* conc=32: e2e latency ≤ 14 s AND throughput ≥ 4500 token/s/GPU  
* conc=4: e2e latency ≤ 6 s AND throughput ≥ 1350 token/s/GPU

   
Ranking score and criteria for **each Track**:

1\. Total score structure

* There are 3 concurrency levels.  
* For each concurrency, the maximum score (SC) is 1000 points where:  
  * Token Throughput per GPU maximum score: 600 points  
  * Interactivity maximum score: 400 points  
* Therefore, the Phase 2 maximum final score (Final\_Score) is 3x1000 \= 3000 points.

2\. How score is calculated at each concurrency level

For each concurrency level, we collect all teams’ results and rank them on these metrics:

* Token Throughput per GPU \= concurrency \* (input\_length \+ output\_ length) / (mean\_TTFT \+ output\_length \* mean\_TPOT) / num\_GPUs\_you\_used, num\_GPUs\_you\_used \= 1,2,...,8. (note: Since we provide a single node with 8× MI355, the maximum supported configuration is TP/EP \= 8\. However, developers may choose smaller TP and EP sizes, as long as the model fits)  
* Interactivity \= 1000 / median\_TPOT

Each team gets points from metric sub-ranks:

2.1 Token Throughput per GPU sub-score

Throughput Points=600×(1−rank/10), rank \= 0, 1,2,3,...9

2.2 Interactivity sub-score

Interactivity Points=400×(1−rank/10), rank \= 0, 1,2,3,...9

Each concurrency-level score (SC) is calculated as the sum of Throughput Points and Interactivity Points at that concurrency level:

SC1 \= Throughput Points \+ Interactivity Points (concurrency \=4)

SC2 \= Throughput Points \+ Interactivity Points (concurrency \=32)

SC3 \= Throughput Points \+ Interactivity Points (concurrency \=128)

3\. Phase 2 final score and ranking

* The Phase 2 final Score (Final\_Score) is the sum of these three scores:  
* Final\_Score \= SC1 \+ SC2 \+ SC3

Teams are ranked based on the Final\_Score.

**4, Other Important criteria:**   
4.1. All submissions must be original work  
4.2. To qualify for a prize:  
\- You must meet performance targets at ALL concurrency levels (4, 32, 128\) for the track you choose  
\- You must achieve required accuracy thresholds  
\- Your code must be mergeable into AMD repositories (ATOM/vLLM/SGLang) within 2-4 weeks after selection as per the guideline provided below

**4.3. Guidelines for upstreaming to frameworks** 

Selected code must be **able to upstream to below selected frameworks within 2–4 weeks** after selection. Specifically:

* For **DeepSeek R1**, the code must be mergeable into **AMD ATOM or SGLang**.  
* For **Kimi K2.5**, the code must be mergeable into **AMD ATOM or vLLM**.

During Phase 2, AMD expects close collaboration to ensure the implementation aligns with upstream requirements and can be merged smoothly. Once the final deadline is reached, the code will enter the upstream process, which may take **an additional 2–4 weeks** for the pull request to be opened and merged into AMD ATOM or vLLM or SGLang.  
If after AMD’s technical assessment, the code is deemed **unlikely to be accepted upstream**, it will **not be eligible for the grand prize**. **Winners will be announced based on AMD team’s assessment on whether the submissions can be merged to vLLM/SGLang.** 

**4.4. Upstreaming to framework Criteria**

**For upstreaming to framework (SGLang or vLLM) repositories, code quality and maintainability must meet the standards of the upstream maintainers.**

* **Submissions must comply with the contribution guidelines of vLLM or SGLang:** please refer to those guidelines for detailed expectations  
* **AMD‑agnostic requirement**: Optimizations must be **AMD‑agnostic (No AMD‑only logic and No vendor lock‑in)** and acceptable to upstream communities (SGLang or vLLM).  
* **Dependency restrictions**: Submissions must **not introduce tightly coupled AMD‑specific dependencies** without clear fallback or downgrade paths.  
* **No modifications to core framework algorithms:** Avoid architectural changes that affect all vendors and are unlikely to be accepted upstream  
* **Upstream acceptance gate**: Optimizations that are clearly unlikely to be accepted by vLLM or SGLang upstream maintainers will be rejected

**Here is a link to AMD ATOM [https://github.com/ROCm/ATOM](https://github.com/ROCm/ATOM)**

Since this is AMD's own framework, Submissions can **introduce tightly coupled AMD‑specific dependencies, optimizations**.

4.5. For top submissions, AMD will build group chats and book regular meetings to keep process smoother and faster.

4.6. Submission Requirements: Submit the following information via email to ai\_dev\_contests@amd.com.  
1\. GitHub repository link with your optimized code  
2\. Pull Request (PR) describing your changes  
3\. Leaderboard results screenshot/data  
4\. Performance metrics documentation (throughput per GPU)  
5\. Technical documentation explaining your approach  
    
Leaderboard placement alone does not guarantee a prize. Winners are determined by meeting performance targets and code mergeability requirements. Prizes awarded after AMD verifies results. Performance targets must be met to win prizes. 

**How are Prizes Awarded?** 

After qualifiers, participants will compete in the finals round to win a total of $1,000,000 in cash prizes across two tracks, targeting different models and inference engines. 

Below are the prizes for each of two tracks. Teams can choose to submit for one or both tracks. 

**Track 1\.** DeepSeek-R1-0528 FP4 \+ MTP

- Grand Prize:  $350,000

**Track 2\.** Kimi K2.5 1T FP4

- Grand Prize:  $650,000

Participants may be invited to travel for a special awards ceremony, but attendance is not a pre-requisite for winning the prizes

In the event of a tie between any eligible entries, the tie is broken based on the judging criteria described above. The decisions of the judges are final and binding. If we do not receive a sufficient number of entries meeting the entry requirements, we may, in our sole discretion, select fewer winners than the number of prizes described above.If you are a potential winner, we will notify you by sending a message to the e-mail address, the phone number, or mailing address (if any) provided at the time of entry within seven (7) days following completion of judging. If the notification sent is returned as undeliverable, or you are otherwise unreachable for any reason, we may award the applicable prize to a runner-up. If there is a dispute as to who is the potential winner, we will consider the potential winner to be the authorized account holder of the e-mail address used to enter the Contest. If you are a potential winner, we may require you to sign an Affidavit of Eligibility, Liability/Publicity Release, and/or a W-9 tax form or W-8 BEN tax form within ten (10) days of notification. You are advised to seek independent counsel regarding the tax implications of accepting a prize. If you do not complete the required forms as instructed and/or return the required forms within the time period listed on the winner notification message, we may disqualify you and select a runner-up as the potential winner. Participants who are under 18 years old should provide a parent/guardian-signed waiver to allow participation and entry in the contest on the front end and this should be done for all minors who submit an entry.  If a minor wins, the parent or guardian should sign the AMD Declaration \- publicity and liability release on behalf of the minor. 

If you are confirmed as a winner of this contest, the following rules apply: 

- You may not exchange your prize for cash or any other merchandise or services. However, if for any reason an advertised prize is unavailable, we reserve the right to substitute a prize of equal or greater value.   
- You may not designate someone else as the winner. If you are unable or unwilling to accept a prize, we may award it to a runner-up.   
- You will be solely responsible for all applicable federal, state, and local taxes related to accepting the prize, if you choose to accept the prize. The final amount transferred to the winner will be exclusive of the applicable federal tax withholding.  
- If a prize is awarded to a project submitted by a team, the prize money will be distributed evenly among the team members.

# **Terms and Conditions**

**Registration and Eligibility:**  
 

- Luma event registration and approval is mandatory for prize eligibility.   
- To register, fill out the registration form on [Luma](https://luma.com/cqq4mojz). Registration is subject to verification and approval by AMD.   
- Registration to AMD Developer Program is a pre-requisite for prize eligibility. You can register via below link until May 11th to be eligible. [https://www.amd.com/en/developer/ai-dev-program.html](https://www.amd.com/en/developer/ai-dev-program.html)  
- The challenge is open to individuals and teams of up to three (3) members.   
- All team members must register using their legal name and contact details, and provide the same team name.   
- Participants must be 18 years or older or of the age of majority in their country as of registration start date.  
- Participants under 18 must present a parent/guardian-signed waiver to allow participation and entry in the contest.   
- All participants must:  
  - Have a valid Discord ID  
  - Have a valid GitHub ID   
- For questions: email: ai\_dev\_contests@amd.com

**Not eligible:**

- Individuals who are nationals of Belarus, Burma, Cuba, Iran, North Korea, Russia, Syria, Sudan, Venezuela, Crimea, Donetsk, Luhansk, or any country subject to U.S. export controls or sanctions, regardless of legal residency, are ineligible to participate. This includes individuals listed on the U.S. Department of Commerce’s Bureau of Industry and Security (BIS) Entity List or the U.S. Department of the Treasury’s Office of Foreign Assets Control (OFAC) Specially Designated Nationals (SDN) list, as well as those employed by or representing entities on these lists.  
- Employees of the Sponsor, its affiliates, subsidiaries, and agents, along with their immediate family members (defined as parents, children, siblings, spouse, or domestic partner) and household members, are not eligible.

**Code of Conduct:**

Entries may NOT contain ANY of the following content: 

- Content that is sexually explicit, profane, or pornographic.   
- Content that is unnecessarily violent or derogatory of any ethnic, racial, gender, sexual orientation, gender identity, religious, professional, or age group.   
- Content that promotes illegal drugs, firearms/weapons (or the use of any of the foregoing) or a particular political agenda.   
- Content that defames, misrepresents or contains disparaging remarks about any third-party, including individuals or organizations.   
- Content that communicates messages or images inconsistent with the positive images and/or goodwill to which we wish to associate.   
- Content that violates any federal, state, or local law.   
- Harassment, discrimination, or inappropriate behavior will result in disqualification.   
- AMD reserves the right to disqualify any participant or team at its sole discretion.

**For all Entries:** 

Any language or information included in a participant’s registration or submission is deemed to be part of the participant’s entry, and participant gives AMD, its designees, successors, assigns, and licensees a royalty-free, irrevocable, non-exclusive worldwide license to use, reproduce, modify, publish, create derivative works from, and display the entry and all elements embodied therein, along with the participant’s name and/or social media account handle(s), in any manner, in whole or in part, on a worldwide basis, and to incorporate it into other works, in any form, media or technology now known or later developed, including for advertising, promotional, marketing and other purposes, without further payment or consideration, notification or permission. All Entries become the property of AMD, and none will be returned. If requested, participant will sign any documentation required for Sponsor or its designees, successors, assignees, and licensees to make use of the non-exclusive rights participant is granting to AMD. Released Parties (as defined below) are not responsible for lost, late, stolen, incomplete, inaccurate, invalid, un-intelligible, garbled, delayed, or misdirected posts, all of which will be void. 

**Release:** 

By participating, Participant agrees to release and hold harmless AMD, and each of its respective subsidiaries, affiliates, suppliers, distributors, advertising/promotion agencies, and each of their respective parent companies and each such company’s officers, directors, employees and agents (collectively, the “Released Parties”) from and against any claim or cause of action, including, but not limited to, damage to or loss of property, arising out of participation in the Challenge or receipt or use or misuse of any prize. 

**Privacy:** 

Participants acknowledge and understand that all personal information submitted as part of the challenge will be collected and processed by AMD for the purpose of managing the challenge in accordance with its Privacy Notice, Participant can read more about their rights, how AMD handles participants’ personal information, and how to contact AMD in its Privacy Notice. 

**Publicity:** 

Except where prohibited by applicable law, participation in the developer challenge constitutes each winner’s consent to AMD’s use of the winner’s name, city, state, province or county, and country, likeness, photograph, statements made by the winner  
about the challenge, about AMD, and/or prize information for the challenge in any media without further payment or consideration, including, but not limited to, posting winner lists online. All submissions become the property of AMD and none will be returned. 

**General Conditions:** 

Sponsor reserves the right to terminate, amend, suspend, or modify the challenge in whole or in part, at any time and without notice or obligation, if in AMD’s sole discretion, any factor interferes with its proper conduct as contemplated herein. Without limiting the generality of the foregoing, if, for any reason, the challenge is not capable of running as planned, including infection by computer virus, bugs, tampering, unauthorized intervention, fraud, technical failures, or any other causes beyond the control of AMD, which corrupt or affect the administration, security, fairness, integrity or proper conduct of the challenge, AMD reserves the right, in its sole discretion, to disqualify any individual or team who tampers with the entry process. Any attempt by any person to deliberately undermine the legitimate operation of the challenge may be a violation of criminal and civil law, and should such an attempt be made, AMD reserves the right to fully seek damages from any such person permitted by law. AMD’s failure to enforce any term of these rules shall not constitute a waiver of that provision or of any other provision of these rules. The invalidity or unenforceability of any provision of these rules shall not affect the validity or enforceability of any other provision. If any provision of the rules is determined to be invalid or otherwise unenforceable, then the rules shall be construed in accordance with the terms as if the invalid or unenforceable provision was not contained therein. 

**Limitations of Liability:** 

The Released Parties are not responsible, to the extent permitted by law, for: (1) any incorrect or inaccurate information, whether caused by participant, printing errors, or omission or by any of the equipment or programming associated with or utilized in the challenge; (2) technical failures of any kind, including, but not limited to malfunctions, interruptions, or disconnections in phone lines or network hardware or software; (3) unauthorized human intervention in any part of the entry process or the challenge; (4) technical or human error which may occur in the administration of the challenge or the processing of entries; or (5) any injury or damage to person or property which may be caused, directly or indirectly, in whole or in part, from participation in the challenge or receipt or use or misuse of any prize. If for any reason an entry is confirmed to have been erroneously deleted, lost, or otherwise destroyed or corrupted, participant or the team’s sole remedy is another entry in the contest, provided that if it is not possible to submit another entry due to discontinuance of the challenge, or any part of it, for any  
reason, AMD, in its sole discretion, may elect to hold a random drawing from among all eligible entries or, as the case may be, from among eligible entries received up to the date of discontinuance for any or all of the prizes offered herein. No more than the stated amount of prizes will be awarded. 

NOTHING IN THESE RULES SHALL DISCLAIM, LIMIT, OR EXCLUDE LIABILITY FOR ANY LIABILITY THAT MAY NOT BE DISCLAIMED, LIMITED, OR EXCLUDED PURSUANT TO APPLICABLE LAW. 

**Disputes:** 

Except where prohibited, participants agree that: (1) any and all disputes, claims and causes of action arising out of or connected with this challenge or any prize awarded shall be resolved individually, without resort to any form of class action, and exclusively by the United States District Court for the Western District of Texas or the appropriate Texas State Court located in Travis County, Texas; (2) any and all claims, judgments and awards shall be limited to actual out-of-pocket costs incurred, including costs  
associated with entering this challenge, but in no event attorneys’ fees; and (3) under no circumstances will participant be permitted to obtain awards for, and participant hereby waives all rights to claim, indirect, punitive, incidental and consequential damages and any other damages, other than for actual out-of-pocket expenses, and any and all rights to have damages multiplied or otherwise increased. 

**Winners List:**

The Winners List will be available in English in GPU MODE’s Discord channel under amd-competition channel, after the close of the contest. Inquiries for the winners list must be received within fourteen (14) days of the close of the contest. Inquiries received after this time will not be honored.

**For EU Residents Only:** 

THE ABOVE CHOICE OF LAW MAY NOT RESULT IN DEPRIVING THE PARTICIPANTS OF THE PROTECTION UNDER MANDATORY STATUTORY PROVISIONS THAT CANNOT BE WAIVED UNDER THE LAW WHICH WOULD HAVE BEEN APPLICABLE IN THE ABSENCE OF THIS CHOICE OF LAW. FOR PARTICIPANTS NOT RESIDING IN THE EUROPEAN UNION, any and all claims, judgments and awards shall be limited to actual out-of-pocket costs incurred, including costs associated with entering this Challenge, but in no event attorneys’ fees, and under no circumstances will Participant be permitted to obtain awards for, and Participant hereby waives all rights to claim, indirect, punitive, incidental, and consequential damages and any other damages, other than for actual out-of-pocket expenses, and any and all rights to have damages multiplied or otherwise increased. ANY DEMAND FOR OUT-OF-POCKET COMPENSATION MUST BE FILED WITHIN ONE (1) YEAR FROM THE END OF THE CHALLENGE PERIOD, OR IN ACCORDANCE WITH THE LAW OF LIMITATIONS AS APPLICABLE LOCALLY, OR THE CAUSE OF ACTION SHALL BE FOREVER BARRED. All issues and questions concerning the construction, validity, interpretation and enforceability of these Rules, or the rights and obligations of the Participant and AMD in connection with the Contest, shall be governed by, and construed in accordance with, the laws of the State of Texas without giving effect to any choice of law or conflict of law rules (whether of the State of Texas or any other jurisdiction), which would cause the application of the laws of any jurisdiction other than the State of Texas. Some jurisdictions do not allow for limitations of certain remedies or damages and so this provision may not apply to you. 

THE ABOVE CHOICE OF LAW MAY NOT RESULT IN DEPRIVING THE PARTICIPANTS OF THE PROTECTION UNDER MANDATORY STATUTORY PROVISIONS THAT CANNOT BE WAIVED UNDER THE LAW WHICH WOULD HAVE BEEN APPLICABLE IN THE ABSENCE OF THIS CHOICE OF LAW. FOR PARTICIPANTS NOT RESIDING IN THE EUROPEAN UNION, any and all claims, judgments and awards shall be limited to actual out-of-pocket costs incurred, including costs associated with entering this Challenge, but in no event attorneys’ fees, and under no circumstances will Participant be permitted to obtain awards for, and Participant hereby waives all rights to claim, indirect, punitive, incidental, and consequential damages and any other damages, other than for actual out-of-pocket expenses, and any and all rights to have damages multiplied or otherwise increased. ANY DEMAND FOR OUT-OF-POCKET COMPENSATION MUST BE FILED WITHIN ONE (1) YEAR FROM THE END OF THE CHALLENGE PERIOD, OR IN ACCORDANCE WITH THE LAW OF LIMITATIONS AS APPLICABLE LOCALLY, OR THE CAUSE OF ACTION SHALL BE FOREVER BARRED. All issues and questions concerning the construction, validity, interpretation and enforceability of these Rules, or the rights and obligations of the Participant and AMD in connection with the Contest, shall be governed by, and construed in accordance with, the laws of the State of Texas without giving effect to any choice of law or conflict of law rules (whether of the State of Texas or any other jurisdiction), which would cause the application of the laws of any jurisdiction other than the State of Texas. Some jurisdictions do not allow for limitations of certain remedies or damages and so this provision may not apply to you. 

**For Germany Residents Only:** 

AMD will be liable for any culpable breach of essential contractual obligations. Essential contractual obligations are contractual obligations that need to be fulfilled to permit proper execution of these Rules and that may regularly be relied upon by the participant. AMD’s liability will otherwise be limited to gross negligence and willful misconduct. In the event of any liability on the part of AMD due to a slightly negligent breach of essential contractual obligations or slightly negligent misconduct on the part of simple vicarious agents, such as the Administrator, the AMD’s and the Administrator’s respective subsidiaries, affiliates, suppliers, distributors, advertising/promotion agencies, and prize suppliers, and each of their respective parent companies and each such company’s officers, directors, employees and agents, AMD’s liability will be limited to typically foreseeable damages. The above limitations of liability will not affect any mandatory statutory liability, in particular AMD’s liability in connection with the loss of life, bodily injury or illness. 

**For UK Residents Only:** 

NOTWITHSTANDING THIS SECTION (LIMITATION OF LIABILITY), NOTHING IN THESE RULES SHALL BE CONSTRUED TO LIMIT OR EXCLUDE ANY LIABILITY OF THE AMD FOR FRAUD, DEATH, OR PERSONAL INJURY CAUSED BY AMD OR PARTICIPANTS’ NEGLIGENCE. No term herein is enforceable by any person who is not a party under the Contracts (Rights of Third Parties) Act 1999 or otherwise, excluding AMD.  

TO THE EXTENT PERMITTED BY LAW, ANY CLAIMS OR DISPUTES RELATING TO THIS CHALLENGE, THE PRIZE OR THESE RULES MUST BE BROUGHT WITHIN ONE (1) YEAR OF THE TIME THE CAUSE OF ACTION OCCURRED.