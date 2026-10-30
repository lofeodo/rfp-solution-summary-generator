# Solution summary: TR202504 RFP Using AI /ML to Write Legal Land Descriptions

- **Source:** data/rfps/missouri.pdf
- **Run:** missouri
- **Generated:** 2026-10-30T19:42:13.945577+00:00
- **Model:** deepseek:deepseek-flash

## Problem statement

### Client situation

- The Missouri Highways and Transportation Commission (MHTC) is the issuing body, and the study is performed for MHTC and the Missouri Department of Transportation (MoDOT), with MoDOT's Right of Way staff reviewing drafts. ((A) Request for Proposal, p. 5 [S8.1]; (B) Background, p. 5 [S9.1])
- The work is coordinated by the Research Unit of MoDOT's Construction and Materials Division, and the Offeror must fully coordinate its activities with that division. (Front matter, pp. 1-2 [S1.1]; (A) MHTC's Representative, p. 13 [S49.1])
- MoDOT's Right of Way staff must produce property descriptions that accurately define the land areas or rights acquired, conveyed or leased, reciting specific rights when less than fee simple title. ((B) Background, p. 5 [S9.1])
- Realty rights acquired or conveyed by MHTC must be described by metes and bounds unless the property is acquired in its entirety, in which case the description must be written exactly as it appears on the last deed of record. ((B) Background, p. 5 [S9.1])
- Descriptions prepared for MHTC must meet the requirements of MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2. ((B) Background, p. 5 [S9.1])
- Before a general warranty deed, quitclaim deed or similar document is presented to the grantor, a professional land surveyor must review the property description to verify the parcel matches the right of way plans and that those plans match the surveyor's survey information. ((B) Background, p. 5 [S9.1])
- Writing these legal land descriptions is long and tedious work, which is the pain point driving the research. ((B) Background, p. 5 [S9.1])
- The business driver is to determine the usefulness of Artificial Intelligence (AI) and Machine Learning (ML) for producing a "first draft" legal land description (LLD) from MHTC parameters that MoDOT Right of Way staff could review and edit. ((B) Background, p. 5 [S9.1])

### Goal

- The client wants a research study, TR202504 "Using AI/ML to Write Legal Land Descriptions," that determines whether AI/ML can generate a first draft of a legal land description using MHTC parameters for review and editing by MoDOT Right of Way staff. ((A) Request for Proposal, p. 5 [S8.1]; (B) Background, p. 5 [S9.1])
- The contract period is 15 months, with the project schedule estimated to start November 1, 2024 and the final invoice due and contract ending February 2, 2026. ((D) Contract Period and Budget, p. 5 [S11.1]; (G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- Task 2 requires a thorough literature search and review of other state DOT practices using AI/ML for right-of-way purposes. (Task 2: Literature Review, p. 8 [S20.1])
- Task 3b requires the Offeror to name the program used to develop the LLDs before proof-of-concept work begins, and MoDOT Information Systems must approve it before Task 3c proceeds. (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- Task 3c requires a proof-of-concept demonstration of how the technology creates draft legal land descriptions on a variety of properties, with MoDOT reviewing the drafts and giving improvement feedback. (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1])
- Task 4 requires the Offeror to train ROW staff on the finalized system and supply a user manual for staff reference. (Task 4: Training and User Manual, p. 9 [S24.1])
- Task 5 requires a draft Synthesis Report and Research Summary plus supporting documentation, and Task 6 requires a final report with all findings, a 1-2 page research summary stating objectives, findings and conclusions, and a presentation for MoDOT staff. (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1]; Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- Task 1 requires a kick-off meeting, quarterly project status meetings with minutes, and a Data Management Plan submitted within 2 weeks after kick-off. (Task 1: Project Management, p. 8 [S19.1])

### Success criteria

- Proposals are due by email to MoDOTResearchRFP@modot.mo.gov by August 21, 2024 at 10 a.m. Central, with notification of receipt sent by noon the same day. (Front matter, pp. 1-2 [S1.1]; (E) RFP Schedule, pp. 5-6 [S12.1])
- All questions and comments must go only to MoDOTResearchRFP@modot.mo.gov by July 17, 2024 at 4 p.m. Central, and contacting MoDOT employees by other methods is prohibited and cause for disqualification. ((E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])
- MoDOT posts its responses to questions publicly on July 31, 2024, and notifies submitters about project selection or interviews on September 18, 2024. ((E) RFP Schedule, pp. 5-6 [S12.1])
- After a responsiveness check, proposals are evaluated against criteria established by the Technical Advisory Committee, and the award goes to the Offeror providing the best proposal; the RFP does not list the specific criteria or weights. ((1) Evaluation Factors, p. 11 [S41.1])
- The Work Plan must be narrative, limited to ten (10) pages with font no smaller than 12 points (excluding attached forms and resumes), must cover all items in Section 2, and must recognize MoDOT's ultimate authority to approve work plans. ((2) Work Plan, p. 10 [S36.1])
- Proposals must be one combined PDF in a fixed order: Proposal Submission Form, optional one-page cover letter, body of proposal (work plan and schedule), Personnel, Organization's Project Experience, Team Member Experience, and Organization's Client References. ((5) References, p. 11 [S39.1])
- The proposal must identify experience in offering the requested services during the past three years and give at least three client references with name, title and telephone number from the past three years. ((4) Experience, p. 11 [S38.1]; (5) References, p. 11 [S39.1])
- The Offeror must present how the AI/ML will create draft LLDs on April 25, 2025 for MoDOT feedback, deliver the manual and ROW training by July 25, 2025, complete the interim presentation by September 15, 2025, and deliver the draft final report, summary and user manual by November 3, 2025. ((G) Project Schedule, p. 7 [S15.2])

### Constraints

- Services are capped at a not-to-exceed amount of $175,000, and the cost estimate must be entered on the Section (4) Price Page with line items for Salaries, Benefits, Operating Expense, Facilities and Administration (F&A) Cost, Miscellaneous and Total. ((A) Services, p. 8 [S17.1])
- Applications must be built on approved technologies: .NET 6.0 or above (or a currently supported .NET Framework 4.8 or above where specifically needed), with web applications using MVC, Razor Pages or Web API, and approved languages limited to C#, JavaScript, CSS, HTML and Python, with Python reserved for ESRI scripts and small one-time uses unless the IS Best Practices Review Team approves larger use. ((Y) Information Technology, pp. 17-18 [S73.1])
- Vendors may not use third-party tools or software that would place a licensing responsibility on MoDOT without prior review and approval by the Information Systems Best Practices Review Team (BRPT) and IS management. ((Y) Information Technology, pp. 17-18 [S73.1])
- Applications must be web-based browser applications requiring no client-side software beyond a modern browser (no Java Applets, no Silverlight), must run on Oracle 19C or a supported SQL Server version, and must meet WCAG 2.1 AA and the State of Missouri Accessibility Standard. ((Y) Information Technology, p. 18 [S73.2])
- No Personal Identifiable Information (PII) may be stored in any database table without a specific business need, and all stored PII requires approval from the IS Cyber Security Team. ((Y) Information Technology, p. 18 [S73.2])
- All documents, reports and exhibits the Offeror produces at MHTC's direction, and information supplied by MHTC, remain MHTC property, and the Offeror must keep working papers available to MHTC and the Missouri State Auditor for three years after final payment. ((Q) Ownership of Reports, p. 16 [S65.1]; (U) Maintain Papers, p. 16 [S69.1])
- The Data Management Plan must describe anticipated data formats and how platform-independent, non-proprietary formats will be used to ensure maximum future utility of the data. (Task 1: Project Management, p. 8 [S19.1])
- Award is subject to a post-award negotiated contract that MHTC may cancel if terms cannot be agreed, and the RFP requires 10% MBE and 5% WBE participation targets, an E-Verify affidavit (Exhibit A), lawful-presence affidavits for sole proprietorships and partnerships (Exhibit B), and insurance of $500,000 per person and $3,000,000 per occurrence for general and automobile liability plus Missouri workers' compensation. (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1]; (G) MBE/WBE Participation Encouraged, p. 14 [S55.1]; (K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1]; (L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1]; (X) Insurance, p. 17 [S72.1])

## Requirements

120 requirements: 101 mandatory, 16 desired, 3 optional.

### Functional (20)

- **R010** (mandatory) The bidder must be a qualified organization proposing to conduct the TR202504 "Using AI/ML to Write Legal Land Descriptions" study for the MHTC and Missouri Department of Transportation (MoDOT).
  > "This document constitutes an RFP from qualified organizations to conduct the TR202504, "Using AI/ML to Write Legal Land Descriptions" study for the MHTC and Missouri Department of Transportation (MoDOT)." ((A) Request for Proposal, p. 5 [S8.1])
- **R014** (mandatory) The property description must recite the specific rights being acquired, conveyed or leased when those rights are less than fee simple title.
  > "The description must recite specific rights being acquired, conveyed, or leased, if such rights are less than fee simple title" ((B) Background, p. 5 [S9.1])
- **R015** (mandatory) The research project must determine the usefulness of Artificial Intelligence (AI) and Machine Learning (ML) to develop a "first draft" of the legal land description (LLD) using the MHTC parameters.
  > "The goal of this research project is to determine the usefulness of Artificial Intelligence (AI) and Machine Learning (ML) to develop a "first draft" of the legal land description (LLD) using the MHTC parameters." ((B) Background, p. 5 [S9.1])
- **R024** (mandatory) The Offeror must demonstrate the AI writing a legal land description. _(merged from R036, R054)_
  > "Demonstration of AI writing a legal land description" (Task Deliverables, p. 6 [S14.1]; (G) Project Schedule, p. 7 [S15.2]; Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1])
- **R026** (mandatory) The Offeror must deliver a draft report, summary, and user manual. _(merged from R039)_
  > "Draft report, summary, and user manual" (Task Deliverables, p. 6 [S14.1]; (G) Project Schedule, p. 7 [S15.2])
- **R027** (mandatory) The Offeror must deliver a final report, summary, presentation, and user manual. _(merged from R040)_
  > "Final report, summary, presentation, and user manual" (Task Deliverables, p. 6 [S14.1]; (G) Project Schedule, p. 7 [S15.2])
- **R032** (mandatory) E-mail and phone communications with MoDOT contacts are required on a monthly basis to provide ongoing updates of progress. _(merged from R033)_
  > "E-mail and phone communications with MoDOT contacts are required to provide ongoing updates of progress." ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- **R044** (mandatory) The Offeror must facilitate a kick-off meeting with MoDOT to review the work plan, scope and schedule and to establish a protocol for regular ongoing communications and coordination with the team. _(merged from R034)_
  > "The Offeror will facilitate a kick-off meeting with MoDOT to review the work plan, scope, and schedule; and establish a protocol for regular ongoing communications and coordination with the team." (Task 1: Project Management, p. 8 [S19.1]; (G) Project Schedule, p. 7 [S15.2])
- **R045** (mandatory) The Offeror must schedule and conduct quarterly project status meetings reviewing progress for the previous period and anticipated work for the next period, held in person or online.
  > "The Offeror will schedule and conduct quarterly project status meetings to review progress for the previous period and anticipated work for the next period." (Task 1: Project Management, p. 8 [S19.1])
- **R046** (mandatory) The Offeror must develop minutes for the kick-off meeting and for each quarterly status meeting. _(merged from R023)_
  > "The Offeror will also develop minutes for the kick-off meeting and each of the quarterly status meetings." (Task 1: Project Management, p. 8 [S19.1]; Task Deliverables, p. 6 [S14.1])
- **R047** (mandatory) The finalized work plan must detail implementation of the project tasks as well as the resources and schedule required to carry them out.
  > "The finalized work plan will detail implementation of the following tasks as well as the resources and schedule required to carry them out." (Task 1: Project Management, p. 8 [S19.1])
- **R051** (mandatory) The vendor must conduct a thorough literature search and review of other state DOT practices using AI/ML for right-of-way (ROW) purposes.
  > "A thorough literature search and review of other state DOT practices using AI/ML for ROW purposes conducted." (Task 2: Literature Review, p. 8 [S20.1])
- **R055** (mandatory) Once the system has been developed and finalized, the Offeror must provide training to ROW staff. _(merged from R025, R037)_
  > "Once the system has been developed and finalized, the Offeror will provide training to ROW staff." (Task 4: Training and User Manual, p. 9 [S24.1]; Task Deliverables, p. 6 [S14.1]; (G) Project Schedule, p. 7 [S15.2])
- **R056** (mandatory) The training must include a user manual for staff to reference.
  > "The training will also have a user manual for staff to reference." (Task 4: Training and User Manual, p. 9 [S24.1])
- **R057** (mandatory) The Offeror must prepare a draft Synthesis Report and Research Summary along with all accompanying documentation identified as beneficial during the study. _(merged from R061)_
  > "The Offeror will prepare a draft Synthesis Report and Research Summary along with all accompanying documentation identified as beneficial during the study." (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1]; Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **R062** (mandatory) The Offeror must provide a 1-2 page research summary stating the project objectives, findings and conclusions. _(merged from R058)_
  > "The Offeror will provide a 1-2 page research summary that states the project objectives, findings and conclusions." (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **R063** (mandatory) The Offeror must provide a presentation for MoDOT staff summarizing important or significant details of the project.
  > "A presentation for MoDOT staff summarizing important or significant details of the project must be provided." (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **R065** (mandatory) The Offeror must consult MHTC's representative regarding any concerns involved with the administration of the services provided under this RFP.
  > "The Offeror will consult MHTC's representative regarding any concerns involved with the administration of the services provided pursuant to this RFP." ((C) Administration of Program, p. 9 [S27.1])
- **R101** (mandatory) The Offeror shall fully coordinate its activities for MHTC with those of the Construction and Materials Division.
  > "The Offeror shall fully coordinate its activities for MHTC with those of the Construction and Materials Division." ((A) MHTC's Representative, p. 13 [S49.1])
- **R102** (mandatory) The Offeror shall make advice and information on matters covered by the Agreement available to the Construction and Materials Division throughout the effective period of the Agreement.
  > "advice and information on matters covered by the Agreement shall be made available by the Offeror to the Construction and Materials Division throughout the effective period." ((A) MHTC's Representative, p. 13 [S49.1])

### Technical (18)

- **R011** (mandatory) Property descriptions prepared on behalf of the MHTC must be prepared in a manner that meets the requirements outlined in the MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2.
  > "Property descriptions prepared on behalf of the MHTC must be prepared in a manner that meets the following requirements as outlined in the MoDOT Engineering Policy Guide (EPG)" ((B) Background, p. 5 [S9.1])
- **R012** (mandatory) Realty rights acquired or conveyed by the MHTC must be described using the metes and bounds method, unless the property is acquired in its entirety.
  > "realty rights being acquired or conveyed by the MHTC must be described using the metes and bounds method, unless the property is acquired in its entirety" ((B) Background, p. 5 [S9.1])
- **R013** (mandatory) When a property is acquired in its entirety, the property description must be written exactly as it appears on the last deed of record for the subject property.
  > "When acquiring a property in its entirety, the property description shall be written exactly as it appears on the last deed of record for the subject property." ((B) Background, p. 5 [S9.1])
- **R049** (mandatory) The Data Management Plan must describe the anticipated format(s) the Offeror's data and related files will use.
  > "The plan will describe the anticipated format(s) your data and related files will use." (Task 1: Project Management, p. 8 [S19.1])
- **R050** (desired) The Data Management Plan should address how the Offeror will use platform-independent and non-proprietary formats to ensure maximum future utility of the data.
  > "The DMP should address how the Offeror will use platform-independent and non-proprietary formats to ensure maximum utility of the data in the future." (Task 1: Project Management, p. 8 [S19.1])
- **R131** (mandatory) All applications must be developed using one of the technologies approved in the Approved Technologies section of the RFP.
  > "All applications must be developed using one of the approved technologies stated in the Approved Technologies section of this document." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R132** (desired) A currently supported .NET 6.0 or above release should be used unless there is a specific need for .NET Framework.
  > "A currently supported .NET 6.0 or above release should be used unless there is a specific need for .NET Framework." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R133** (mandatory) If .NET Framework is required, a currently supported 4.8 release or above must be used.
  > "If a .NET Framework is required, a currently supported 4.8 release or above will be used." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R134** (mandatory) Web applications must use either the MVC, Razor Pages or Web API framework.
  > "Web applications must use either the MVC, Razor Pages or Web API framework." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R135** (desired) Library dependencies used in the application should be reviewed and updated on an annual basis.
  > "Library dependencies used in the application should be reviewed/updated on an annual basis." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R137** (desired) New development should use the approved programming languages: C#, JavaScript, CSS, HTML, and Python.
  > "The following are the approved programming languages that should be used for new development." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R138** (mandatory) Python is reserved for ESRI scripts and other small one-time uses, and large-scale use of Python requires approval of the Information Systems (IS) Best Practices Review Team (BRPT).
  > "Python is reserved for use in ESRI scripts and other small one-time uses. Large scale use of Python requires the approval of the Information Systems (IS) Best Practices Review Team (BRPT)." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R139** (desired) For platforms other than ArcGIS Desktop, ArcGIS Pro and ArcGIS Enterprise, version 3.x of Python from www.python.org should be used.
  > "For other platforms a version 3.x of Python from www.python.org should be used." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R140** (desired) All customer applications should be web-based browser applications.
  > "All customer applications should be Web Based, browser applications." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R141** (desired) Applications should be tested and designed to use the latest IS-approved browser(s) at a minimum. _(merged from R142)_
  > "Applications should be tested and designed to use the latest IS approved browser(s), at a minimum." ((Y) Information Technology, pp. 17-18 [S73.1]; (Y) Information Technology, p. 18 [S73.2])
- **R143** (desired) No client-side software other than a modern browser (e.g., no Java Applets, no Silverlight) should be required to run the web application.
  > "No client-side software, other than a modern browser, should be required to run the web application." ((Y) Information Technology, p. 18 [S73.2])
- **R144** (mandatory) On-premise database deployments must run on Oracle 19C. _(conflicts with R145)_
  > "On premise database deployments shall be ran on:" ((Y) Information Technology, p. 18 [S73.2])
- **R145** (desired) The application should be designed and maintained to run on the latest supported version of SQL Server, with Microsoft SQL Server 2016 or higher permitted only if approved by the MoDOT IS Data Service Management team. _(conflicts with R144)_
  > "The application should be designed and maintained to run on the latest supported version of SQL server." ((Y) Information Technology, p. 18 [S73.2])

### Security and compliance (8)

- **R117** (mandatory) The business entity must provide acceptable enrollment and participation documentation consisting of a completed copy of the E-Verify Memorandum of Understanding (MOU) for the employees proposed to work in connection with the services. _(merged from R116)_
  > "The business entity must affirm its enrollment and participation in the E-Verify federal work authorization program with respect to the employees proposed to work in connection with the services requested herein by providing acceptable enrollment and participation documentation consisting of **completed** copy of the E-Verify Memorandum of Understanding (MOU)." ((K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1])
- **R118** (mandatory) The business entity must, by sworn affidavit, affirm that it does not knowingly employ any person who is an unauthorized alien in connection with the contracted services.
  > "By sworn affidavit, affirm that it does not knowingly employ any person who is an unauthorized alien in connection with the contracted services." ((K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1])
- **R119** (mandatory) If the business entity is a sole proprietorship or partnership, each sole proprietor and each general partner must provide affirmative proof of lawful presence in the United States pursuant to Section 208.009, RSMo.
  > "each sole proprietor and each general partner shall provide affirmative proof of lawful presence in the United States" ((L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1])
- **R122** (mandatory) The Offeror shall not disclose confidential factual matters provided by MHTC to third parties except as required by statute, ordinance, or court order, or as authorized by MHTC's representative.
  > "The Offeror shall not disclose to third parties confidential factual matters provided except as may be required by statute, ordinance, or order of court, or as authorized by MHTC's representative." ((R) Confidentiality, p. 16 [S66.1])
- **R123** (mandatory) The Offeror shall notify MHTC immediately of any request for such confidential information.
  > "The Offeror shall notify MHTC immediately of any request for such information." ((R) Confidentiality, p. 16 [S66.1])
- **R146** (mandatory) No Personal Identifiable Information (PII) may be stored in any database table unless the application has a specific business need for that data.
  > "No Personal Identifiable Information (PII) can be stored in any database table unless the application has a specific business need to use that data." ((Y) Information Technology, p. 18 [S73.2])
- **R147** (mandatory) All PII data that is stored must be approved by the IS Cyber Security Team.
  > "All PII data that is stored must have approval from the IS Cyber Security Team." ((Y) Information Technology, p. 18 [S73.2])
- **R149** (mandatory) All web applications must adhere to the W3 Web Content Accessibility Guidelines 2.1 at 'AA' level of conformance (WCAG 2.1 AA). _(merged from R148)_
  > "All web applications must adhere to the W3 Web Content Accessibility Guidelines 2.1 with a 'AA' level of conformance (WCAG 2.1 AA)." ((Y) Information Technology, p. 18 [S73.2])

### Legal and contractual (21)

- **R098** (mandatory) The awarded contract must incorporate the contract provisions specified in this RFP, which will also appear in the post-award negotiated contract.
  > "This RFP shall be governed by the following contract provisions." (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- **R099** (mandatory) The Offeror must accept that the award is subject to a post-award negotiated contract.
  > "The award of this RFP is subject to a post-award negotiated contract." (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- **R100** (mandatory) The Offeror must accept that if the parties cannot agree on post-award contract terms, MHTC may cancel the award and select a different Offeror.
  > "If the parties are unable to agree to terms in the post-award contract, MHTC shall reserve the right to cancel the award of the RFP and contract and select a different Offeror." (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- **R103** (mandatory) The Offeror must not release any material or reports it prepares to the public without the prior consent of MHTC's representative.
  > "No material or reports prepared by the Offeror shall be released to the public without the prior consent of MHTC's representative." ((B) Release to Public, p. 13 [S50.1])
- **R104** (mandatory) The Offeror shall not assign, delegate, or novate any interest in the services to be provided without the prior written consent of MHTC's representative.
  > "The Offeror shall not assign or delegate any interest, and shall not transfer any interest in the services to be provided (whether by assignment, delegation, or novation) without the prior written consent of MHTC's representative." ((C) Assignment, p. 13 [S51.1])
- **R106** (mandatory) The Offeror must accept that written clarifications issued by MHTC govern over conflicting requirements in the RFP or in the Offeror's proposal.
  > "MHTC reserves the right to clarify any relationship in writing and such written clarification shall govern in case of conflict with the applicable requirements stated in the RFP or the Offeror's proposal." ((E) Components of Agreement, p. 13 [S53.1])
- **R107** (mandatory) Any change to the Agreement, whether by modification or supplementation, must be accompanied by a formal contract amendment signed and approved by the duly authorized representative of the Offeror and MHTC.
  > "Any change in the Agreement, whether by modification or supplementation, must be accompanied by a formal contract amendment signed and approved by the duly authorized representative of the Offeror and MHTC." ((F) Amendments, p. 13 [S54.1])
- **R111** (mandatory) The Offeror remains ultimately responsible and liable to MHTC for the complete, accurate and professional quality and performance of the services regardless of which subcontractors or suppliers it uses.
  > "the Offeror ultimately remains responsible and liable to MHTC for the complete, accurate and professional quality/performance of these services." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **R113** (mandatory) By signing the Agreement, the Offeror certifies that any employee assigned to perform services under the contract is eligible and authorized to work in the United States in compliance with federal law. _(merged from R112)_
  > "By signing this Agreement, the Offeror hereby certifies that any employee of the Offeror assigned to perform services under the contract is eligible and authorized to work in the United States in compliance with federal law." ((I) Executive Order, p. 14 [S57.1])
- **R114** (mandatory) The Offeror must include the provisions of Section (3), paragraph I of the Agreement in every subcontract.
  > "The Offeror shall include the provisions of Section (3), paragraph I of this Agreement in every subcontract." ((J) Incorporation of Provisions, p. 14 [S58.1])
- **R115** (mandatory) The Offeror must take such action with respect to any subcontract as the Commission may direct as a means of enforcing such provisions, including sanctions for noncompliance.
  > "The Offeror shall take such action with respect to any subcontract as the Commission may direct as a means of enforcing such provisions, including sanctions for noncompliance." ((J) Incorporation of Provisions, p. 14 [S58.1])
- **R121** (mandatory) All documents, reports, exhibits and other deliverables produced by the Offeror at the direction of MHTC's representative, along with information supplied by MHTC's representative, shall remain the property of MHTC.
  > "All documents, reports, exhibits, etc. produced by the Offeror at the direction of MHTC's representative and information supplied by MHTC's representative shall remain the property of MHTC." ((Q) Ownership of Reports, p. 16 [S65.1])
- **R125** (mandatory) The Offeror's records must be made available at no charge to MHTC and/or the Missouri State Auditor at all reasonable times during the term of the Agreement and any extension, and for three (3) years from the date of final payment. _(merged from R124)_
  > "These records must be made available at all reasonable times at no charge to MHTC and/or the Missouri State Auditor during the term of the Agreement and any extension thereof, and for three (3) years from the date of final payment made under the Agreement." ((U) Maintain Papers, p. 16 [S69.1])
- **R126** (optional) MHTC's representative may reproduce and use any products derived from the Offeror's work without payment of royalties or fees.
  > "MHTC's representative shall have the right to reproduce and/or use any products derived from the Offeror's work without payment of any royalties, fees, etc." ((U) Maintain Papers, p. 16 [S69.1])
- **R127** (optional) The Offeror may be asked, prior to contract signing, to demonstrate its ability to provide certificates of insurance meeting or approaching the specified coverages.
  > "Prior to contract signing, the Offeror may be asked about its ability to provide certificates of insurance which meet, or approach, the following coverages:" ((X) Insurance, p. 17 [S72.1])
- **R128** (mandatory) General Liability insurance must be not less than $500,000 for any one person in a single accident or occurrence and not less than $3,000,000 for all claims arising out of a single occurrence.
  > "General Liability Not less than $500,000 for any one person in a single accident or occurrence, and not less than $3,000,000 for all claims arising out of a single occurrence;" ((X) Insurance, p. 17 [S72.1])
- **R129** (mandatory) Automobile Liability insurance must be not less than $500,000 for any one person in a single accident or occurrence and not less than $3,000,000 for all claims arising out of a single occurrence.
  > "Automobile Liability Not less than $500,000 for any one person in a single accident or occurrence, and not less than $3,000,000 for all claims arising out of a single occurrence;" ((X) Insurance, p. 17 [S72.1])
- **R130** (mandatory) The Offeror must maintain a Missouri State Workmen's Compensation policy or equivalent in accordance with state law.
  > "Missouri State Workmen's Compensation policy or equivalent in accordance with state law." ((X) Insurance, p. 17 [S72.1])
- **R136** (mandatory) Vendors may not use third-party tools or software that would place a licensing responsibility on MoDOT without prior review and approval by the Information Systems Best Practices Review Team (BRPT) and IS management.
  > "Vendors may not use third-party tools or software which would place a licensing responsibility on MoDOT without prior review and approval of the tools and or software by the Information Systems Best Practices Review Team (BRPT) and IS management." ((Y) Information Technology, pp. 17-18 [S73.1])
- **R150** (mandatory) The vendor must never use text, diagrams, photographs, audio, multimedia, program source code, script or graphics from another author's web pages unless the author explicitly permits free copying or appropriate arrangements are made with the author.
  > "Never use text, diagrams, photographs, audio, multimedia, program source code, script or graphics from another author's web pages unless the author explicitly states it may be freely copied or you make appropriate arrangements with the author." ((Y) Information Technology, p. 18 [S73.2])
- **R151** (mandatory) Vendor logos, branding or other company endorsements must not appear where a supported, licensed option exists to eliminate them from the display.
  > "Vendor logos, branding, or other company endorsements must not appear if there is a supported option, and licensed way to eliminate them from the display." ((Y) Information Technology, p. 18 [S73.2])

### Timeline (9)

- **R005** (mandatory) Proposals must be submitted within the RFP's stated submission deadlines, as time is of the essence.
  > "Time is of the essence for responding to the RFP within the submission deadlines." (INTRODUCTION, p. 4 [S4.1])
- **R016** (mandatory) The contract period will run for 15 months. _(conflicts with R041)_
  > "The contract period will run for 15 months." ((D) Contract Period and Budget, p. 5 [S11.1])
- **R017** (mandatory) All RFP events must occur between 7:30 a.m. and 4 p.m. Central time.
  > "The time of day for the following events shall be between 7:30 a.m. and 4 p.m., Central." ((E) RFP Schedule, pp. 5-6 [S12.1])
- **R029** (mandatory) Quarterly updates on work accomplished during the quarter must be submitted on or before the last working day of March, June, September, and December for the duration of the project.
  > "Quarterly updates on work accomplished during the quarter are due on or before the last working day of March, June, September, and December during the course of the project." ((G) Project Schedule, pp. 6-7 [S15.1])
- **R031** (mandatory) An interim presentation must be scheduled near the mid-point of the project to update MoDOT on progress and project direction. _(merged from R038)_
  > "An interim presentation shall be scheduled near the mid-point of the project to update MoDOT on the progress and the direction of the project." ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- **R041** (mandatory) The final invoice is due and the contract ends on 2/2/2026. _(conflicts with R016)_
  > "Final invoice due and contract ends." ((G) Project Schedule, p. 7 [S15.2])
- **R048** (mandatory) The Offeror must submit a Data Management Plan (DMP) to MoDOT within 2 weeks after the project kick-off meeting. _(merged from R035)_
  > "The Offeror is required to submit a Data Management Plan (DMP) to MoDOT within 2 weeks after the project kick-off meeting." (Task 1: Project Management, p. 8 [S19.1]; (G) Project Schedule, p. 7 [S15.2])
- **R053** (mandatory) MoDOT Information Systems must approve the named LLD development program before the Offeror may move forward with Task 3c.
  > "MoDOT Information Systems must give approval before moving forward with Task 3c" (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- **R074** (mandatory) Questions must be submitted by the date and time listed in section 1E.
  > "by the date and time listed in section 1E" ((4) Clarification of Requirements, p. 10 [S33.1])

### Budget and pricing (6)

- **R007** (mandatory) The Offeror must agree to provide the services at the fees quoted, under the terms of this RFP.
  > "The Offeror agrees to provide the services at the fees quoted, under the terms of this RFP." (PROPOSAL, p. 4 [S5.1])
- **R042** (mandatory) The successful Offeror shall provide the services described in the RFP for a total not to exceed $175,000.
  > "The successful Offeror shall provide the following services not to exceed $175,000." ((A) Services, p. 8 [S17.1])
- **R092** (mandatory) The Offeror must submit a proposed cost estimate covering all services defined in the Scope of Work. _(merged from R095)_
  > "The Offeror must submit a proposed cost estimate for all services defined in the Scope of Work." ((1) Cost Estimate, p. 11 [S45.1]; (A) Cost Estimate, p. 12 [S47.1])
- **R093** (mandatory) The cost estimate must be shown on Section (4), Price Page, of the proposal.
  > "This estimate must be shown on Section (4), Price Page, of this proposal" ((1) Cost Estimate, p. 11 [S45.1])
- **R096** (mandatory) The Cost Estimate must be broken out into Salaries, Benefits, Operating Expense, Facilities and Administration (F&A) Cost, Miscellaneous, and a Total.
  > "Facilities and Administration (F&A)<br>Cost" ((A) Cost Estimate, p. 12 [S47.1])
- **R097** (mandatory) Miscellaneous costs must be itemized, with an additional sheet attached if needed.
  > "Miscellaneous (list-attach additional<br>sheet if needed)" ((A) Cost Estimate, p. 12 [S47.1])

### Submission (35)

- **R001** (mandatory) Proposals for project TR202504 must be submitted to MoDOTResearchRFP@modot.mo.gov by August 21, 2024 at 10 a.m. Central. _(merged from R021, R066, R069)_
  > "Please submit all proposals to **<u>MoDOTResearchRFP@modot.mo.gov</u>** by **August 21, 2024** at **10 a.m. (Central)** ." (Front matter, pp. 1-2 [S1.1]; (E) RFP Schedule, pp. 5-6 [S12.1]; (1) Pricing and Signature, p. 10 [S30.1])
- **R006** (mandatory) The Offeror must provide a fee proposal to MHTC on the PRICE PAGE in accordance with the terms of this RFP. _(merged from R094)_
  > "The Offeror shall provide a fee proposal to MHTC on the **PRICE PAGE** in accordance with the terms of this RFP." (PROPOSAL, p. 4 [S5.1]; (1) Cost Estimate, p. 11 [S45.1])
- **R008** (mandatory) The proposal must be signed by an authorized signatory of the Offeror and dated.
  > "Authorized Signature of Offeror: ___________________________________________________" (PROPOSAL, p. 4 [S5.1])
- **R009** (mandatory) The proposal must include the Offeror's printed or typed name, mailing address, city, state, zip, telephone, fax and electronic mail address.
  > "Printed or Typed Name: __________________________________________________________ Mailing Address: _______________________________________________________________ City: __________________________ State: ______________________ Zip: _______________ Telephone: ________________________________ Fax: _______________________________ Electronic Mail Address: _________________________________________________________" (PROPOSAL, p. 4 [S5.1])
- **R019** (mandatory) The only acceptable method of contact regarding the RFP is the designated email; contacting MoDOT employees via other methods is prohibited and is cause for disqualification. _(merged from R018, R020, R073)_
  > "This is the only acceptable method for contact regarding the RFP and<br>contacting MoDOT employees via other methods is prohibited." ((E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])
- **R022** (mandatory) A proposal is not considered submitted until the submitter receives notification of receipt from MoDOT.
  > "Do<br>not consider your proposal submitted until you receive notification of receipt." ((E) RFP Schedule, pp. 5-6 [S12.1])
- **R028** (mandatory) The proposal must include a work plan with a proposed timeline. _(merged from R002, R003, R004)_
  > "Proposals need to include a work plan with a proposed timeline." ((G) Project Schedule, pp. 6-7 [S15.1]; Front matter, pp. 1-2 [S1.1])
- **R030** (mandatory) Quarterly updates must be submitted electronically to the MoDOT project manager.
  > "These quarterly updates shall be submitted electronically to the MoDOT project manager." ((G) Project Schedule, pp. 6-7 [S15.1])
- **R043** (mandatory) The Offeror must provide Construction and Materials with an electronic copy of a program proposal that will help bring the project to successful completion.
  > "The Offeror will provide Construction and Materials an electronic copy of a program proposal which will help bring the project to its successful completion." ((B) Specific Requirements, p. 8 [S18.1])
- **R052** (mandatory) Before work begins on the proof of concepts, the Offeror must provide the name of the program used to develop the LLDs.
  > "Before work begins on the proof of concepts, the Offeror will provide the name of the program used to develop the LLDs." (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- **R059** (mandatory) The final report must include a completed Technical Report Documentation page.
  > "A final report must include a completed Technical Report Documentation page." (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **R064** (mandatory) The final report and research summary must follow the Publications Guidelines. _(merged from R060)_
  > "Please refer to the **Publications Guidelines** for the report and research summary, which can be found on the website." (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1]; Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **R067** (optional) Any form containing a signature line, amendments, pricing pages and similar documents may be electronically signed or manually signed, scanned and returned as part of the proposal.
  > "Any form containing a signature line in this RFP and any amendments, pricing pages, etc., can be electronically signed or manually signed and scanned and returned as part of the proposal." ((1) Pricing and Signature, p. 10 [S30.1])
- **R068** (mandatory) The proposal must reference the project number and title because more than one RFP may be due at one time.
  > "Please reference the project number and title since more than one RFP may be due at one time." ((1) Pricing and Signature, p. 10 [S30.1])
- **R070** (mandatory) The Offeror must submit all data required in paragraph (B) of the RFP for its proposal to be evaluated and considered for award.
  > "The Offeror must respond to this RFP by submitting all data required in paragraph (B) below for its proposal to be evaluated and considered for award." ((2) Submission of All Data Required, p. 10 [S31.1])
- **R071** (mandatory) Failure to submit the required data is sufficient cause for disqualification of the proposal from further consideration.
  > "Failure to submit such data shall be deemed sufficient cause for disqualification of a proposal from further consideration." ((2) Submission of All Data Required, p. 10 [S31.1])
- **R072** (mandatory) The Offeror must submit its proposal on the basis that all proposals and their contents will be open to public inspection, without reservations.
  > "Therefore, the Offeror must submit its proposal based on such conditions without reservations." ((3) Public Inspection, p. 10 [S32.1])
- **R075** (mandatory) The proposal must include the Proposal Submission Form.
  > "The proposal submission form can be found here:" ((1) Proposal Submission Form, p. 10 [S35.1])
- **R076** (mandatory) The proposal must include a narrative-style description of how the Offeror will work with MoDOT to fulfill project-specific requirements.
  > "A narrative style description must be included of how the Offeror will work with MoDOT in order to fulfill project-specific requirements." ((2) Work Plan, p. 10 [S36.1])
- **R077** (mandatory) The Work Plan section must be no longer than ten (10) pages, excluding forms and resumes attached to the proposal. _(merged from R078)_
  > "This section should be no longer than ten (10) pages in length, with a font size no less than 12 points." ((2) Work Plan, p. 10 [S36.1])
- **R079** (mandatory) The project plan must include all items outlined in Section 2.
  > "The project plan shall include all items outlined in Section 2" ((2) Work Plan, p. 10 [S36.1])
- **R081** (mandatory) The proposal must indicate the name, location, telephone number, and email address of the Offeror's primary contact person.
  > "Please indicate the name, location, telephone number, and email address of the primary contact person for the Offeror." ((3) Personnel, pp. 10-11 [S37.1])
- **R082** (desired) The Personnel section of the proposal must highlight the Offeror's previous experience, including any relevant work with other state agencies or local governments in Missouri.
  > "Information presented in this section should highlight the previous Offeror experience, as well as any relevant work with other state agencies or local governments in Missouri." ((3) Personnel, pp. 10-11 [S37.1])
- **R083** (mandatory) The Offeror must furnish a complete listing of each Sub-Offeror, if any, together with complete contact information for that Sub-Offeror.
  > "The Offeror must furnish a complete listing of each Sub-Offeror, if any, and complete contact information for that Sub-Offeror." ((3) Personnel, pp. 10-11 [S37.1])
- **R084** (mandatory) The proposal must clearly identify the bidder's experience in offering the services requested in this RFP during the past three (3) years.
  > "The proposal must clearly identify the experience in offering the services requested in this RFP during the past three (3) years." ((4) Experience, p. 11 [S38.1])
- **R085** (desired) The experience description should include a list of the agencies the bidder's institution has served or currently serves.
  > "The description should include a list of the agencies which your institution has served or currently serves." ((4) Experience, p. 11 [S38.1])
- **R086** (desired) Proposals should indicate the name, title, and telephone number of at least three officials of clients within the past three years.
  > "Proposals should indicate the name, title, and telephone number of at least three officials of clients within the past three years." ((5) References, p. 11 [S39.1])
- **R087** (mandatory) Proposals must be submitted as one combined PDF document.
  > "Proposals must be submitted as one combined PDF document." ((5) References, p. 11 [S39.1])
- **R088** (desired) The proposal submission should only include the required documents.
  > "The submission should **only include the required documents**" ((5) References, p. 11 [S39.1])
- **R089** (mandatory) The proposal must be organized in the following order: 1) Proposal Submission Form; 2) Cover Letter (Optional; 1 page maximum); 3) Body of Proposal (including work plan and project schedule); 4) Personnel; 5) Organization's Project Experience; 6) Team Member Experience; and 7) Organization's Client References.
  > "organized in the following order: 1) Proposal Submission Form; 2) Cover Letter (Optional; 1 page maximum); 3) Body of Proposal (including work plan and project schedule); 4) Personnel; 5) Organization's Project Experience; 6) Team Member Experience; and 7) Organization's Client References." ((5) References, p. 11 [S39.1])
- **R090** (mandatory) The optional cover letter must not exceed one page.
  > "Cover Letter (Optional; 1 page maximum)" ((5) References, p. 11 [S39.1])
- **R091** (mandatory) The Offeror bears sole responsibility for submitting all information related to the evaluation categories with its proposal, and MHTC's representative is not obligated to solicit any information that is missing from the proposal.
  > "it is the Offeror's sole responsibility to submit information related to the evaluation categories" ((3) Responsibility to Submit Information, p. 11 [S43.1])
- **R105** (mandatory) The Offeror's proposal must be submitted so that it is acceptable to MHTC without further clarification, since MHTC may accept it as-is.
  > "The Offeror is cautioned that its proposal shall be subject to acceptance by MHTC without further clarification." ((E) Components of Agreement, p. 13 [S53.1])
- **R108** (desired) Offerors are encouraged to submit copies of their existing affirmative action programs, if any.
  > "Offerors are encouraged to submit copies of their existing affirmative action programs, if any." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **R120** (mandatory) Each sole proprietor and general partner of a sole proprietorship or partnership must submit a sworn affidavit of lawful presence using the form attached as Exhibit B. _(merged from R152)_
  > "A copy of the affidavit reference herein is provided within this document, attached as Exhibit B." ((L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1]; EXHIBIT B: APPLICANT AFFIDAVIT FOR SOLE-PROPRIETORSHIP OR PARTNERSHIP, p. 20 [S75.1])

### Other (3)

- **R080** (mandatory) The project plan must recognize MoDOT's ultimate authority to approve the work plans.
  > "recognize the ultimate authority of MoDOT to approve the work plans" ((2) Work Plan, p. 10 [S36.1])
- **R109** (desired) Offerors are encouraged to directly hire minorities and women as direct employees of the Offerors.
  > "Offerors are also encouraged to directly hire minorities and women as direct employees of the Offerors." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **R110** (desired) Offerors are encouraged to obtain MBE and WBE participation in this work through subcontractors, suppliers, joint ventures, or other arrangements, with a target of 10% MBE and 5% WBE participation.
  > "Offerors are encouraged to obtain 10% MBE and 5% WBE participation." ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])

### Ambiguities

- **A01** The submission deadlines are not stated in this chunk; a bidder would ask for the exact due date and time (and time zone) for proposals. _(affects R005)_ (INTRODUCTION, p. 4 [S4.1])
- **A02** The PRICE PAGE is referenced as the required location for the fee proposal but is not included in this text; the bidder would ask where the PRICE PAGE form is obtained and whether pricing must follow a prescribed format or cost breakdown. _(affects R006)_ (PROPOSAL, p. 4 [S5.1])
- **A03** The "MHTC parameters" that the AI/ML draft must use are not defined in this text; a bidder would ask what these parameters are and where they are documented. _(affects R015)_ ((B) Background, p. 5 [S9.1])
- **A04** The text requires descriptions to meet EPG Section 236.4.6.2 but does not state its content; a bidder would ask whether that section is provided or must be obtained independently. _(affects R011)_ ((B) Background, p. 5 [S9.1])
- **A05** The table lists the 7/17/2024 4 p.m. (Central) row as the deadline for comments/questions and contact, but the question-submission row carries no date of its own; bidders would ask whether questions must arrive by 7/17/2024 4 p.m. Central. _(affects R019)_ ((E) RFP Schedule, pp. 5-6 [S12.1])
- **A06** The proposal deadline is 8/21/2024 10 a.m. Central, yet MoDOT reserves the right to expand the schedule without notification except for the proposal deadline date; it is unclear whether the deadline time or only the date is fixed. _(affects R001)_ ((E) RFP Schedule, pp. 5-6 [S12.1])
- **A07** The deliverables table lists items without dates, sequencing or acceptance criteria, so the bidder cannot tell when each deliverable is due or how many training sessions and demonstrations are expected; the bidder would ask for the deliverable schedule and the scope of the training and demonstration. _(affects R024, R055, R026, R027)_ (Task Deliverables, p. 6 [S14.1])
- **A08** The schedule is only an estimate presuming a November 1, 2024 start, and the timeline will be finalized during contracting; bidders would ask whether the November 1, 2024 start date is fixed and what the expected project duration/end date is. _(affects R028, R029, R031)_ ((G) Project Schedule, pp. 6-7 [S15.1])
- **A09** "Near the mid-point of the project" is undefined, so the bidder cannot fix the interim presentation date or its cost; the bidder would ask whether a specific month or milestone defines the mid-point. _(affects R031)_ ((G) Project Schedule, pp. 6-7 [S15.1])
- **A10** The milestone table fixes the draft deliverables at 11/3/2025 while also saying draft documents shall be submitted approximately two months prior to the final report; it is unclear whether 11/3/2025 is the binding date or a date derived from the final report date. _(affects R026, R027)_ ((G) Project Schedule, p. 7 [S15.2])
- **A11** The kick-off meeting row states that the dates of key milestones and deliverables will be determined from that meeting, which conflicts with the fixed dates in the same table; the bidder would ask whether the listed dates are binding or subject to change after kick-off. _(affects R044, R048, R024, R055, R031, R026, R027, R041)_ ((G) Project Schedule, p. 7 [S15.2])
- **A12** The services are defined only by reference to "the services listed below in (B)", which is not included in this chunk; the bidder would ask which task descriptions in (B) are binding versus merely guidance, since the text says task descriptions are only intended to provide guidance. _(affects R042)_ ((A) Services, p. 8 [S17.1])
- **A13** The chunk does not say what the "program proposal" must contain, what format the electronic copy must take, or when it is due; a bidder would ask for the required content, file format and submission deadline. _(affects R043)_ ((B) Specific Requirements, p. 8 [S18.1])
- **A14** The text refers to "the following tasks" in the finalized work plan but the task list is not contained in this chunk, so a bidder cannot tell which tasks the work plan must cover; the bidder would ask for the complete task list or confirm it is the Task 1..n set in the Scope of Work. _(affects R047)_ (Task 1: Project Management, p. 8 [S19.1])
- **A15** The 2-week DMP deadline runs from "the project kick-off meeting", but the text does not say how soon after contract award the kick-off must occur, so the effective DMP due date is open; the bidder would ask for the required kick-off timing. _(affects R048)_ (Task 1: Project Management, p. 8 [S19.1])
- **A16** The scope of the literature review is undefined: which states, time period, publication types and ROW use cases must be covered, and what depth or deliverable format constitutes a "thorough" review. The bidder would ask what coverage and deliverable (report, memo, presentation) is expected. _(affects R051)_ (Task 2: Literature Review, p. 8 [S20.1])
- **A17** The text does not say what information about the program must accompany its name (version, license, hosting, security documentation) or what criteria MoDOT Information Systems will use to approve it, so the bidder cannot know what to submit or how long approval may take. _(affects R052, R053)_ (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])
- **A18** The number and types of properties, and the format of the demonstration (live, recorded, sample outputs), are not specified, which affects effort and cost; the bidder would ask how many properties and what property types must be covered. _(affects R024)_ (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1])
- **A19** The scope of the training is undefined: the number of ROW staff to be trained, the delivery mode (on-site, virtual, recorded), the duration and the number of sessions are not stated, all of which affect staffing and price. The bidder would ask what training volume and format is expected. _(affects R055)_ (Task 4: Training and User Manual, p. 9 [S24.1])
- **A20** The user manual's required content, format (print or electronic) and whether it must be updated or delivered in multiple copies are unspecified. The bidder would ask what the manual must contain and in what form it must be delivered. _(affects R056)_ (Task 4: Training and User Manual, p. 9 [S24.1])
- **A21** The scope of "all accompanying documentation identified as beneficial during the study" is open-ended and undefined, so the bidder cannot size the deliverable; the bidder would ask what documentation is expected and who determines what is beneficial. _(affects R057)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **A22** The Publication Guidelines and summary template are referenced only as being "on the website" without a specific location or version, so the bidder would ask where to obtain them and which version governs. _(affects R064)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **A23** The chunk does not state when the final report, research summary and presentation are due, nor whether the presentation is delivered in person or virtually; a bidder would ask for the deliverable schedule and presentation format. _(affects R057, R062, R063)_ (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **A24** The text does not specify how often, in what form (meeting, written report) or within what timeframe the Offeror must consult MHTC's representative, so the bidder cannot size the effort or price it. _(affects R065)_ ((C) Administration of Program, p. 9 [S27.1])
- **A25** The submission deadline is stated only as "the due date indicated" without a calendar date in this text; a bidder would ask what the exact due date is. _(affects R001)_ ((1) Pricing and Signature, p. 10 [S30.1])
- **A26** The text says the section "should be no longer than ten (10) pages" while also stating the plan "shall include all items outlined in Section 2"; it is unclear whether the 10-page limit is a hard pass/fail constraint or a guideline, and whether the Section 2 items must fit within it. _(affects R077, R079)_ ((2) Work Plan, p. 10 [S36.1])
- **A27** The text requires "complete contact information" for each Sub-Offeror but does not say which fields that covers (unlike the primary contact, where name, location, telephone and email are listed). A bidder would ask whether the same four fields suffice or additional details are required. _(affects R083)_ ((3) Personnel, pp. 10-11 [S37.1])
- **A28** The references requirement asks for at least three client officials from the past three years but does not say whether these must be public-agency clients, whether they must be for similar legal-description or AI/ML work, or whether contact details must be verifiable/current; a bidder would ask what qualifies a reference. _(affects R086)_ ((5) References, p. 11 [S39.1])
- **A29** The evaluation criteria are not stated here, only that they are "established by the Technical Advisory Committee"; a bidder would ask what the specific weighted criteria and scoring method are, since they determine how the proposal should be structured and prioritized. ((1) Evaluation Factors, p. 11 [S41.1])
- **A30** The text refers to "the evaluation categories" without listing them here, so a bidder cannot tell exactly what information must be submitted; the bidder would ask which evaluation categories and required content are meant. _(affects R091)_ ((3) Responsibility to Submit Information, p. 11 [S43.1])
- **A31** The text says a detailed budget will be developed later, so it is unclear how detailed the cost estimate submitted with the proposal must be and what level of breakdown (labor categories, hours, rates) is expected at this stage. _(affects R092, R093)_ ((1) Cost Estimate, p. 11 [S45.1])
- **A32** The cost estimate gives no period of performance or basis (e.g., annual vs. total contract value) for the estimated amounts, so a bidder cannot tell what timeframe the salaries, benefits and F&A figures should cover. _(affects R092, R096)_ ((A) Cost Estimate, p. 12 [S47.1])
- **A33** The chunk refers to "the following contract provisions" but does not state them here, so the bidder cannot tell which terms it must accept or price against; the bidder would ask where those provisions are set out and whether they are negotiable. _(affects R098, R099, R100)_ (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- **A34** The text does not define what "fully coordinate" with the Construction and Materials Division requires (meeting cadence, review gates, approval steps), which affects staffing and schedule; the bidder would ask what coordination activities and turnaround times are expected. _(affects R101)_ ((A) MHTC's Representative, p. 13 [S49.1])
- **A35** The text says the proposal must be acceptable without further clarification, yet MHTC reserves the right to clarify relationships in writing; a bidder would ask whether post-submission clarifications can change scope, price or terms, and whether the proposal must be fully self-contained. _(affects R105, R106)_ ((E) Components of Agreement, p. 13 [S53.1])
- **A36** The 10% MBE / 5% WBE participation is stated as encouraged rather than required, and it is unclear whether the percentages are measured against total contract value, subcontract value, or another base, and whether any reporting or documentation of M/WBE participation is expected in the proposal. _(affects R110)_ ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- **A37** The text does not state what Section (3), paragraph I contains, so the bidder cannot tell which obligations must be flowed down to subcontractors; the bidder would ask for the text of that provision. _(affects R114)_ ((J) Incorporation of Provisions, p. 14 [S58.1])
- **A38** The text does not define what counts as "confidential factual matters" or how such material will be marked or identified, so the bidder cannot tell what handling, storage or personnel restrictions it must price; the bidder would ask MHTC for a definition and marking convention. _(affects R122, R123)_ ((R) Confidentiality, p. 16 [S66.1])
- **A39** "Immediately" sets no measurable notification window, and it is unclear whether the notice must go to MHTC's representative or another contact; the bidder would ask for a defined timeframe and named recipient. _(affects R123)_ ((R) Confidentiality, p. 16 [S66.1])
- **A40** The clause grants MHTC rights to reproduce and use "any products derived from the Offeror's work" without royalties, but does not state who owns the deliverables or whether pre-existing Offeror IP/tools are included; a bidder would ask what ownership and license rights it retains in its models, code and data. _(affects R126)_ ((U) Maintain Papers, p. 16 [S69.1])
- **A41** The insurance coverages are only something the Offeror "may be asked" about, and the standard is "meet, or approach" the listed amounts, so it is unclear whether these limits are binding contract requirements and how much deviation is acceptable. The bidder would ask whether the stated limits are mandatory at contract signing and what tolerance "approach" allows. _(affects R127, R128, R129, R130)_ ((X) Insurance, p. 17 [S72.1])
- **A42** The chunk requires development on "one of the approved technologies stated in the Approved Technologies section of this document" but that section is not included here, so a bidder cannot tell whether the listed runtimes and languages are the complete approved set or whether additional technologies are permitted. _(affects R131, R137)_ ((Y) Information Technology, pp. 17-18 [S73.1])
- **A43** The threshold for "large scale use of Python" that triggers BRPT approval is undefined, so a bidder cannot judge whether its planned Python components need prior approval and how that affects schedule. _(affects R138)_ ((Y) Information Technology, pp. 17-18 [S73.1])
- **A44** The text requires on-premise databases to run on Oracle 19C but also describes SQL Server as an option; it is unclear whether these are alternatives the bidder may choose between or whether Oracle 19C is the default with SQL Server requiring approval. The bidder would ask which database platform is required and what approval process applies. _(affects R144, R145)_ ((Y) Information Technology, p. 18 [S73.2])
- **A45** The text does not define what constitutes a 'specific business need' for storing PII or what the IS Cyber Security Team approval process and timeline are, which affects design and schedule. The bidder would ask for the approval criteria and expected turnaround. _(affects R146, R147)_ ((Y) Information Technology, p. 18 [S73.2])
- **A46** Conflicting requirements R144 and R145: R144 mandates on-premise databases run on Oracle 19C while R145 directs design for the latest supported SQL Server, incompatible database platforms for the same deployment. _(affects R144, R145)_ ((Y) Information Technology, p. 18 [S73.2])
- **A47** Conflicting requirements R016 and R041: R016 sets a 15-month contract period while the schedule in R041 ends the contract on 2/2/2026, roughly 14.5 months after the 11/15/2024 kick-off. _(affects R016, R041)_ ((D) Contract Period and Budget, p. 5 [S11.1]; (G) Project Schedule, p. 7 [S15.2])

### Gaps

- **G01** An attachment is referenced but not included in this chunk; the bidder needs it to know what forms or requirements accompany the proposal. _(referenced document: Attachment)_ (Front matter, pp. 1-2 [S1.1])
- **G02** The letter points to a web page for more information about project contracting in general, which may hold additional requirements or forms. _(referenced document: https://www.modot.org/information-researchers)_ (Front matter, pp. 1-2 [S1.1]; (1) Cost Estimate, p. 11 [S45.1])
- **G03** The PRICE PAGE form on which the fee proposal must be submitted is referenced but not provided in this chunk. _(referenced document: PRICE PAGE)_ (PROPOSAL, p. 4 [S5.1])
- **G04** The MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2, which defines the requirements property descriptions must meet, is referenced but not included in this text. _(referenced document: MoDOT Engineering Policy Guide (EPG) Section 236.4.6.2)_ ((B) Background, p. 5 [S9.1])
- **G05** The Standard Research Agreement, which the bidder must review for contractual terms, is provided separately on the issuer's website. _(referenced document: Standard Research Agreement)_ ((D) Contract Period and Budget, p. 5 [S11.1])
- **G06** The Publication Guidelines document referenced for report formatting is provided separately on the website. _(referenced document: Publication Guidelines)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **G07** The summary template referenced for the Research Summary is provided separately on the website. _(referenced document: summary template)_ (Task 5: Develop Draft Report and Research Summary, p. 9 [S25.1])
- **G08** The Publications Guidelines governing the format of the report and research summary are referenced as being on the website but not included in this chunk. _(referenced document: Publications Guidelines)_ (Task 6: Develop Final Report, Research Summary, and Presentation, p. 9 [S26.1])
- **G09** The Proposal Submission Form itself is not included in the RFP; the bidder must obtain it from the MoDOT information-for-researchers web page. _(referenced document: Proposal Submission Form)_ ((1) Proposal Submission Form, p. 10 [S35.1])
- **G10** Executive Order 07-13 is incorporated by reference but its full text is not reproduced in this chunk; the bidder needs the order's provisions to confirm compliance obligations. _(referenced document: Executive Order 07-13)_ ((I) Executive Order, p. 14 [S57.1])
- **G11** The sworn affidavit the bidder must submit is provided as an attachment to the RFP but is not included in this chunk. _(referenced document: Exhibit A)_ ((K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1])
- **G12** The sworn affidavit of lawful presence form that sole proprietors and general partners must submit is provided as a separate exhibit. _(referenced document: Exhibit B)_ ((L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1]; EXHIBIT B: APPLICANT AFFIDAVIT FOR SOLE-PROPRIETORSHIP OR PARTNERSHIP, p. 20 [S75.1])
- **G13** The State of Missouri Accessibility Standard that web applications must meet is referenced as an external document/web page rather than reproduced in the RFP. _(referenced document: Accessibility Standard)_ ((Y) Information Technology, p. 18 [S73.2])

## Proposed solution

The bid is a 15-month research and development engagement, not a software procurement: we deliver a proof-of-concept AI/ML tool that drafts legal land descriptions from MHTC parameters, together with the evidence, training and reporting that let MoDOT decide whether the technology is useful. The work runs in six phases — kick-off and planning, literature and peer-state review, program selection and MoDOT IS approval, proof-of-concept build and demonstration, training and manual, then synthesis and final reporting — each gated by a MoDOT review point. We build the prototype on the approved MoDOT technology stack (.NET 6.0 or above, MVC/Razor Pages/Web API, C#/JavaScript/HTML/CSS, Python only for ESRI scripts or small one-time uses) and host it in a MoDOT-approved environment, with no third-party licensing burden placed on MoDOT. The team is a small, senior one: a principal investigator and land-surveying subject-matter expert, an AI/ML engineer, a .NET developer, a technical writer/trainer and a part-time contract and compliance lead, with a professional land surveyor reviewing every generated description. Everything is priced to the $175,000 not-to-exceed ceiling on the Section (4) Price Page, and all deliverables, data and working papers remain MHTC property. A bid-administration workstream owns the RFP's own calendar — the question deadline, the proposal deadline and the 7:30 a.m. to 4 p.m. Central window for every RFP event — so the offer is submitted on time and through the single permitted channel.

### Coverage

Covers 72 of 72 mandatory requirements.

### Components

#### C01. Bid administration and RFP calendar compliance

A named bid manager owns the RFP's own timetable and contact rules so the offer is never late and never disqualified. Questions and comments go only to MoDOTResearchRFP@modot.mo.gov by the date and time in Section 1E (17 July 2024, 4 p.m. Central), with no contact with MoDOT employees by any other method; the proposal is emailed to the same address by 21 August 2024, 10 a.m. Central, and we treat submission as complete only when MoDOT's notification of receipt arrives. Every RFP event we schedule or attend — question submission, proposal delivery, any interview or clarification session — is booked inside the 7:30 a.m. to 4 p.m. Central window, and the calendar is tracked against a written submission checklist with a time buffer before each deadline. The same workstream assembles the single combined PDF in the required order and confirms the Proposal Submission Form, signatures and contact details are present.

Addresses: R005, R017, R074.

- Proposals are due by email to MoDOTResearchRFP@modot.mo.gov by 21 August 2024 at 10 a.m. Central, and questions are due by 17 July 2024 at 4 p.m. Central. (Front matter, pp. 1-2 [S1.1]; (E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])
- All RFP events must occur between 7:30 a.m. and 4 p.m. Central time. ((E) RFP Schedule, pp. 5-6 [S12.1])

#### C02. Project management, governance and MoDOT coordination

A named project manager runs the engagement under a finalized work plan that details every task, resource and schedule commitment and explicitly recognizes MoDOT's ultimate authority to approve work plans. We facilitate the kick-off meeting to confirm scope, schedule and a communications protocol, then hold quarterly status meetings (in person or online) with written minutes for the kick-off and every quarterly meeting, submit quarterly progress updates by the last working day of March, June, September and December, and maintain monthly email and phone updates to MoDOT contacts. All activity is coordinated with the Research Unit of the Construction and Materials Division, and advice and information on Agreement matters is available to that Division throughout the term. A single MHTC representative channel handles concerns about administration of the services.

Addresses: R044, R045, R046, R047, R080, R029, R032, R101, R102, R065, R016, R041, R031.

- The contract period is 15 months, with an estimated 1 November 2024 start and a final invoice and contract end date of 2 February 2026. ((D) Contract Period and Budget, p. 5 [S11.1]; (G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- The work is coordinated by the Research Unit of MoDOT's Construction and Materials Division, with which the Offeror must fully coordinate. (Front matter, pp. 1-2 [S1.1]; (A) MHTC's Representative, p. 13 [S49.1])

#### C03. Data Management Plan and research data handling

Within two weeks of kick-off we submit a Data Management Plan that names the anticipated formats for every data type the study produces — source deeds and right-of-way plans, MHTC parameter sets, training corpora, model artefacts, generated descriptions and review comments — and commits to platform-independent, non-proprietary formats (plain text, CSV, PDF/A, GeoJSON where spatial) so the data retains maximum future utility for MoDOT. The plan also states retention, access and handover arrangements consistent with MHTC ownership of all data and deliverables and with records being available to MHTC and the Missouri State Auditor for three years after final payment. No PII is stored in any database table without a documented business need and IS Cyber Security Team approval.

Addresses: R048, R049, R050, R121, R125, R146, R147.

- The Data Management Plan is due within two weeks after the kick-off meeting. (Task 1: Project Management, p. 8 [S19.1]; (G) Project Schedule, p. 7 [S15.2])

#### C04. Literature search and peer-state practice review

A structured review of published research and of other state DOTs' use of AI/ML for right-of-way work, covering document-drafting and deed-description automation, spatial data extraction, and the accuracy, liability and professional-surveyor review questions those uses raise. We deliver an annotated bibliography, a comparison matrix of peer-state practice and a findings memo that feeds directly into the program selection and the proof-of-concept design, so the demonstration is grounded in what has already been shown to work rather than starting from zero.

Addresses: R051.

- Task 2 requires a thorough literature search and review of other state DOT practices using AI/ML for right-of-way purposes. (Task 2: Literature Review, p. 8 [S20.1])

#### C05. Program selection and MoDOT Information Systems approval

We name the specific program used to develop the LLDs before any proof-of-concept work begins, and submit it to MoDOT Information Systems with the information that review needs: version, licensing model, hosting location, data flows, security posture and any third-party dependencies. We do not proceed to the proof-of-concept demonstration until MoDOT IS has approved the named program, and we hold a schedule contingency for that approval. The selection is constrained to the approved technology stack — .NET 6.0 or above (or a supported .NET Framework 4.8+ where specifically needed), MVC/Razor Pages/Web API, C#/JavaScript/HTML/CSS, with Python limited to ESRI scripts and small one-time uses unless the IS Best Practices Review Team approves more — and to components that place no licensing responsibility on MoDOT without BRPT and IS management approval.

Addresses: R053, R131, R132, R133, R134, R136, R137, R138, R139.

- Task 3b requires the Offeror to name the program used to develop the LLDs before proof-of-concept work begins, and MoDOT Information Systems must approve it before Task 3c proceeds. (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1])

#### C06. Legal land description rules engine and drafting prototype

The core build: a rules-and-template layer that encodes MoDOT EPG Section 236.4.6.2 requirements and the MHTC drafting conventions, so that generated descriptions use metes and bounds for partial acquisitions, reproduce the last deed of record verbatim where a property is acquired in its entirety, and recite the specific rights acquired, conveyed or leased whenever the interest is less than fee simple. The AI/ML component drafts from MHTC parameters supplied per property and produces a clearly marked first draft for Right of Way staff to review and edit, with every generated call and bearing traceable to its source input. The application is a browser-based web application requiring no client-side software beyond a modern browser, tested against the latest IS-approved browsers, meeting WCAG 2.1 AA and the State of Missouri Accessibility Standard, running on Oracle 19C or an approved SQL Server version, and free of vendor branding where a licensed option removes it and of unlicensed third-party content.

Addresses: R011, R012, R013, R014, R015, R140, R141, R143, R144, R145, R149, R150, R151, R135.

- Realty rights acquired or conveyed by MHTC must be described by metes and bounds unless the property is acquired in its entirety, in which case the description must be written exactly as it appears on the last deed of record. ((B) Background, p. 5 [S9.1])
- Descriptions prepared for MHTC must meet MoDOT Engineering Policy Guide Section 236.4.6.2. ((B) Background, p. 5 [S9.1])

#### C07. Proof-of-concept demonstration and surveyor verification

A live demonstration on 25 April 2025 in which the technology generates draft legal land descriptions across a spread of property types — partial takes, whole-parcel acquisitions, easements and less-than-fee interests — with MoDOT Right of Way staff reviewing the drafts and giving structured improvement feedback that we log, triage and fold into the next iteration. Each generated description is checked by a professional land surveyor against the right-of-way plans and the surveyor's survey information before it is presented as a candidate for deed use, mirroring the review MoDOT requires before a deed reaches a grantor. We report measured accuracy and staff editing effort per property so MoDOT can judge usefulness, not just feasibility.

Addresses: R024, R010, R015.

- The Offeror must present how the AI/ML will create draft LLDs on 25 April 2025 for MoDOT feedback. ((G) Project Schedule, p. 7 [S15.2])
- Before a deed is presented to a grantor, a professional land surveyor must verify the description matches the right-of-way plans and the survey information. ((B) Background, p. 5 [S9.1])

#### C08. Training, user manual and knowledge transfer

Once the system is finalized we train Right of Way staff and deliver a user manual for ongoing reference, both by 25 July 2025. Training is role-based — drafters, reviewers and approvers — covering parameter entry, reading and correcting a generated description, the surveyor verification step and the audit trail, delivered in sessions plus recorded walkthroughs so staff can revisit them. The manual is delivered electronically and in print-ready form, covering installation and access, every workflow, the EPG 236.4.6.2 rules the tool applies, troubleshooting and worked examples, and is updated to match the final system at project close.

Addresses: R055, R056, R026, R027.

- The manual and ROW training must be delivered by 25 July 2025. ((G) Project Schedule, p. 7 [S15.2])

#### C09. Synthesis, final reporting and research summary

A draft Synthesis Report and Research Summary with supporting documentation, delivered by 3 November 2025, followed by the final report containing all findings, a 1–2 page research summary stating objectives, findings and conclusions, and a presentation for MoDOT staff. The final report carries a completed Technical Report Documentation page and follows the Publications Guidelines and summary template. The synthesis answers the research question directly: whether AI/ML can usefully produce a first draft LLD from MHTC parameters, under what conditions, with what review burden and what residual risk — and recommends next steps for MoDOT adoption.

Addresses: R057, R062, R063, R026, R027.

- The draft final report, summary and user manual are due by 3 November 2025. ((G) Project Schedule, p. 7 [S15.2])

#### C10. Contract, compliance and commercial obligations

A compliance workstream that carries every non-technical obligation: acceptance of the post-award negotiated contract and its provisions, including MHTC's right to cancel if terms cannot be agreed; no public release of materials without MHTC consent; no assignment or delegation without written consent; acceptance that MHTC written clarifications govern; formal signed amendments for any change; full responsibility for subcontractor performance; flow-down of Section (3) paragraph I to every subcontract with Commission-directed enforcement; MHTC ownership of all deliverables and information; confidentiality of MHTC factual matters with immediate notice of any disclosure request; records available to MHTC and the State Auditor for three years after final payment; and MHTC's royalty-free right to reproduce derived products. It also carries the employment and insurance package: E-Verify MOU, the sworn affidavit of no unauthorized-alien employment, lawful-presence affidavits for sole proprietors and general partners, general and automobile liability at $500,000 per person and $3,000,000 per occurrence, Missouri workers' compensation, and certificates of insurance available on request. We commit to 10% MBE and 5% WBE participation and to direct hiring of minorities and women.

Addresses: R098, R099, R100, R103, R104, R106, R107, R111, R113, R114, R115, R117, R118, R119, R121, R122, R123, R125, R126, R127, R128, R129, R130, R109, R110.

- Award is subject to a post-award negotiated contract that MHTC may cancel if terms cannot be agreed. (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1])
- The RFP requires 10% MBE and 5% WBE participation targets, an E-Verify affidavit, lawful-presence affidavits, and insurance of $500,000 per person and $3,000,000 per occurrence plus Missouri workers' compensation. ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1]; (K) Non-employment of Unauthorized Aliens, pp. 14-15 [S59.1]; (L) Proof of Lawful Presence for Sole Proprietorships and Partnerships, p. 15 [S60.1]; (X) Insurance, p. 17 [S72.1])

#### C11. Price page and cost estimate

A complete cost estimate for all services in the Scope of Work, entered on Section (4), the Price Page, broken out into Salaries, Benefits, Operating Expense, Facilities and Administration (F&A) Cost, Miscellaneous and Total, with miscellaneous costs itemized on an attached sheet. The estimate is built bottom-up from named staff, hours and rates across the full 15-month period and totals no more than the $175,000 not-to-exceed ceiling, with the Offeror agreeing to perform at the quoted fees under the RFP's terms. A cost narrative maps each line to a task so MoDOT can see what each phase buys.

Addresses: R092, R093, R096, R097, R042, R007.

- Services are capped at a not-to-exceed amount of $175,000, with the cost estimate entered on the Section (4) Price Page. ((A) Services, p. 8 [S17.1])

### Assumptions

- The MHTC parameters are assumed to be the right-of-way plan data, parcel and ownership records, deed references and acquisition instructions that MoDOT Right of Way staff currently use to hand-write descriptions; we will confirm the exact parameter set at kick-off and treat it as a fixed input specification for the prototype. *(inference)* ((B) Background, p. 5 [S9.1])
- MoDOT EPG Section 236.4.6.2 is assumed to be obtainable from MoDOT's public Engineering Policy Guide and to be stable for the project term; we will encode it as a versioned ruleset and re-verify it at each review gate rather than assume it is supplied with the RFP. *(inference)* ((B) Background, p. 5 [S9.1])
- The 1 November 2024 start is assumed to be the planning baseline, with the 2 February 2026 contract end and the fixed milestone dates (25 April 2025 demonstration, 25 July 2025 training and manual, 15 September 2025 interim presentation, 3 November 2025 draft deliverables) treated as binding and not re-opened at kick-off. *(inference)* ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2]; (D) Contract Period and Budget, p. 5 [S11.1])
- The interim presentation is assumed to fall at the September 2025 milestone already named in the schedule, which we treat as the project mid-point. *(inference)* ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])
- The proof-of-concept is assumed to cover a representative sample of roughly ten to fifteen properties spanning partial takes, whole-parcel acquisitions, easements and less-than-fee interests, sized to fit within the $175,000 ceiling; the exact count will be agreed with MoDOT at kick-off. *(inference)* (Task 3c: Proof of Concept that AI/ML Can Develop Legal Land Descriptions, p. 9 [S23.1]; (A) Services, p. 8 [S17.1])
- Training is assumed to be delivered as a small number of virtual or on-site sessions for the Right of Way staff who will use the tool, plus recorded walkthroughs and one electronic and print-ready manual, rather than repeated sessions for the whole division. *(inference)* (Task 4: Training and User Manual, p. 9 [S24.1])
- The prototype is assumed to be hosted in a MoDOT-approved environment on Oracle 19C, with SQL Server used only if MoDOT IS approves it, and no PII stored, since the study works from property and deed data rather than personal records. *(inference)* ((Y) Information Technology, p. 18 [S73.2])
- The named LLD development program is assumed to be a commercially or openly licensed tool whose licence sits with the Offeror or is otherwise free of cost and licensing responsibility for MoDOT, so that BRPT review is a confirmation step rather than a procurement. *(inference)* ((Y) Information Technology, pp. 17-18 [S73.1])
- The literature review is assumed to be delivered as an annotated bibliography plus a peer-state comparison memo and a short briefing at a quarterly meeting, covering the past ten years of US state DOT practice, rather than a standalone published report. *(inference)* (Task 2: Literature Review, p. 8 [S20.1])
- The cost estimate is assumed to be a total-contract-value estimate for the full 15-month period of performance, detailed by labour category, hours and rates, since a detailed budget is developed only after award. *(inference)* ((1) Cost Estimate, p. 11 [S45.1]; (A) Cost Estimate, p. 12 [S47.1])
- The 10% MBE and 5% WBE targets are assumed to be measured against total contract value and reported in the proposal with named subcontracting partners, even though the RFP states them as encouraged. *(inference)* ((G) MBE/WBE Participation Encouraged, p. 14 [S55.1])
- The insurance limits are assumed to be binding at contract signing, with certificates of insurance provided on request before award. *(inference)* ((X) Insurance, p. 17 [S72.1])
- Confidential MHTC material is assumed to be identified by marking at the time it is supplied, and we will notify MHTC's representative within one business day of any third-party request for it. *(inference)* ((R) Confidentiality, p. 16 [S66.1])
- The Offeror is assumed to retain ownership of its pre-existing models, code and tooling, granting MHTC the royalty-free right to reproduce and use products derived from the work, with all study deliverables and MHTC-supplied information remaining MHTC property. *(inference)* ((U) Maintain Papers, p. 16 [S69.1]; (Q) Ownership of Reports, p. 16 [S65.1])
- The question deadline is assumed to be 17 July 2024 at 4 p.m. Central, the date carried on the contact row of the RFP timetable, and the proposal deadline is assumed to be fixed at 21 August 2024 at 10 a.m. Central even though MoDOT reserves the right to expand the rest of the schedule. *(inference)* ((E) RFP Schedule, pp. 5-6 [S12.1]; (4) Clarification of Requirements, p. 10 [S33.1])

## Risks

| ID | Risk | Severity | Likelihood | Source |
|---|---|---|---|---|
| K01 | Fixed milestone dates may be re-opened at kick-off, leaving the 25 April 2025 demonstration and 25 July 2025 training unachievable | high | medium | RFP |
| K02 | MoDOT IS approval of the named LLD program gates the proof of concept | high | medium | RFP |
| K03 | The $175,000 ceiling may not cover a surveyor-verified prototype plus training and reporting | high | medium | RFP |
| K04 | MHTC parameters and EPG Section 236.4.6.2 are not defined or supplied | high | medium | RFP |
| K05 | Contract term of 15 months conflicts with a 2 February 2026 end date | medium | medium | RFP |
| K06 | Oracle 19C and SQL Server requirements point at incompatible database platforms | medium | medium | RFP |
| K07 | Licensing and Python approval gates could force a redesign of the prototype | medium | medium | Solution |
| K08 | Exhibits A and B are referenced but not in the RFP | medium | medium | RFP |
| K09 | Unreadable pages 19 and 20 may carry requirements the proposal does not answer | medium | medium | RFP |
| K10 | The Price Page form is not provided, so the cost estimate may not match the required format | medium | medium | RFP |
| K11 | Evaluation criteria and weights are not disclosed | medium | medium | RFP |
| K12 | Post-award negotiated contract lets MHTC cancel the award | medium | low | RFP |

### K01. Fixed milestone dates may be re-opened at kick-off, leaving the 25 April 2025 demonstration and 25 July 2025 training unachievable

The RFP fixes a 25 April 2025 demonstration, 25 July 2025 training and manual, a September 2025 interim presentation and 3 November 2025 draft deliverables, yet the same table says milestone dates will be determined at the kick-off meeting and the schedule is only an estimate presuming a 1 November 2024 start. If the start slips or the dates move, the six-phase plan compresses and the demonstration, training and reporting dates are missed. Missing a contractual date on a research contract of this size is a material failure for the bidder and delays MoDOT's decision on the technology.

**Why:** The RFP both fixes and unfixes the same dates, and the schedule is explicitly an estimate pending contracting, so a later start is plausible; the consequence is a missed contractual milestone. ((G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2]; (D) Contract Period and Budget, p. 5 [S11.1])

**Mitigation:** State in the proposal that the milestone dates in the RFP table are treated as binding and that any later start is handled by a written schedule amendment, and ask MoDOT before the deadline whether the 1 November 2024 start and the listed milestone dates are fixed.

**Related requirements:** R016, R024, R026, R027, R031, R041, R055.

### K02. MoDOT IS approval of the named LLD program gates the proof of concept

The RFP requires the Offeror to name the program used to develop the LLDs before proof-of-concept work begins and requires MoDOT Information Systems to approve it before the demonstration phase may proceed. The RFP does not say what information must accompany the name or what criteria and turnaround the approval uses. If approval is slow or the chosen program is rejected, the 25 April 2025 demonstration slips and the bidder carries unplanned idle effort inside a fixed ceiling.

**Why:** The approval is a hard gate on the critical path to a fixed demonstration date, and the RFP leaves both the submission content and the approval timeline open. (Task 3b: Offeror Provides Program to Develop LLDs, p. 8 [S22.1]; (Y) Information Technology, pp. 17-18 [S73.1])

**Mitigation:** Name the program in the proposal with version, licensing model, hosting location, data flows and security posture, ask MoDOT IS before the deadline what else it needs and how long review takes, and hold explicit schedule contingency between approval and the demonstration.

**Related requirements:** R052, R053, R131, R136, R138.

### K03. The $175,000 ceiling may not cover a surveyor-verified prototype plus training and reporting

The RFP caps the work at a not-to-exceed $175,000 for a 15-month engagement that includes a literature review, a program approval cycle, a working AI/ML prototype, a professional land surveyor reviewing every generated description, role-based training, a user manual and a final report. The proposed solution prices a five-person senior team to that ceiling and assumes a sample of roughly ten to fifteen properties. If the property sample, training volume or surveyor review effort is larger than assumed, the bidder absorbs the overrun or cuts scope that MoDOT expects.

**Why:** The ceiling is fixed and the RFP leaves the demonstration sample, training volume and manual scope undefined, so the effort that drives cost is not settled; a senior team plus surveyor review is expensive relative to the cap. ((A) Services, p. 8 [S17.1]; (1) Cost Estimate, p. 11 [S45.1]; (A) Cost Estimate, p. 12 [S47.1])

**Mitigation:** State the assumed property count, training session count and manual scope explicitly in the proposal as the basis of the price, and ask MoDOT before the deadline to confirm the expected demonstration sample and training volume.

**Related requirements:** R042, R092, R096, R097, R007.

### K04. MHTC parameters and EPG Section 236.4.6.2 are not defined or supplied

The RFP requires the tool to draft from 'MHTC parameters' and to meet MoDOT EPG Section 236.4.6.2, but neither the parameter set nor the EPG section is included. The proposed solution assumes the parameters are right-of-way plan data, parcel and ownership records and deed references, and that the EPG section is publicly available and stable. If the real parameter set is different or the EPG rules are more intricate than assumed, the rules engine and the drafting model are rebuilt after kick-off, inside a fixed ceiling and a fixed demonstration date.

**Why:** The core technical input and the governing drafting standard are both undefined in the RFP, and the solution's reading of them is an explicit inference rather than a confirmed fact. ((B) Background, p. 5 [S9.1])

**Mitigation:** Ask MoDOT before the deadline for a sample MHTC parameter set and confirmation of which EPG 236.4.6.2 version governs, and state in the proposal that the parameter specification is fixed at kick-off and that changes to it are handled by written amendment.

**Related requirements:** R011, R012, R013, R014, R015.

### K05. Contract term of 15 months conflicts with a 2 February 2026 end date

The RFP states a 15-month contract period and separately ends the contract on 2 February 2026, which is roughly 14.5 months after the estimated 1 November 2024 start. The proposed solution prices and staffs a full 15 months and treats both as binding. If the shorter period governs, the final reporting phase and the last quarterly update fall outside the term and the bidder either absorbs unbilled effort or negotiates a change order.

**Why:** The two statements cannot both be true from the same start date, and the RFP does not say which governs; the gap is about two weeks of effort, absorbable but real. ((D) Contract Period and Budget, p. 5 [S11.1]; (G) Project Schedule, pp. 6-7 [S15.1]; (G) Project Schedule, p. 7 [S15.2])

**Mitigation:** Ask MoDOT to confirm whether the term is 15 months from the actual start or ends on 2 February 2026, and build the cost estimate on the shorter of the two with the final report scheduled before the end date.

**Related requirements:** R016, R041.

### K06. Oracle 19C and SQL Server requirements point at incompatible database platforms

One requirement mandates Oracle 19C for on-premise deployments while another directs the application to be designed and maintained on the latest supported SQL Server, with SQL Server 2016 or higher only if MoDOT IS approves. The proposed solution hedges by saying it runs on Oracle 19C or an approved SQL Server version. If the platform is not settled before the build, the prototype's data layer is built twice or rebuilt late, and the proof-of-concept demonstration date is at risk.

**Why:** The two requirements are directly contradictory and the RFP does not say whether they are alternatives or whether Oracle is the default; the prototype is small, so rework is material but not fatal. ((Y) Information Technology, p. 18 [S73.2])

**Mitigation:** Ask MoDOT IS before the deadline which platform the prototype must run on and what approval SQL Server needs, and design the data access layer so the database can be swapped without rewriting the rules engine.

**Related requirements:** R144, R145.

### K07. Licensing and Python approval gates could force a redesign of the prototype

The RFP bars third-party tools that place a licensing responsibility on MoDOT without prior BRPT and IS management approval, and reserves Python for ESRI scripts and small one-time uses unless the BRPT approves larger use. The proposed solution assumes the named program's licence sits with the Offeror at no cost to MoDOT and that Python use stays small. If either assumption is wrong, the bidder must re-select the program or rewrite components in C#, and the approval queue adds weeks to a fixed schedule.

**Why:** The solution's own assumptions make both approvals confirmation steps, but the RFP sets no threshold for 'large scale' Python and no criteria for the licensing review, so rejection is plausible. ((Y) Information Technology, pp. 17-18 [S73.1])

**Mitigation:** State in the proposal that the named program's licence is held by the Offeror with no cost or licensing obligation for MoDOT, keep Python to ESRI scripts only, and ask the BRPT before the deadline what it treats as large-scale Python use.

**Related requirements:** R136, R138, R131, R137.

### K08. Exhibits A and B are referenced but not in the RFP

The RFP requires an E-Verify MOU, a sworn affidavit of no unauthorized-alien employment and lawful-presence affidavits for sole proprietors and general partners, and points to Exhibit A and Exhibit B for the forms, but neither exhibit is in the document. The proposed solution commits to the affidavits without having seen the forms. If the forms cannot be obtained or require information the bidder does not hold at submission, the proposal is incomplete and can be disqualified.

**Why:** The obligation is mandatory and the forms are missing from the RFP, so the bidder cannot confirm it can complete them correctly before the deadline.

**Mitigation:** Request Exhibit A and Exhibit B from MoDOTResearchRFP@modot.mo.gov before the question deadline, and prepare the E-Verify MOU and affidavits in draft so they can be signed as soon as the forms arrive.

**Related requirements:** R117, R118, R119, R120.

### K09. Unreadable pages 19 and 20 may carry requirements the proposal does not answer

Pages 19 and 20 of the RFP could not be read: each has only 19 words of text and an image covering more than half the page. Those pages sit in the section that sets out the kick-off, Data Management Plan and task requirements. If they contain task detail, deliverable formats or review gates, the proposal may be non-responsive on a mandatory item without the bidder knowing.

**Why:** The pages fall in a substantive part of the scope of work and the text is largely unreadable, so a missed requirement is plausible; the consequence is a responsiveness failure rather than a delivery failure.

**Mitigation:** Ask MoDOT for a text-searchable copy of pages 19 and 20 before the question deadline, and cross-check the work plan and Data Management Plan against whatever those pages contain before submission.

**Related requirements:** R044, R047, R048, R049.

### K10. The Price Page form is not provided, so the cost estimate may not match the required format

The RFP requires the fee proposal on the Section (4) Price Page with Salaries, Benefits, Operating Expense, F&A, Miscellaneous and Total, but the form itself is not in the document. The proposed solution builds a bottom-up estimate and maps it to those categories. If the actual form has different line items, a different period basis or a prescribed breakdown, the estimate must be rebuilt close to the deadline and may not be comparable to other offers.

**Why:** The pricing form is mandatory and missing, and the RFP also leaves open whether the estimate covers the total contract value or an annual basis. (PROPOSAL, p. 4 [S5.1]; (1) Cost Estimate, p. 11 [S45.1]; (A) Cost Estimate, p. 12 [S47.1])

**Mitigation:** Obtain the Price Page from the MoDOT information-for-researchers page or by question before the deadline, and prepare the estimate so it can be re-cut into any prescribed line-item structure without re-pricing.

**Related requirements:** R006, R092, R093, R096, R097.

### K11. Evaluation criteria and weights are not disclosed

The RFP says proposals are evaluated against criteria set by the Technical Advisory Committee but does not list the criteria or their weights, and states that MHTC is not obliged to solicit missing information. The proposed solution allocates effort across a ten-page work plan, personnel, experience and references without knowing what is scored. If the weighting favours, for example, prior AI/ML or Missouri state-agency experience, the bid may be structured against the wrong strengths.

**Why:** The criteria are absent from the RFP and the proposal is judged as submitted, so a misallocated emphasis directly affects the chance of award. ((1) Evaluation Factors, p. 11 [S41.1]; (3) Responsibility to Submit Information, p. 11 [S43.1]; (2) Work Plan, p. 10 [S36.1])

**Mitigation:** Ask MoDOT before the deadline whether the evaluation criteria and weights can be shared, and structure the ten-page work plan so each Section 2 item and each differentiator is visible within the page limit.

**Related requirements:** R091, R105, R077, R079.

### K12. Post-award negotiated contract lets MHTC cancel the award

The RFP makes award subject to a post-award negotiated contract and allows MHTC to cancel and select another Offeror if terms cannot be agreed, while the contract provisions themselves are not reproduced in the RFP. The proposed solution accepts the negotiated contract and its provisions. If the negotiated terms add obligations the bidder has not priced, such as broader IP rights or different insurance, the bidder either accepts an uneconomic contract or loses the award after spending bid effort.

**Why:** Cancellation requires a negotiation breakdown, which is unusual, but the contract terms are not visible in the RFP and the bidder cannot price against them. (SECTION (5): AGREEMENT REQUIREMENTS, p. 13 [S48.1]; (E) Components of Agreement, p. 13 [S53.1])

**Mitigation:** Review the Standard Research Agreement on the MoDOT website before submission, ask before the deadline which provisions are non-negotiable, and state in the proposal the assumptions on IP ownership and insurance on which the price rests.

**Related requirements:** R098, R099, R100, R106, R107.

## Referenced documents

| Name | Kind | Page | Section | In PDF | URL |
|---|---|---|---|---|---|
| Exhibit A | exhibit | 15 | SECTION (5): AGREEMENT REQUIREMENTS | no |  |
| Exhibit B | exhibit | 15 | SECTION (5): AGREEMENT REQUIREMENTS | no |  |
| https://www.modot.org/information-researchers | hyperlink | 1 |  | no | https://www.modot.org/information-researchers |
| Section | hyperlink | 5 | GENERAL DESCRIPTION AND BACKGROUND | no | https://epg.modot.org/index.php/236.4_Description_Writing_and_Titles#236.4.6.2_Methods_of_Legally_Describing_the_Fee_or_Portion_Thereof |
| https://www.modot.org/research- | hyperlink | 6 | GENERAL DESCRIPTION AND BACKGROUND | no | https://www.modot.org/research-requests-proposal |
| Data Management Plan | hyperlink | 8 | Project Management | no | https://www.modot.org/media/14044 |
| https://www.e-verify.gov/ | hyperlink | 15 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://www.e-verify.gov/ |
| .NET and .NET Core official | hyperlink | 17 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core |
| State of Missouri's | hyperlink | 18 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://at.mo.gov/it-access/ |
| Accessibility (mo.gov)). | hyperlink | 18 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://www.mo.gov/accessibility/ |
| (WCAG 2.1 AA). | hyperlink | 18 | SECTION (5): AGREEMENT REQUIREMENTS | no | https://www.w3.org/TR/WCAG21/ |

## Parse flags

- Page 19: low word count (19 words)
- Page 19: large image block (image covers 54% of the page)
- Page 20: low word count (19 words)
- Page 20: large image block (image covers 54% of the page)
